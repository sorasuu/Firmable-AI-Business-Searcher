from typing import Dict, List, Optional, Any
import json
import os
import re
from datetime import datetime
from urllib.parse import urljoin
from langchain_groq import ChatGroq
from langchain.schema import HumanMessage, AIMessage, SystemMessage
from api.groq_services import GroqCompoundClient
from api.data_store import AnalysisStore, analysis_store

INSIGHT_FIELDS = (
    "summary",
    "industry",
    "company_size",
    "location",
    "usp",
    "products_services",
    "target_audience",
    "sentiment",
)

PLACEHOLDER_KEYWORDS = (
    "summary not available",
    "unable to determine",
    "unable to extract",
    "not found",
    "unknown",
    "n/a",
)

class ConversationalAgent:
    def __init__(
        self,
        groq_client: Optional[GroqCompoundClient] = None,
        store: Optional[AnalysisStore] = None,
    ):
        self.llm = ChatGroq(
            model=os.environ.get("GROQ_MODEL", "openai/gpt-oss-20b"),
            temperature=0.2,
            groq_api_key=os.environ.get("GROQ_API_KEY", "")
        )
        self.groq_client = groq_client or GroqCompoundClient()
        self.store = store or analysis_store

        # In-memory cache keyed by URL
        self.website_cache: Dict[str, Dict[str, Any]] = {}

    def cache_website_data(self, url: str, scraped_data: Dict, insights: Dict):
        """Cache website data and hydrate the shared semantic store."""

        normalized_url = str(url or scraped_data.get('url') or '').strip()
        if not normalized_url:
            return

        entry = None
        try:
            entry = self.store.store_analysis(normalized_url, scraped_data, insights)
        except Exception as error:
            print(f"[API] Failed to update analysis store for {normalized_url}: {error}")

        chunks = entry.chunks if entry else scraped_data.get('structured_chunks', []) or []

        self.website_cache[normalized_url] = {
            'scraped_data': scraped_data,
            'insights': insights,
            'chunks': chunks,
            'live_visits': [],
        }
    
    def get_cached_data(self, url: str) -> Optional[Dict]:
        """Retrieve cached website data"""
        normalized = str(url or '').strip()
        return self.website_cache.get(normalized)
    
    def chat(self, url: str, query: str, conversation_history: Optional[List[Dict]] = None) -> str:
        """Answer conversational queries about a previously analyzed website.

        Uses cached insights and the shared semantic vector index to assemble
        focused context for the LLM. Requires that the site has been analyzed and
        cached via ``cache_website_data`` (or previously stored in the analysis store).
        """

        normalized_url, cached = self._get_or_restore_cached(url)
        if not cached:
            return "I don't have information about this website yet. Please analyze it first using the /api/analyze endpoint."

        try:
            answer_text, context, _ = self._generate_answer_details(
                normalized_url=normalized_url,
                cached=cached,
                query=query,
                conversation_history=conversation_history,
            )
            if answer_text is None:
                return "I don't have information about this website yet. Please analyze it first using the /api/analyze endpoint."

            self._maybe_update_analysis_fields(
                url=normalized_url,
                cached=cached,
                question=query,
                answer_text=answer_text,
                context=context,
            )
            return answer_text

        except Exception as error:
            print(f"[API] Chat error: {error}")
            import traceback
            traceback.print_exc()
            return "I ran into an issue while answering. Please try rephrasing your question or re-running the analysis."

    def answer_question_with_sources(
        self,
        url: str,
        query: str,
        conversation_history: Optional[List[Dict]] = None,
    ) -> Optional[Dict[str, Any]]:
        normalized_url, cached = self._get_or_restore_cached(url)
        if not cached:
            return None

        try:
            answer_text, context, source_results = self._generate_answer_details(
                normalized_url=normalized_url,
                cached=cached,
                query=query,
                conversation_history=conversation_history,
            )
            if answer_text is None:
                return None

            self._maybe_update_analysis_fields(
                url=normalized_url,
                cached=cached,
                question=query,
                answer_text=answer_text,
                context=context,
            )

            formatted_sources = [
                {
                    'chunk_index': result.get('chunk_index', -1),
                    'chunk_text': result.get('chunk_text', ''),
                    'relevance_score': float(result.get('relevance_score', 0.0)),
                }
                for result in (source_results or [])
            ]

            return {
                'answer': answer_text,
                'source_chunks': formatted_sources,
            }

        except Exception as error:
            print(f"[API] Chat custom question error: {error}")
            import traceback
            traceback.print_exc()
            return None

    def _generate_answer_details(
        self,
        normalized_url: str,
        cached: Dict[str, Any],
        query: str,
        conversation_history: Optional[List[Dict]] = None,
    ) -> tuple[Optional[str], str, List[Dict[str, Any]]]:
        self._maybe_run_live_visit(normalized_url, query, cached)
        context, source_results = self._build_context(normalized_url, cached, query)

        messages: List[Any] = [
            SystemMessage(content="""You are an AI assistant that helps users understand websites and businesses.
You have access to processed website insights, contact details, and retrieved content snippets.

GUIDELINES:
- Always answer using Markdown formatting.
- Prefer concise paragraphs (1-3 sentences) or short bullet lists when listing facts.
- Use **bold** for key facts, `code` for short data (like emails), and tables when presenting multiple comparable items.
- Be transparent about uncertainty; if information is missing in the provided context, say so.
- Cite the provided snippets when relevant by referencing their chunk numbers (e.g., "(Chunk 2)").
""")
        ]

        if conversation_history:
            for msg in conversation_history[-5:]:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if role == "user":
                    messages.append(HumanMessage(content=content))
                elif role == "assistant":
                    messages.append(AIMessage(content=content))

        context_prompt = f"""Website Context:
{context}

User Question: {query}
"""
        messages.append(HumanMessage(content=context_prompt))

        response = self.llm.invoke(messages)
        answer_text = response.content.strip() if response and response.content else None
        return answer_text, context, source_results

    def extract_contact_profile(
        self,
        url: str,
        conversation_history: Optional[List[Dict]] = None,
    ) -> Optional[Dict[str, Any]]:
        normalized_url, cached = self._get_or_restore_cached(url)
        if not cached:
            return None

        try:
            self._maybe_run_live_visit(normalized_url, "contact", cached)
            context, source_results = self._build_context(normalized_url, cached, "contact information")

            messages: List[Any] = [
                SystemMessage(content="""You extract contact information from website context.
Respond strictly in JSON with the structure:
{
  "emails": [string],
  "phones": [string],
  "contact_urls": [string],
  "addresses": [string],
  "social_media": {
     "linkedin": [string],
     "twitter": [string],
     "facebook": [string],
     "instagram": [string],
     "youtube": [string],
     "other": [string]
  }
}
Collect every email, phone number, and contact page URL explicitly mentioned. Include only verified items from the context."""),
                HumanMessage(content=f"Website Context:\n{context}\n\nReturn JSON only.")
            ]

            response = self.llm.invoke(messages)
            raw_content = (response.content or "").strip() if response else ""
        except Exception as error:
            print(f"[API] Chat contact extraction error for {normalized_url}: {error}")
            import traceback
            traceback.print_exc()
            return None

        contact_payload = self._parse_contact_payload(raw_content)
        if contact_payload is None:
            return None

        formatted_sources = [
            {
                'chunk_index': result.get('chunk_index', -1),
                'chunk_text': result.get('chunk_text', ''),
                'relevance_score': float(result.get('relevance_score', 0.0)),
            }
            for result in (source_results or [])
        ]

        return {
            'contact_info': contact_payload,
            'source_chunks': formatted_sources,
        }

    def _is_live_visit_enabled(self) -> bool:
        return bool(self.groq_client and self.groq_client.is_available and self.groq_client.enable_visit)

    def _maybe_run_live_visit(self, base_url: str, query: str, cached: Dict[str, Any]) -> None:
        if not self._is_live_visit_enabled():
            return

        query_lower = (query or "").lower()
        trigger_keywords = {"pricing", "price", "plan", "plans", "cost", "subscription", "package", "latest", "update"}
        should_trigger = any(keyword in query_lower for keyword in trigger_keywords)

        if not should_trigger:
            return

        target_url = self._select_live_visit_target(base_url, query_lower, cached)
        if not target_url:
            return

        visits: List[Dict[str, Any]] = cached.setdefault('live_visits', [])
        if any(visit.get('url') == target_url for visit in visits):
            return

        instructions = "Summarise pricing plans, tiers, costs, and any key calls to action you find." if "pricing" in query_lower or "price" in query_lower else None
        result = self.groq_client.visit_website(target_url, instructions)

        if not result:
            return

        content = (result or {}).get('content', '')
        entry = {
            'url': result.get('url', target_url),
            'content': content,
            'query': query,
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'executed_tools': result.get('executed_tools'),
            'error': result.get('error'),
        }
        visits.append(entry)

        if content:
            self._blend_live_content_into_cache(cached, content)

    def _select_live_visit_target(self, base_url: str, query_lower: str, cached: Dict[str, Any]) -> Optional[str]:
        scraped = cached.get('scraped_data', {}) or {}
        all_links = scraped.get('all_links', {}) or {}

        candidate_urls: List[str] = []
        internal_links = all_links.get('internal', []) or []
        for link in internal_links:
            href = str(link.get('url') or '')
            if not href:
                continue
            text = str(link.get('text') or '').lower()
            if 'pric' in href.lower() or 'pric' in text:
                candidate_urls.append(href)

        contact_pages = all_links.get('contact_pages', []) or []
        for link in contact_pages:
            href = str(link.get('url') or '')
            if href:
                candidate_urls.append(href)

        if 'pricing' in query_lower or 'price' in query_lower or 'plan' in query_lower:
            for href in candidate_urls:
                if 'pric' in href.lower():
                    return href

        if candidate_urls:
            return candidate_urls[0]

        if base_url:
            base = base_url.rstrip('/')
            if 'pricing' in query_lower or 'price' in query_lower or 'plan' in query_lower:
                return urljoin(base + '/', 'pricing/')

        return base_url

    def _blend_live_content_into_cache(self, cached: Dict[str, Any], content: str) -> None:
        snippet = (content or '').strip()
        if not snippet:
            return

        normalized = snippet.replace('\r\n', '\n').strip()
        if not normalized:
            return

        segments: List[str] = []
        max_length = 900
        prefix = "[Live Visit] "

        remaining = normalized
        while remaining:
            segment = remaining[:max_length].strip()
            if segment:
                segments.append(f"{prefix}{segment}")
            if len(segments) >= 5:
                break
            if len(remaining) <= max_length:
                break
            remaining = remaining[max_length:]

        if not segments:
            return

        chunks: List[str] = cached.setdefault('chunks', [])
        for segment in segments:
            if segment not in chunks:
                chunks.append(segment)

        self._refresh_store_with_cache(cached)
    
    def _build_context(self, url: str, cached_data: Dict[str, Any], query: str) -> tuple[str, List[Dict[str, Any]]]:
        scraped = cached_data.get('scraped_data', {})
        insights = cached_data.get('insights', {})
        chunks: List[str] = cached_data.get('chunks', []) or []

        context_lines: List[str] = []

        page_url = scraped.get('url') or insights.get('url')
        if page_url:
            context_lines.append(f"URL: {page_url}")
        title = scraped.get('title') or insights.get('title')
        if title:
            context_lines.append(f"Title: {title}")

        summary = insights.get('summary')
        if summary:
            context_lines.append(f"Summary: {summary}")

        core_facts = []
        if insights.get('industry') and insights['industry'] != 'Unable to determine':
            core_facts.append(f"Industry: {insights['industry']}")
        if insights.get('location') and insights['location'] != 'Not found':
            core_facts.append(f"Location: {insights['location']}")
        if insights.get('company_size') and insights['company_size'] != 'Unable to determine':
            core_facts.append(f"Company Size: {insights['company_size']}")
        if insights.get('usp') and insights['usp'] != 'Unable to extract':
            core_facts.append(f"USP: {insights['usp']}")
        if insights.get('products_services') and insights['products_services'] != 'Unable to extract':
            core_facts.append(f"Products/Services: {insights['products_services']}")
        if insights.get('target_audience') and insights['target_audience'] != 'Unable to determine':
            core_facts.append(f"Target Audience: {insights['target_audience']}")

        if core_facts:
            context_lines.append("Key Insights:")
            context_lines.extend(f"- {fact}" for fact in core_facts)

        contact = insights.get('contact_info') or {}
        contact_lines = []
        if contact.get('emails'):
            contact_lines.append(f"Emails: {', '.join(contact['emails'])}")
        if contact.get('phones'):
            contact_lines.append(f"Phones: {', '.join(contact['phones'])}")
        social = contact.get('social_media') or {}
        if social:
            formatted_social = ", ".join(f"{platform}: {links[0]}" for platform, links in social.items() if links)
            if formatted_social:
                contact_lines.append(f"Social: {formatted_social}")
        if contact_lines:
            context_lines.append("Contact Info:")
            context_lines.extend(f"- {line}" for line in contact_lines)

        live_visit = insights.get('groq_live_visit')
        if isinstance(live_visit, dict) and live_visit.get('content'):
            snippet = live_visit['content'][:600].strip()
            context_lines.append("Live Visit Snapshot:")
            context_lines.append(f"- {snippet}")

        live_browser = insights.get('groq_browser_research')
        if isinstance(live_browser, dict):
            highlights = []
            for question, data in list(live_browser.items())[:2]:
                if isinstance(data, dict) and data.get('content'):
                    highlights.append(f"{question}: {data['content'][:400].strip()}")
            if highlights:
                context_lines.append("Live Research Highlights:")
                context_lines.extend(f"- {item}" for item in highlights)

        live_visits_cached = cached_data.get('live_visits') or []
        if live_visits_cached:
            context_lines.append("Additional Live Visit Content:")
            for visit in live_visits_cached[-2:]:
                if visit.get('error'):
                    context_lines.append(f"- {visit.get('url', page_url)}: (error) {visit['error']}")
                    continue
                visit_snippet = str(visit.get('content', '')).strip()
                if visit_snippet:
                    if len(visit_snippet) > 500:
                        visit_snippet = visit_snippet[:500].rstrip() + "..."
                    context_lines.append(f"- {visit.get('url', page_url)} (fetched {visit.get('timestamp', 'recently')}): {visit_snippet}")
                else:
                    context_lines.append(f"- {visit.get('url', page_url)}: (no content returned)")

        # Retrieve relevant chunks via semantic search fallback
        retrieved_chunks: List[str] = []
        semantic_results = self._search_semantic_chunks(url, query, top_k=4)
        if not semantic_results and chunks:
            semantic_results = self._fallback_chunk_scan(chunks, query, top_k=2)

        deduped_results = self._dedupe_results(semantic_results, limit=4)

        for result in deduped_results:
            snippet = str(result.get('chunk_text', '')).strip()
            if len(snippet) > 650:
                snippet = snippet[:650].rstrip() + "..."
            index = result.get('chunk_index')
            label = f"Chunk {index + 1}" if isinstance(index, int) and index >= 0 else "Chunk"
            retrieved_chunks.append(f"{label}: {snippet}")

        if not retrieved_chunks and chunks:
            fallback_chunk_full = chunks[0]
            fallback_chunk = fallback_chunk_full[:650].strip()
            retrieved_chunks.append(f"Chunk 1: {fallback_chunk}")
            if not deduped_results:
                deduped_results = [{
                    'chunk_index': 0,
                    'chunk_text': fallback_chunk_full,
                    'relevance_score': 0.0,
                }]

        if retrieved_chunks:
            context_lines.append("Relevant Content Snippets:")
            context_lines.extend(f"- {chunk}" for chunk in retrieved_chunks)

        # Include previous answers if available
        custom_answers = insights.get('custom_answers') or {}
        if custom_answers:
            context_lines.append("Custom Question Answers:")
            for question, answer in list(custom_answers.items())[:3]:
                answer_text = str(answer)[:400].strip()
                context_lines.append(f"- {question}: {answer_text}")

        return "\n".join(context_lines), deduped_results

    def _maybe_update_analysis_fields(
        self,
        url: str,
        cached: Dict[str, Any],
        question: str,
        answer_text: str,
        context: str,
    ) -> None:
        if not url or not answer_text.strip():
            return

        insights: Dict[str, Any] = cached.setdefault('insights', {})
        current_snapshot = {field: insights.get(field) for field in INSIGHT_FIELDS}

        try:
            snapshot_json = json.dumps(current_snapshot, ensure_ascii=False)
        except (TypeError, ValueError):
            snapshot_json = json.dumps({})

        # Reduce prompt size while preserving supporting evidence
        truncated_context = context[-1500:]
        sanitized_answer = answer_text[:1200]
        sanitized_question = (question or "")[:600]

        verifier_messages = [
            SystemMessage(content=(
                "You maintain canonical report fields for a business analysis. "
                "Only propose updates that are explicitly supported by the assistant's latest answer "
                "and the retrieved context. Respond strictly in JSON with the structure: "
                "{\"updates\": {<field>: <new_value>, ...}}. Do not include fields when unsure."
            )),
            HumanMessage(content=(
                "Current insights (JSON):\n"
                f"{snapshot_json}\n\n"
                "User question:\n"
                f"{sanitized_question}\n\n"
                "Assistant answer:\n"
                f"{sanitized_answer}\n\n"
                "Retrieved context snippets:\n"
                f"{truncated_context}\n\n"
                "Identify high-confidence updates for summary, industry, company_size, location, usp, "
                "products_services, target_audience, or sentiment. Return {\"updates\": {}} if none."
            )),
        ]

        try:
            verifier_response = self.llm.invoke(verifier_messages)
            raw_content = (verifier_response.content or "").strip()
        except Exception as error:
            print(f"[API] Chat update verification failed for {url}: {error}")
            return

        updates_payload: Dict[str, Any]
        try:
            json_start = raw_content.find('{')
            json_end = raw_content.rfind('}') + 1
            if json_start == -1 or json_end <= json_start:
                return
            updates_payload = json.loads(raw_content[json_start:json_end])
        except (json.JSONDecodeError, TypeError, ValueError):
            return

        if not isinstance(updates_payload, dict):
            return

        proposed = updates_payload.get('updates', {})
        if not isinstance(proposed, dict) or not proposed:
            return

        support_text = f"{context}\n{answer_text}".lower()
        updated_fields: List[str] = []
        source_chunks = insights.setdefault('source_chunks', {})

        for field, value in proposed.items():
            if field not in INSIGHT_FIELDS:
                continue
            if not isinstance(value, str):
                continue
            new_value = value.strip()
            if not new_value:
                continue

            current_value = insights.get(field)
            placeholder_current = self._is_placeholder_value(current_value)
            if not placeholder_current and isinstance(current_value, str):
                if new_value.lower() == current_value.strip().lower():
                    continue
                if field != 'summary' and new_value.lower() not in support_text:
                    continue

            insights[field] = new_value
            source_chunks[field] = [{
                'chunk_index': -1,
                'chunk_text': f"[Chat Update] {answer_text[:400]}",
                'relevance_score': 1.0,
            }]
            updated_fields.append(field)

        if not updated_fields:
            return

        cached['insights'] = insights
        try:
            self.store.update_insights(url, insights)
        except Exception as error:
            print(f"[API] Failed to persist chat-driven updates for {url}: {error}")

    def _refresh_store_with_cache(self, cached: Dict[str, Any]) -> None:
        scraped = cached.get('scraped_data') or {}
        url = str(scraped.get('url') or '').strip()
        if not url:
            return

        refreshed_payload = dict(scraped)
        refreshed_payload['structured_chunks'] = cached.get('chunks', []) or []

        try:
            self.store.prepare_site(url, refreshed_payload)
            insights = cached.get('insights')
            if insights:
                self.store.update_insights(url, insights)
        except Exception as error:
            print(f"[API] Failed to refresh semantic store with live content for {url}: {error}")

    def _search_semantic_chunks(self, url: str, query: str, top_k: int = 4) -> List[Dict[str, Any]]:
        if not url or not query or not query.strip():
            return []
        try:
            results = self.store.search_chunks(url, query, top_k=top_k)
        except Exception as error:
            print(f"[API] Chat semantic search failed for {url}: {error}")
            return []

        formatted: List[Dict[str, Any]] = []
        for result in results:
            chunk_text = str(result.get('chunk_text', '')).strip()
            if not chunk_text:
                continue
            formatted.append({
                'chunk_index': int(result.get('chunk_index', -1)),
                'chunk_text': chunk_text,
                'relevance_score': float(result.get('score', result.get('relevance_score', 0.0)) or 0.0)
            })
        return formatted

    def _fallback_chunk_scan(self, chunks: List[str], query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        if not chunks or not query or not query.strip():
            return []

        tokens = [token.lower() for token in re.split(r"\W+", query) if len(token) >= 3]
        if not tokens:
            tokens = [query.lower()]

        results: List[Dict[str, Any]] = []
        for index, chunk in enumerate(chunks[:25]):
            chunk_lower = chunk.lower()
            score = 0
            for token in tokens:
                if token in chunk_lower:
                    score += 1

            if score > 0:
                results.append({
                    'chunk_index': index,
                    'chunk_text': chunk,
                    'relevance_score': float(score)
                })

        results.sort(key=lambda item: item['relevance_score'], reverse=True)
        return results[:top_k]

    def _dedupe_results(self, results: List[Dict[str, Any]], limit: int = 4) -> List[Dict[str, Any]]:
        deduped: List[Dict[str, Any]] = []
        seen_indices: set[int] = set()

        for item in results:
            idx = int(item.get('chunk_index', -1))
            if idx < 0 or idx in seen_indices:
                continue
            seen_indices.add(idx)
            deduped.append({
                'chunk_index': idx,
                'chunk_text': item.get('chunk_text', ''),
                'relevance_score': float(item.get('relevance_score', 0.0))
            })
            if limit and len(deduped) >= limit:
                break

        return deduped

    def _get_or_restore_cached(self, url: str) -> tuple[str, Optional[Dict[str, Any]]]:
        normalized_url = str(url or '').strip()
        cached = self.get_cached_data(normalized_url)
        if cached:
            return normalized_url, cached

        entry = self.store.get(normalized_url)
        if entry and entry.insights:
            cached = {
                'scraped_data': entry.scraped_data,
                'insights': entry.insights,
                'chunks': entry.chunks,
                'live_visits': [],
            }
            self.website_cache[normalized_url] = cached
            return normalized_url, cached

        return normalized_url, None

    @staticmethod
    def _is_placeholder_value(value: Any) -> bool:
        if not value:
            return True
        if not isinstance(value, str):
            return False
        normalized = value.strip().lower()
        if not normalized:
            return True
        return any(keyword in normalized for keyword in PLACEHOLDER_KEYWORDS)

    def _parse_contact_payload(self, raw_content: str) -> Optional[Dict[str, Any]]:
        if not raw_content:
            return None

        json_start = raw_content.find('{')
        json_end = raw_content.rfind('}') + 1
        if json_start == -1 or json_end <= json_start:
            return None

        try:
            payload = json.loads(raw_content[json_start:json_end])
        except json.JSONDecodeError:
            return None

        if not isinstance(payload, dict):
            return None

        emails = self._ensure_string_list(payload.get('emails'))
        phones = self._ensure_string_list(payload.get('phones'))
        contact_urls = self._ensure_string_list(payload.get('contact_urls'))
        addresses = self._ensure_string_list(payload.get('addresses'))

        socials_payload = payload.get('social_media') or {}
        social_media: Dict[str, List[str]] = {}
        if isinstance(socials_payload, dict):
            for key, value in socials_payload.items():
                social_media[key] = self._ensure_string_list(value)

        return {
            'emails': emails,
            'phones': phones,
            'contact_urls': contact_urls,
            'addresses': addresses,
            'social_media': social_media,
        }

    @staticmethod
    def _ensure_string_list(value: Any) -> List[str]:
        if not value:
            return []
        if isinstance(value, str):
            return [value.strip()] if value.strip() else []
        if isinstance(value, (list, tuple, set)):
            cleaned = [str(item).strip() for item in value if str(item).strip()]
            seen: set[str] = set()
            unique: List[str] = []
            for item in cleaned:
                lowered = item.lower()
                if lowered not in seen:
                    seen.add(lowered)
                    unique.append(item)
            return unique
        return []
