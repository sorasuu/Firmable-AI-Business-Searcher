from typing import Dict, List, Optional
import os
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from langchain.output_parsers import PydanticOutputParser
from langchain.chains import LLMChain
from pydantic import BaseModel, Field
import json

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
    def __init__(self):
        self.llm = ChatOpenAI(
            model="openai/gpt-oss-20b",
            temperature=0.3,
            api_key=os.environ.get("GROQ_API_KEY", ""),
            base_url="https://api.groq.com/openai/v1"
        )
        
        # Setup output parser
        self.parser = PydanticOutputParser(pydantic_object=BusinessInsights)
    
    def analyze_website(self, scraped_data: Dict, custom_questions: Optional[List[str]] = None) -> Dict:
        """Analyze website content using LangChain"""
        
        # Prepare context from scraped data
        context = self._prepare_context(scraped_data)
        
        # Get default insights using structured output
        default_insights = self._get_default_insights(context)
        
        # Answer custom questions if provided
        custom_insights = {}
        if custom_questions:
            custom_insights = self._answer_custom_questions(context, custom_questions)
        
        return {
            **default_insights,
            'custom_answers': custom_insights,
            'contact_info': scraped_data.get('contact_info', {})
        }
    
    def _prepare_context(self, scraped_data: Dict) -> str:
        """Prepare context string from scraped data"""
        context_parts = [
            f"Website URL: {scraped_data.get('url', 'N/A')}",
            f"Title: {scraped_data.get('title', 'N/A')}",
            f"\nHeadings:",
        ]
        
        for heading in scraped_data.get('headings', [])[:8]:
            context_parts.append(f"- {heading.get('text', '')}")
        
        context_parts.append(f"\nMain Content:\n{scraped_data.get('main_content', '')[:4000]}")
        
        # Add footer content if available
        footer_content = scraped_data.get('footer_content', '').strip()
        if footer_content:
            context_parts.append(f"\nFooter Content:\n{footer_content}")
        
        return "\n".join(context_parts)
    
    def _get_default_insights(self, context: str) -> Dict:
        """Extract default business insights using LangChain"""
        
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
                    return parsed
                except json.JSONDecodeError as je:
                    print(f"[API] JSON parse error: {je}")
            
            # Fallback: try to parse line by line or extract key-value pairs
            return self._parse_llm_response_fallback(content)
            
        except Exception as e:
            print(f"Analysis error: {str(e)}")
            import traceback
            print(f"Analysis traceback: {traceback.format_exc()}")
            return {
                "industry": "Unable to determine",
                "company_size": "Unable to determine", 
                "location": "Not found",
                "usp": "Unable to extract",
                "products_services": "Unable to extract",
                "target_audience": "Unable to determine",
                "sentiment": "neutral",
                "error": str(e)
            }
            
        except Exception as e:
            print(f"Analysis error: {str(e)}")
            print(f"Analysis error type: {type(e)}")
            import traceback
            print(f"Analysis traceback: {traceback.format_exc()}")
            return {
                "industry": "Unable to determine",
                "company_size": "Unable to determine",
                "location": "Not found",
                "usp": "Unable to extract",
                "products_services": "Unable to extract",
                "target_audience": "Unable to determine",
                "sentiment": "neutral",
                "error": str(e)
            }
    
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
    
    def _answer_custom_questions(self, context: str, questions: List[str]) -> Dict:
        """Answer custom user questions using LangChain"""
        
        answers = {}
        
        # Create prompt for Q&A
        qa_prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a helpful assistant that answers questions about websites based on their content. Provide clear, concise answers in 1-3 sentences."),
            ("human", """Website Content:
{context}

Question: {question}

Answer:""")
        ])
        
        # Create chain
        qa_chain = qa_prompt | self.llm
        
        for question in questions[:5]:  # Limit to 5 questions
            try:
                response = qa_chain.invoke({
                    "context": context,
                    "question": question
                })
                
                answers[question] = response.content.strip()
                
            except Exception as e:
                answers[question] = f"Unable to answer: {str(e)}"
        
        return answers
