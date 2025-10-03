from typing import Dict, List, Optional, Any
import os
from datetime import datetime
from urllib.parse import urljoin
from langchain_groq import ChatGroq
from langchain.schema import HumanMessage, AIMessage, SystemMessage
from api.groq_services import GroqCompoundClient
from api.chunk_search import ChunkSearcher

class ConversationalAgent:
    def __init__(self, groq_client: Optional[GroqCompoundClient] = None):
        self.llm = ChatGroq(
            model=os.environ.get("GROQ_MODEL", "openai/gpt-oss-20b"),
            temperature=0.2,
            groq_api_key=os.environ.get("GROQ_API_KEY", "")
        )
        self.groq_client = groq_client or GroqCompoundClient()

        # In-memory cache keyed by URL
        self.website_cache: Dict[str, Dict[str, Any]] = {}

    def cache_website_data(self, url: str, scraped_data: Dict, insights: Dict):
        """Cache website data, including a BM25 chunk search index."""
        chunks = scraped_data.get('structured_chunks', []) or []
        chunk_searcher = ChunkSearcher(chunks) if chunks else None

        self.website_cache[url] = {
            'scraped_data': scraped_data,
            'insights': insights,
            'chunk_searcher': chunk_searcher,
            'chunks': chunks,
            'live_visits': [],
        }
    
    def get_cached_data(self, url: str) -> Optional[Dict]:
        """Retrieve cached website data"""
        return self.website_cache.get(url)
    
    def chat(self, url: str, query: str, conversation_history: Optional[List[Dict]] = None) -> str:
        """Answer conversational queries about a previously analyzed website.

        Uses cached insights and in-memory BM25 search over markdown chunks to build
        focused context for the LLM. Requires that the site has been analyzed and
        cached via ``cache_website_data``.
        """
        
        # Get cached data
        cached = self.get_cached_data(url)
        
        if not cached:
            return "I don't have information about this website yet. Please analyze it first using the /api/analyze endpoint."
        
        try:
            self._maybe_run_live_visit(url, query, cached)
            context = self._build_context(cached, query)

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
            return response.content.strip()

        except Exception as error:
            print(f"[API] Chat error: {error}")
            import traceback
            traceback.print_exc()
            return "I ran into an issue while answering. Please try rephrasing your question or re-running the analysis."

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
        chunks.extend(segments)
        cached['chunk_searcher'] = ChunkSearcher(chunks)
    
    def _build_context(self, cached_data: Dict[str, Any], query: str) -> str:
        scraped = cached_data.get('scraped_data', {})
        insights = cached_data.get('insights', {})
        searcher: Optional[ChunkSearcher] = cached_data.get('chunk_searcher')
        chunks: List[str] = cached_data.get('chunks', []) or []

        context_lines: List[str] = []

        url = scraped.get('url') or insights.get('url')
        if url:
            context_lines.append(f"URL: {url}")
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
                    context_lines.append(f"- {visit.get('url', url)}: (error) {visit['error']}")
                    continue
                visit_snippet = str(visit.get('content', '')).strip()
                if visit_snippet:
                    if len(visit_snippet) > 500:
                        visit_snippet = visit_snippet[:500].rstrip() + "..."
                    context_lines.append(f"- {visit.get('url', url)} (fetched {visit.get('timestamp', 'recently')}): {visit_snippet}")
                else:
                    context_lines.append(f"- {visit.get('url', url)}: (no content returned)")

        # Retrieve relevant chunks via BM25
        retrieved_chunks: List[str] = []
        if searcher:
            results = searcher.search(query, top_k=4)
            for result in results:
                snippet = result.text.strip()
                if len(snippet) > 650:
                    snippet = snippet[:650].rstrip() + "..."
                retrieved_chunks.append(f"Chunk {result.index + 1}: {snippet}")

        if not retrieved_chunks and chunks:
            fallback_chunk = chunks[0][:650].strip()
            retrieved_chunks.append(f"Chunk 1: {fallback_chunk}")

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

        return "\n".join(context_lines)
