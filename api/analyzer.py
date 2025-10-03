from typing import Any, Dict, List, Optional
import os
from langchain_groq import ChatGroq
from langchain.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from pydantic import BaseModel, Field
import json
import re

from api.groq_services import GroqCompoundClient
from api.chunk_search import ChunkSearcher, ChunkSearchResult
from api.chunk_search import ChunkSearcher, ChunkSearchResult


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
    
    def __init__(self, groq_client: Optional[GroqCompoundClient] = None):
        self.llm = ChatGroq(
            model=os.environ.get("GROQ_MODEL", "openai/gpt-oss-20b"),
            temperature=0.3,
            groq_api_key=os.environ.get("GROQ_API_KEY", "")
        )
        self.groq_client = groq_client or GroqCompoundClient()
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
        """Analyze website content using LangChain"""
        
        # Prepare context from scraped data
        context = self._prepare_context(scraped_data)
        chunks = scraped_data.get('structured_chunks', [])
        chunk_searcher = ChunkSearcher(chunks) if chunks else None
        
        # Get default insights using structured output with source tracking
        default_insights, source_chunks = self._get_default_insights(context, chunks, chunk_searcher)
        
        # Answer custom questions if provided
        custom_insights = {}
        custom_source_chunks = {}
        if custom_questions:
            custom_result = self._answer_custom_questions(context, custom_questions, chunks, chunk_searcher)
            custom_insights = custom_result['answers']
            custom_source_chunks = custom_result['source_chunks']
        
        # Merge source chunks from default insights and custom questions
        all_source_chunks = {**source_chunks}
        for question, chunks_list in custom_source_chunks.items():
            all_source_chunks[question] = chunks_list
        
        # Add source tracking for contact info
        contact_info = scraped_data.get('contact_info', {})
        contact_sources = self._identify_contact_sources(contact_info, chunks, chunk_searcher)
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
        context: str,
        chunks: List[str],
        chunk_searcher: Optional[ChunkSearcher] = None
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
                    source_chunks = self._identify_source_chunks(normalized, chunks, chunk_searcher)
                    
                    return normalized, source_chunks
                except json.JSONDecodeError as je:
                    print(f"[API] JSON parse error: {je}")
            
            # Fallback: try to parse line by line or extract key-value pairs
            fallback_result = self._parse_llm_response_fallback(content)
            normalized = self._normalize_insights(fallback_result)
            source_chunks = self._identify_source_chunks(normalized, chunks, chunk_searcher)
            return normalized, source_chunks
            
        except Exception as e:
            print(f"Analysis error: {str(e)}")
            import traceback
            print(f"Analysis traceback: {traceback.format_exc()}")
            fallback_result = self._default_insight_values()
            fallback_result["error"] = str(e)
            source_chunks = self._identify_source_chunks(fallback_result, chunks, chunk_searcher)
            return fallback_result, source_chunks
    
    def _identify_source_chunks(
        self,
        insights: Dict,
        chunks: List[str],
        chunk_searcher: Optional[ChunkSearcher] = None
    ) -> Dict:
        source_chunks: Dict[str, List[Dict[str, Any]]] = {}
        defaults = self._default_insight_values()

        # Keywords for heuristic fallback when BM25 does not produce matches
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

        for key in heuristic_keywords.keys():
            insight_value = insights.get(key)
            if not insight_value or insight_value == defaults.get(key):
                source_chunks[key] = []
                continue

            bm25_results: List[ChunkSearchResult] = []
            if chunk_searcher and isinstance(insight_value, str):
                bm25_results = chunk_searcher.search(insight_value, top_k=3)

            if bm25_results:
                source_chunks[key] = [
                    {
                        'chunk_index': result.index,
                        'chunk_text': result.text,
                        'relevance_score': round(result.score, 4)
                    }
                    for result in bm25_results
                ]
                continue

            # Fallback heuristic search if BM25 found nothing
            relevant_chunks = []
            keywords = heuristic_keywords[key]
            for i, chunk in enumerate(chunks[:10]):
                chunk_lower = chunk.lower()
                score = 0

                for keyword in keywords:
                    if keyword in chunk_lower:
                        score += 1

                if isinstance(insight_value, str):
                    insight_lower = insight_value.lower()
                    if len(insight_lower) > 3 and insight_lower in chunk_lower:
                        score += 2

                if score > 0:
                    relevant_chunks.append({
                        'chunk_index': i,
                        'chunk_text': chunk,
                        'relevance_score': score
                    })

            relevant_chunks.sort(key=lambda x: x['relevance_score'], reverse=True)
            source_chunks[key] = relevant_chunks[:3]

        return source_chunks
    
    def _identify_contact_sources(
        self,
        contact_info: Dict,
        chunks: List[str],
        chunk_searcher: Optional[ChunkSearcher] = None
    ) -> Dict:
        """Identify source chunks for contact information"""
        source_chunks = {}
        
        # Keywords for contact information
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

            bm25_results: List[ChunkSearchResult] = []
            if chunk_searcher:
                if isinstance(values, list):
                    query = " ".join(str(value) for value in values if value)
                elif isinstance(values, dict):
                    query = " ".join(str(value) for value in values.values() if value)
                else:
                    query = str(values)

                bm25_results = chunk_searcher.search(query, top_k=3) if query else []

            if bm25_results:
                source_chunks[contact_type] = [
                    {
                        'chunk_index': result.index,
                        'chunk_text': result.text,
                        'relevance_score': round(result.score, 4)
                    }
                    for result in bm25_results
                ]
                continue

            relevant_chunks = []
            for i, chunk in enumerate(chunks[:10]):
                chunk_lower = chunk.lower()
                score = 0

                for keyword in keywords:
                    if keyword in chunk_lower:
                        score += 1

                if isinstance(values, list):
                    for value in values:
                        if str(value).lower() in chunk_lower:
                            score += 3
                            break
                elif isinstance(values, dict):
                    for value in values.values():
                        if str(value).lower() in chunk_lower:
                            score += 3
                            break
                else:
                    if str(values).lower() in chunk_lower:
                        score += 3

                if score > 0:
                    relevant_chunks.append({
                        'chunk_index': i,
                        'chunk_text': chunk,
                        'relevance_score': score
                    })

            relevant_chunks.sort(key=lambda x: x['relevance_score'], reverse=True)
            source_chunks[contact_type] = relevant_chunks[:3]
        
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
        context: str,
        questions: List[str],
        chunks: Optional[List[str]] = None,
        chunk_searcher: Optional[ChunkSearcher] = None
    ) -> Dict:
        """Answer custom user questions using LangChain with RAG approach"""
        
        answers: Dict[str, str] = {}
        source_chunks: Dict[str, List[Dict[str, Any]]] = {}

        available_chunks = chunks or []
        searcher = chunk_searcher or (ChunkSearcher(available_chunks) if available_chunks else None)
        
        for question in questions[:5]:  # Limit to 5 questions
            try:
                relevant_context = context
                relevant_results: List[ChunkSearchResult] = []

                if searcher:
                    relevant_results = searcher.search(question, top_k=3)
                    if relevant_results:
                        relevant_context = "\n\n".join(result.text for result in relevant_results)
                        print(f"[API] Using {len(relevant_results)} BM25 chunks for question: {question[:50]}...")
                
                # Create prompt for Q&A with retrieved context
                qa_prompt = ChatPromptTemplate.from_messages([
                    ("system", "You are a helpful assistant that answers questions about websites based on their content. Provide clear, concise answers in 1-3 sentences. Use markdown formatting for better readability when appropriate (lists, bold, etc.). If you cannot find the information in the provided content, say so clearly."),
                    ("human", """Website Content:
{context}

Question: {question}

Answer:""")
                ])
                
                # Create chain
                qa_chain = qa_prompt | self.llm
                
                response = qa_chain.invoke({
                    "context": relevant_context,
                    "question": question
                })
                
                answer_text = response.content.strip()
                answers[question] = answer_text
                
                # Track source chunks for this question
                if relevant_results:
                    source_chunks[question] = [
                        {
                            'chunk_index': result.index,
                            'chunk_text': available_chunks[result.index] if 0 <= result.index < len(available_chunks) else result.text,
                            'relevance_score': round(result.score, 4) if result.score else 1.0
                        }
                        for result in relevant_results
                    ]
                else:
                    source_chunks[question] = []
                
            except Exception as e:
                answers[question] = f"Unable to answer: {str(e)}"
                source_chunks[question] = []
        
        return {
            'answers': answers,
            'source_chunks': source_chunks
        }
    
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
