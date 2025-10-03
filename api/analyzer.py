from typing import Dict, List, Optional
import os
from langchain_groq import ChatGroq
from langchain.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from pydantic import BaseModel, Field
import json
import re

from api.groq_services import GroqCompoundClient


# Define structured output models
class BusinessInsights(BaseModel):
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
    
    def analyze_website(self, scraped_data: Dict, custom_questions: Optional[List[str]] = None) -> Dict:
        """Analyze website content using LangChain"""
        
        # Prepare context from scraped data
        context = self._prepare_context(scraped_data)
        chunks = scraped_data.get('structured_chunks', [])
        
        # Get default insights using structured output with source tracking
        default_insights, source_chunks = self._get_default_insights(context, chunks)
        
        # Answer custom questions if provided
        custom_insights = {}
        custom_source_chunks = {}
        if custom_questions:
            custom_result = self._answer_custom_questions(context, custom_questions, chunks)
            custom_insights = custom_result['answers']
            custom_source_chunks = custom_result['source_chunks']
        
        # Merge source chunks from default insights and custom questions
        all_source_chunks = {**source_chunks}
        for question, chunks_list in custom_source_chunks.items():
            all_source_chunks[question] = chunks_list
        
        # Add source tracking for contact info
        contact_info = scraped_data.get('contact_info', {})
        contact_sources = self._identify_contact_sources(contact_info, chunks)
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
    
    def _get_default_insights(self, context: str, chunks: List[str]) -> tuple[Dict, Dict]:
        """Extract default business insights using LangChain with source tracking"""
        
        try:
            # Create prompt template
            system_template = """You are an expert business analyst specializing in website analysis. 
Analyze the provided website content and extract key business insights.
Return your analysis as a JSON object with these exact keys:
- industry: Primary industry or sector
- company_size: Estimated company size (startup/small/medium/large/enterprise)
- location: Company headquarters or primary location
- usp: Unique selling proposition
- products_services: Main products or services offered
- target_audience: Primary customer demographic or market segment
- sentiment: Overall tone and sentiment of the website

Be specific, concise, and accurate. Keep each field under 200 characters."""

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
                    source_chunks = self._identify_source_chunks(parsed, chunks)
                    
                    return parsed, source_chunks
                except json.JSONDecodeError as je:
                    print(f"[API] JSON parse error: {je}")
            
            # Fallback: try to parse line by line or extract key-value pairs
            fallback_result = self._parse_llm_response_fallback(content)
            source_chunks = self._identify_source_chunks(fallback_result, chunks)
            return fallback_result, source_chunks
            
        except Exception as e:
            print(f"Analysis error: {str(e)}")
            import traceback
            print(f"Analysis traceback: {traceback.format_exc()}")
            fallback_result = {
                "industry": "Unable to determine",
                "company_size": "Unable to determine", 
                "location": "Not found",
                "usp": "Unable to extract",
                "products_services": "Unable to extract",
                "target_audience": "Unable to determine",
                "sentiment": "neutral",
                "error": str(e)
            }
            source_chunks = self._identify_source_chunks(fallback_result, chunks)
            return fallback_result, source_chunks
    
    def _identify_source_chunks(self, insights: Dict, chunks: List[str]) -> Dict:
        source_chunks = {}
        
        # Keywords for each insight type
        insight_keywords = {
            'industry': ['industry', 'sector', 'business', 'company', 'market', 'field'],
            'company_size': ['employee', 'team', 'size', 'company', 'startup', 'enterprise', 'small', 'large', 'medium'],
            'location': ['location', 'headquarters', 'office', 'address', 'city', 'country', 'based'],
            'usp': ['unique', 'selling', 'proposition', 'advantage', 'differentiator', 'why choose', 'benefit'],
            'products_services': ['product', 'service', 'solution', 'offering', 'platform', 'tool', 'software'],
            'target_audience': ['customer', 'client', 'user', 'audience', 'market', 'target', 'who we serve'],
            'sentiment': ['professional', 'innovative', 'reliable', 'trusted', 'quality', 'experience']
        }
        
        for insight_key, keywords in insight_keywords.items():
            if insight_key in insights and insights[insight_key] and insights[insight_key] != "Unable to determine":
                relevant_chunks = []
                
                for i, chunk in enumerate(chunks[:10]):  # Check top 10 chunks
                    chunk_lower = chunk.lower()
                    score = 0
                    
                    # Count keyword matches
                    for keyword in keywords:
                        if keyword in chunk_lower:
                            score += 1
                    
                    # Also check if insight value appears in chunk
                    insight_value = str(insights[insight_key]).lower()
                    if len(insight_value) > 3 and insight_value in chunk_lower:
                        score += 2
                    
                    if score > 0:
                        relevant_chunks.append({
                            'chunk_index': i,
                            'chunk_text': chunk,
                            'relevance_score': score
                        })
                
                # Sort by relevance score and take top 3
                relevant_chunks.sort(key=lambda x: x['relevance_score'], reverse=True)
                source_chunks[insight_key] = relevant_chunks[:3]
            else:
                source_chunks[insight_key] = []
        
        return source_chunks
    
    def _identify_contact_sources(self, contact_info: Dict, chunks: List[str]) -> Dict:
        """Identify source chunks for contact information"""
        source_chunks = {}
        
        # Keywords for contact information
        contact_keywords = {
            'emails': ['email', 'contact', 'mail', '@', 'support', 'info', 'hello'],
            'phones': ['phone', 'tel', 'call', 'contact', 'mobile', 'number', '+', '('],
            'social_media': ['social', 'facebook', 'twitter', 'linkedin', 'instagram', 'youtube', 'follow']
        }
        
        for contact_type, keywords in contact_keywords.items():
            if contact_type in contact_info and contact_info[contact_type]:
                relevant_chunks = []
                
                for i, chunk in enumerate(chunks[:10]):  # Check top 10 chunks
                    chunk_lower = chunk.lower()
                    score = 0
                    
                    # Count keyword matches
                    for keyword in keywords:
                        if keyword in chunk_lower:
                            score += 1
                    
                    # Check if any contact values appear in chunk
                    contact_values = contact_info[contact_type]
                    if isinstance(contact_values, list):
                        for value in contact_values:
                            if str(value).lower() in chunk_lower:
                                score += 3  # Higher score for direct matches
                                break
                    elif isinstance(contact_values, dict):
                        for value in contact_values.values():
                            if str(value).lower() in chunk_lower:
                                score += 3
                                break
                    else:
                        if str(contact_values).lower() in chunk_lower:
                            score += 3
                    
                    if score > 0:
                        relevant_chunks.append({
                            'chunk_index': i,
                            'chunk_text': chunk,
                            'relevance_score': score
                        })
                
                # Sort by relevance score and take top 3
                relevant_chunks.sort(key=lambda x: x['relevance_score'], reverse=True)
                source_chunks[contact_type] = relevant_chunks[:3]
            else:
                source_chunks[contact_type] = []
        
        return source_chunks
    
    def _parse_llm_response_fallback(self, content: str) -> Dict:
        """Fallback parser for LLM responses that aren't valid JSON"""
        try:
            # Initialize with defaults
            result = {
                "industry": "Unable to determine",
                "company_size": "Unable to determine",
                "location": "Not found", 
                "usp": "Unable to extract",
                "products_services": "Unable to extract",
                "target_audience": "Unable to determine",
                "sentiment": "neutral"
            }
            
            # Try to extract information using regex patterns
            import re
            
            # Look for key-value patterns
            patterns = {
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
            return {
                "industry": "Unable to determine",
                "company_size": "Unable to determine",
                "location": "Not found",
                "usp": "Unable to extract",
                "products_services": "Unable to extract", 
                "target_audience": "Unable to determine",
                "sentiment": "neutral",
                "error": f"Parsing failed: {str(e)}"
            }
    
    def _answer_custom_questions(self, context: str, questions: List[str], chunks: Optional[List[str]] = None) -> Dict:
        """Answer custom user questions using LangChain with RAG approach"""
        
        answers = {}
        source_chunks = {}
        
        # Use chunks if available for better context retrieval
        available_chunks = chunks or []
        
        for question in questions[:5]:  # Limit to 5 questions
            try:
                # If we have chunks, find the most relevant ones
                relevant_context = context
                relevant_chunk_indices = []
                if available_chunks:
                    relevant_chunks = self._find_relevant_chunks(question, available_chunks)
                    if relevant_chunks:
                        relevant_context = "\n\n".join(relevant_chunks[:3])  # Use top 3 chunks
                        # Track which chunk indices were used
                        for chunk in relevant_chunks[:3]:
                            for i, orig_chunk in enumerate(available_chunks):
                                if chunk == orig_chunk:
                                    relevant_chunk_indices.append(i)
                                    break
                        print(f"[API] Using {len(relevant_chunks)} relevant chunks for question: {question[:50]}...")
                
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
                if relevant_chunk_indices:
                    source_chunks[question] = [
                        {
                            'chunk_index': idx,
                            'chunk_text': available_chunks[idx],
                            'relevance_score': 1  # Simple score since we already filtered relevant chunks
                        }
                        for idx in relevant_chunk_indices[:3]  # Top 3 chunks
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
    
    def _find_relevant_chunks(self, question: str, chunks: List[str]) -> List[str]:
        """Find chunks most relevant to the question using simple keyword matching"""
        question_lower = question.lower()
        question_words = set(re.findall(r'\b\w+\b', question_lower))
        
        # Remove common stop words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must', 'can', 'what', 'when', 'where', 'why', 'how', 'who', 'which'}
        question_words = question_words - stop_words
        
        chunk_scores = []
        for chunk in chunks:
            chunk_lower = chunk.lower()
            score = 0
            
            # Count keyword matches
            for word in question_words:
                if word in chunk_lower:
                    score += 1
            
            # Boost score for exact phrase matches
            if question_lower in chunk_lower:
                score += 10
                
            chunk_scores.append((chunk, score))
        
        # Sort by score and return top chunks
        chunk_scores.sort(key=lambda x: x[1], reverse=True)
        return [chunk for chunk, score in chunk_scores if score > 0][:5]  # Return top 5 relevant chunks

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
