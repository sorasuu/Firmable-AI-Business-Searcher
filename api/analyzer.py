from typing import Any, Dict, List, Optional
import os
from langchain_groq import ChatGroq
from langchain.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from pydantic import BaseModel, Field
import json
import re

from api.groq_services import GroqCompoundClient
from api.data_store import AnalysisStore, WebsiteEntry, analysis_store


# Define structured output models
class BusinessInsights(BaseModel):
    summary: str = Field(description="Concise AI summary of the website")
    industry: str = Field(description="Primary industry or sector")
    company_size: str = Field(description="Estimated company size (startup/small/medium/large/enterprise)")
    location: str = Field(description="Company headquarters or primary location")
    usp: str = Field(description="Unique selling proposition")
    products_services: str = Field(description="Main products or services offered")
    target_audience: str = Field(description="Primary customer demographic or market segment")
    sentiment: str = Field(description="Overall tone and sentiment of the website")


class AIAnalyzer:
    """Business website analyzer using Firecrawl-scraped data"""
    
    def __init__(
        self,
        groq_client: Optional[GroqCompoundClient] = None,
        store: Optional[AnalysisStore] = None,
    ):
        self.llm = ChatGroq(
            model=os.environ.get("GROQ_MODEL", "openai/gpt-oss-20b"),
            temperature=0.3,
            groq_api_key=os.environ.get("GROQ_API_KEY", "")
        )
        self.groq_client = groq_client or GroqCompoundClient()
        self.store = store or analysis_store
        try:
            self.browser_question_limit = int(os.environ.get("GROQ_BROWSER_QUESTION_LIMIT", "3"))
        except ValueError:
            self.browser_question_limit = 3

    def _default_insight_values(self) -> Dict[str, str]:
        return {
            "summary": "Summary not available",
            "industry": "Unable to determine",
            "company_size": "Unable to determine",
            "location": "Not found",
            "usp": "Unable to extract",
            "products_services": "Unable to extract",
            "target_audience": "Unable to determine",
            "sentiment": "neutral",
        }

    def _normalize_insights(self, insights: Dict[str, Any]) -> Dict[str, Any]:
        defaults = self._default_insight_values()
        normalized: Dict[str, Any] = {}

        for key, default in defaults.items():
            value = insights.get(key, default)
            if isinstance(value, str):
                value = value.strip()
            if not value:
                value = default
            normalized[key] = value

        # Preserve any additional keys (like errors) from the original payload
        for key, value in insights.items():
            if key not in normalized:
                normalized[key] = value

        return normalized
    
    def analyze_website(self, scraped_data: Dict, custom_questions: Optional[List[str]] = None) -> Dict:
        """Analyze website content using LangChain backed by the shared semantic store."""

        # Prepare context from scraped data
        context = self._prepare_context(scraped_data)

        url = str(scraped_data.get('url') or '').strip()
        entry: Optional[WebsiteEntry] = None
        chunks: List[str] = scraped_data.get('structured_chunks', []) or []

        if url:
            try:
                entry = self.store.prepare_site(url, scraped_data)
                chunks = entry.chunks
            except Exception as error:
                print(f"[API] Failed to prepare semantic store for {url}: {error}")
        else:
            print("[API] No URL provided in scraped data; semantic store disabled for this run.")

        # Get default insights using structured output with source tracking
        default_insights, source_chunks = self._get_default_insights(url, context, chunks)

        # Answer custom questions if provided
        custom_insights: Dict[str, Any] = {}
        custom_source_chunks: Dict[str, List[Dict[str, Any]]] = {}
        if custom_questions:
            custom_result = self._answer_custom_questions(url, context, custom_questions, chunks)
            custom_insights = custom_result['answers']
            custom_source_chunks = custom_result['source_chunks']

        # Merge source chunks from default insights and custom questions
        all_source_chunks = {**source_chunks}
        for question, chunks_list in custom_source_chunks.items():
            all_source_chunks[question] = chunks_list

        # Add source tracking for contact info
        contact_info = scraped_data.get('contact_info', {}) or {}
        contact_sources = self._identify_contact_sources(url, contact_info, chunks)
        all_source_chunks.update(contact_sources)

        live_visit = self._run_live_visit(scraped_data)
        live_browser_answers = self._run_live_browser_research(scraped_data.get('url'), custom_questions or [])

        result = {
            **default_insights,
            'custom_answers': custom_insights,
            'source_chunks': all_source_chunks,
            'contact_info': contact_info
        }
        if live_visit:
            result['groq_live_visit'] = live_visit
        if live_browser_answers:
            result['groq_browser_research'] = live_browser_answers

        if url:
            try:
                self.store.update_insights(url, result)
            except Exception as error:
                print(f"[API] Failed to persist insights for {url}: {error}")

        return result
    
    def _prepare_context(self, scraped_data: Dict) -> str:
        """Prepare context from Firecrawl-scraped data using markdown content"""
        context_parts = [
            f"Website URL: {scraped_data.get('url', 'N/A')}",
            f"Title: {scraped_data.get('title', 'N/A')}",
            f"Description: {scraped_data.get('description', 'N/A')}",
        ]

        # Add headings for structure
        headings = scraped_data.get('headings', [])
        if headings:
            context_parts.append(f"\nPage Structure (Headings):")
            for heading in headings[:12]:  # Top 12 headings
                context_parts.append(f"{'#' * heading.get('level', 1)} {heading.get('text', '')}")

        # Use content chunks from Firecrawl (already intelligently chunked)
        chunks = scraped_data.get('structured_chunks', [])
        if chunks:
            context_parts.append(f"\nMain Content (from {len(chunks)} chunks):")
            # Use top chunks for context
            for i, chunk in enumerate(chunks[:10]):  # Top 10 chunks
                context_parts.append(f"\n--- Chunk {i+1} ---")
                context_parts.append(chunk[:1500])  # Limit chunk size
        
        # Add markdown content summary if available
        markdown_content = scraped_data.get('markdown_content', '')
        if markdown_content and len(markdown_content) < 8000:
            context_parts.append(f"\nMarkdown Content Summary:")
            context_parts.append(markdown_content[:8000])

        return "\n".join(context_parts)
    
    def _get_default_insights(
        self,
        url: str,
        context: str,
        chunks: List[str],
    ) -> tuple[Dict, Dict]:
        """Extract default business insights using LangChain with source tracking"""
        
        try:
            # Create prompt template
            system_template = """You are an expert business analyst specializing in website analysis. 
Analyze the provided website content and extract key business insights.
Return your analysis as a JSON object with these exact keys:
- summary: Concise AI-written overview of the business (1-2 sentences)
- industry: Primary industry or sector
- company_size: Estimated company size (startup/small/medium/large/enterprise)
- location: Company headquarters or primary location
- usp: Unique selling proposition
- products_services: Main products or services offered
- target_audience: Primary customer demographic or market segment
- sentiment: Overall tone and sentiment of the website

Be specific, concise, and accurate. Keep each field under 200 characters (summary up to 350 characters)."""

            human_template = """Analyze the following website content and return JSON:

{context}

Return only valid JSON, no other text:"""

            system_message = SystemMessagePromptTemplate.from_template(system_template)
            human_message = HumanMessagePromptTemplate.from_template(human_template)
            
            chat_prompt = ChatPromptTemplate.from_messages([system_message, human_message])
            
            # Create chain without Pydantic parser
            chain = chat_prompt | self.llm
            
            # Run analysis
            response = chain.invoke({
                "context": context
            })
            
            # Parse JSON response manually
            content = response.content.strip()
            print(f"[API] Raw LLM response: {content[:500]}...")
            
            # Try to extract JSON from response
            json_start = content.find('{')
            json_end = content.rfind('}') + 1
            
            if json_start != -1 and json_end > json_start:
                json_content = content[json_start:json_end]
                try:
                    parsed = json.loads(json_content)
                    print(f"[API] Successfully parsed JSON: {parsed}")
                    
                    # Track source chunks for each insight
                    normalized = self._normalize_insights(parsed)
                    source_chunks = self._identify_source_chunks(url, normalized, chunks)
                    
                    return normalized, source_chunks
                except json.JSONDecodeError as je:
                    print(f"[API] JSON parse error: {je}")
            
            # Fallback: try to parse line by line or extract key-value pairs
            fallback_result = self._parse_llm_response_fallback(content)
            normalized = self._normalize_insights(fallback_result)
            source_chunks = self._identify_source_chunks(url, normalized, chunks)
            return normalized, source_chunks
            
        except Exception as e:
            print(f"Analysis error: {str(e)}")
            import traceback
            print(f"Analysis traceback: {traceback.format_exc()}")
            fallback_result = self._default_insight_values()
            fallback_result["error"] = str(e)
            source_chunks = self._identify_source_chunks(url, fallback_result, chunks)
            return fallback_result, source_chunks
    
    def _identify_source_chunks(
        self,
        url: str,
        insights: Dict,
        chunks: List[str],
    ) -> Dict[str, List[Dict[str, Any]]]:
        source_chunks: Dict[str, List[Dict[str, Any]]] = {}
        defaults = self._default_insight_values()

        heuristic_keywords = {
            'summary': ['summary', 'overview', 'company', 'business', 'focus', 'mission', 'vision', 'help', 'solution', 'platform'],
            'industry': ['industry', 'sector', 'business', 'company', 'market', 'field'],
            'company_size': ['employee', 'team', 'size', 'company', 'startup', 'enterprise', 'small', 'large', 'medium'],
            'location': ['location', 'headquarters', 'office', 'address', 'city', 'country', 'based'],
            'usp': ['unique', 'selling', 'proposition', 'advantage', 'differentiator', 'why choose', 'benefit'],
            'products_services': ['product', 'service', 'solution', 'offering', 'platform', 'tool', 'software'],
            'target_audience': ['customer', 'client', 'user', 'audience', 'market', 'target', 'who we serve'],
            'sentiment': ['professional', 'innovative', 'reliable', 'trusted', 'quality', 'experience']
        }

        for key, keywords in heuristic_keywords.items():
            insight_value = insights.get(key)
            if not insight_value or insight_value == defaults.get(key):
                source_chunks[key] = []
                continue

            results: List[Dict[str, Any]] = []
            if isinstance(insight_value, str):
                results.extend(self._search_semantic_chunks(url, insight_value, top_k=4))

            if not results:
                results.extend(self._heuristic_chunk_matches(chunks, keywords, str(insight_value) if isinstance(insight_value, str) else None))

            source_chunks[key] = self._dedupe_results(results, limit=3)

        return source_chunks
    
    def _identify_contact_sources(
        self,
        url: str,
        contact_info: Dict,
        chunks: List[str],
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Identify source chunks for contact information."""

        source_chunks: Dict[str, List[Dict[str, Any]]] = {}

        contact_keywords = {
            'emails': ['email', 'contact', 'mail', '@', 'support', 'info', 'hello'],
            'phones': ['phone', 'tel', 'call', 'contact', 'mobile', 'number', '+', '('],
            'social_media': ['social', 'facebook', 'twitter', 'linkedin', 'instagram', 'youtube', 'follow']
        }

        for contact_type, keywords in contact_keywords.items():
            values = contact_info.get(contact_type)
            if not values:
                source_chunks[contact_type] = []
                continue

            query_fragments: List[str] = []
            if isinstance(values, list):
                query_fragments.extend(str(value) for value in values if value)
            elif isinstance(values, dict):
                query_fragments.extend(str(value) for value in values.values() if value)
            elif values:
                query_fragments.append(str(values))

            query = " ".join(fragment for fragment in query_fragments if fragment)

            results: List[Dict[str, Any]] = []
            if query:
                semantic_results = self._search_semantic_chunks(url, query, top_k=6)
                results.extend(self._filter_contact_results(semantic_results, values))

            if not results:
                results.extend(self._heuristic_contact_matches(chunks, keywords, values))

            source_chunks[contact_type] = self._dedupe_results(results, limit=3)

        return source_chunks
    
    def _parse_llm_response_fallback(self, content: str) -> Dict:
        """Fallback parser for LLM responses that aren't valid JSON"""
        try:
            # Initialize with defaults
            result = self._default_insight_values().copy()
            
            # Try to extract information using regex patterns
            import re
            
            # Look for key-value patterns
            patterns = {
                'summary': r'(?:summary|overall|overview)[\s:]+([^\n\r]{1,350})',
                'industry': r'(?:industry|sector)[\s:]+([^\n\r]{1,200})',
                'company_size': r'(?:company.size|size)[\s:]+([^\n\r]{1,100})',
                'location': r'(?:location|headquarters)[\s:]+([^\n\r]{1,100})',
                'usp': r'(?:usp|selling.proposition|unique.selling)[\s:]+([^\n\r]{1,200})',
                'products_services': r'(?:products|services)[\s:]+([^\n\r]{1,200})',
                'target_audience': r'(?:target.audience|customers|market)[\s:]+([^\n\r]{1,200})',
                'sentiment': r'(?:sentiment|tone)[\s:]+([^\n\r]{1,50})'
            }
            
            content_lower = content.lower()
            for key, pattern in patterns.items():
                match = re.search(pattern, content_lower, re.IGNORECASE)
                if match:
                    # Get the original case version from the original content
                    start = content_lower.find(match.group(1).lower())
                    if start != -1:
                        original_text = content[start:start + len(match.group(1))]
                        result[key] = original_text.strip()
            
            print(f"[API] Fallback parsing result: {result}")
            return result
            
        except Exception as e:
            print(f"[API] Fallback parsing error: {str(e)}")
            error_result = self._default_insight_values().copy()
            error_result["error"] = f"Parsing failed: {str(e)}"
            return error_result
    
    def _answer_custom_questions(
        self,
        url: str,
        context: str,
        questions: List[str],
        chunks: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Answer custom user questions using LangChain with RAG approach."""

        answers: Dict[str, str] = {}
        source_chunks: Dict[str, List[Dict[str, Any]]] = {}

        available_chunks = chunks or []

        for question in questions[:5]:  # Limit to 5 questions
            try:
                semantic_results = self._search_semantic_chunks(url, question, top_k=4)
                if not semantic_results and available_chunks:
                    semantic_results = self._fallback_chunk_scan(available_chunks, question, top_k=3)

                deduped_results = self._dedupe_results(semantic_results, limit=4)

                if deduped_results:
                    relevant_context = "\n\n".join(result['chunk_text'] for result in deduped_results)
                else:
                    relevant_context = context

                qa_prompt = ChatPromptTemplate.from_messages([
                    ("system", "You are a helpful assistant that answers questions about websites based on their content. Provide clear, concise answers in 1-3 sentences. Use markdown formatting for better readability when appropriate (lists, bold, etc.). If you cannot find the information in the provided content, say so clearly."),
                    ("human", """Website Content:
{context}

Question: {question}

Answer:""")
                ])

                qa_chain = qa_prompt | self.llm

                response = qa_chain.invoke({
                    "context": relevant_context,
                    "question": question
                })

                answer_text = response.content.strip()
                answers[question] = answer_text
                source_chunks[question] = deduped_results

            except Exception as error:
                answers[question] = f"Unable to answer: {error}"
                source_chunks[question] = []

        return {
            'answers': answers,
            'source_chunks': source_chunks
        }

    # ------------------------------------------------------------------
    # Semantic store helpers
    # ------------------------------------------------------------------
    def _search_semantic_chunks(self, url: str, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        if not url or not query or not query.strip():
            return []
        try:
            results = self.store.search_chunks(url, query, top_k=top_k)
        except Exception as error:
            print(f"[API] Semantic search failed for {url}: {error}")
            return []

        formatted: List[Dict[str, Any]] = []
        for result in results:
            chunk_text = str(result.get('chunk_text', '')).strip()
            if not chunk_text:
                continue
            score = result.get('score', 0.0)
            if isinstance(score, (int, float)):
                relevance = round(float(score), 4)
            else:
                relevance = 0.0
            chunk_index = int(result.get('chunk_index', -1))
            formatted.append({
                'chunk_index': chunk_index,
                'chunk_text': chunk_text,
                'relevance_score': relevance
            })

        return formatted

    def _heuristic_chunk_matches(
        self,
        chunks: List[str],
        keywords: List[str],
        text_hint: Optional[str],
        top_k: int = 3,
    ) -> List[Dict[str, Any]]:
        if not chunks:
            return []

        keywords_lower = [keyword.lower() for keyword in keywords if keyword]
        hint_lower = text_hint.lower() if isinstance(text_hint, str) else None

        results: List[Dict[str, Any]] = []
        for index, chunk in enumerate(chunks[:25]):
            chunk_lower = chunk.lower()
            score = 0

            for keyword in keywords_lower:
                if keyword in chunk_lower:
                    score += 1

            if hint_lower and len(hint_lower) > 3 and hint_lower in chunk_lower:
                score += 2

            if score > 0:
                results.append({
                    'chunk_index': index,
                    'chunk_text': chunk,
                    'relevance_score': score
                })

        results.sort(key=lambda item: item['relevance_score'], reverse=True)
        return results[:top_k]

    def _heuristic_contact_matches(
        self,
        chunks: List[str],
        keywords: List[str],
        values: Any,
        top_k: int = 3,
    ) -> List[Dict[str, Any]]:
        if not chunks:
            return []

        keywords_lower = [keyword.lower() for keyword in keywords if keyword]

        value_tokens: List[str] = []
        if isinstance(values, list):
            value_tokens = [str(value).lower() for value in values if value]
        elif isinstance(values, dict):
            value_tokens = [str(value).lower() for value in values.values() if value]
        elif values:
            value_tokens = [str(values).lower()]

        results: List[Dict[str, Any]] = []
        for index, chunk in enumerate(chunks[:20]):
            chunk_lower = chunk.lower()
            normalized_chunk = re.sub(r"[^a-z0-9@+]+", "", chunk_lower)
            score = 0
            matched_value = False

            for keyword in keywords_lower:
                if keyword in chunk_lower:
                    score += 1

            for token in value_tokens:
                if token and token in chunk_lower:
                    score += 3
                    matched_value = True
                    break
                normalized_token = re.sub(r"[^a-z0-9@+]+", "", token)
                if normalized_token and normalized_token in normalized_chunk:
                    score += 3
                    matched_value = True
                    break

            if score > 0 and matched_value:
                results.append({
                    'chunk_index': index,
                    'chunk_text': chunk,
                    'relevance_score': score
                })

        results.sort(key=lambda item: item['relevance_score'], reverse=True)
        return results[:top_k]

    def _fallback_chunk_scan(self, chunks: List[str], query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        if not chunks or not query or not query.strip():
            return []

        tokens = [token.lower() for token in re.split(r"\W+", query) if len(token) >= 3]
        if not tokens:
            tokens = [query.lower()]

        return self._heuristic_chunk_matches(chunks, tokens, query, top_k=top_k)

    def _dedupe_results(self, results: List[Dict[str, Any]], limit: int = 3) -> List[Dict[str, Any]]:
        deduped: List[Dict[str, Any]] = []
        seen_indices: set[int] = set()

        for item in results:
            idx = int(item.get('chunk_index', -1))
            if idx in seen_indices or idx < 0:
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

    def _filter_contact_results(self, results: List[Dict[str, Any]], values: Any) -> List[Dict[str, Any]]:
        if not results:
            return []

        value_tokens: List[str] = []
        if isinstance(values, list):
            value_tokens = [str(value).lower() for value in values if value]
        elif isinstance(values, dict):
            value_tokens = [str(value).lower() for value in values.values() if value]
        elif values:
            value_tokens = [str(values).lower()]

        if not value_tokens:
            return []

        filtered: List[Dict[str, Any]] = []
        normalized_tokens = [re.sub(r"[^a-z0-9@+]+", "", token) for token in value_tokens]

        for item in results:
            chunk_text = str(item.get('chunk_text', '')).lower()
            normalized_chunk = re.sub(r"[^a-z0-9@+]+", "", chunk_text)

            match_found = False
            for token, normalized_token in zip(value_tokens, normalized_tokens):
                if token and token in chunk_text:
                    match_found = True
                    break
                if normalized_token and normalized_token in normalized_chunk:
                    match_found = True
                    break

            if match_found:
                filtered.append(item)

        return filtered
    
    # ------------------------------------------------------------------
    # Groq Compound integrations
    # ------------------------------------------------------------------
    def _run_live_visit(self, scraped_data: Dict) -> Optional[Dict]:
        url = scraped_data.get('url')
        if not self.groq_client or not url:
            return None
        visit_result = self.groq_client.visit_website(url, instructions="Provide any breaking updates, positioning changes, or noteworthy calls-to-action that may not appear in cached data.")
        if visit_result and visit_result.get('content'):
            return visit_result
        return None

    def _run_live_browser_research(self, url: Optional[str], questions: List[str]) -> Dict[str, Dict]:
        if not self.groq_client or not questions:
            return {}

        results: Dict[str, Dict] = {}
        limit = max(0, self.browser_question_limit)
        if limit == 0:
            return {}

        for question in questions[:limit]:
            if not question.strip():
                continue
            research = self.groq_client.browser_research(question, focus_url=url)
            if research and research.get('content'):
                results[question] = research
        return results
