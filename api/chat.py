from typing import Dict, List, Optional
import os
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.schema import HumanMessage, AIMessage, SystemMessage
from langchain.memory import ConversationBufferMemory

class ConversationalAgent:
    def __init__(self):
        self.llm = ChatOpenAI(
            model="openai/gpt-oss-20b",
            temperature=0.7,
            api_key=os.environ.get("GROQ_API_KEY", ""),
            base_url="https://api.groq.com/openai/v1"
        )
        
        # Simple in-memory cache for website data
        self.website_cache = {}
    
    def cache_website_data(self, url: str, scraped_data: Dict, insights: Dict):
        """Cache website data for conversational context"""
        self.website_cache[url] = {
            'scraped_data': scraped_data,
            'insights': insights
        }
    
    def get_cached_data(self, url: str) -> Optional[Dict]:
        """Retrieve cached website data"""
        return self.website_cache.get(url)
    
    def chat(self, url: str, query: str, conversation_history: Optional[List[Dict]] = None) -> str:
        """
        Handle conversational queries about a website using LangChain.
        Uses cached data if available, otherwise returns error.
        """
        
        # Get cached data
        cached = self.get_cached_data(url)
        
        if not cached:
            return "I don't have information about this website yet. Please analyze it first using the /api/analyze endpoint."
        
        # Prepare context from cached data
        context = self._prepare_conversation_context(cached)
        
        # Build messages for LangChain
        messages = [
            SystemMessage(content=f"""You are an AI assistant that helps users understand websites and businesses. 
You have analyzed a website and have the following information:

{context}

Answer user questions based on this information. Be conversational, helpful, and concise. 
If you don't have specific information to answer a question, say so honestly.""")
        ]
        
        # Add conversation history if provided
        if conversation_history:
            for msg in conversation_history[-5:]:  # Keep last 5 messages for context
                role = msg.get("role", "user")
                content = msg.get("content", "")
                
                if role == "user":
                    messages.append(HumanMessage(content=content))
                elif role == "assistant":
                    messages.append(AIMessage(content=content))
        
        # Add current query
        messages.append(HumanMessage(content=query))
        
        try:
            # Use LangChain to generate response
            response = self.llm.invoke(messages)
            return response.content.strip()
            
        except Exception as e:
            return f"I encountered an error processing your question: {str(e)}"
    
    def _prepare_conversation_context(self, cached_data: Dict) -> str:
        """Prepare context string from cached website data"""
        
        scraped = cached_data.get('scraped_data', {})
        insights = cached_data.get('insights', {})
        
        context_parts = [
            f"Website URL: {scraped.get('url', 'N/A')}",
            f"Title: {scraped.get('title', 'N/A')}",
            f"\nBusiness Insights:",
            f"- Industry: {insights.get('industry', 'N/A')}",
            f"- Company Size: {insights.get('company_size', 'N/A')}",
            f"- Location: {insights.get('location', 'N/A')}",
            f"- USP: {insights.get('usp', 'N/A')}",
            f"- Products/Services: {insights.get('products_services', 'N/A')}",
            f"- Target Audience: {insights.get('target_audience', 'N/A')}",
        ]
        
        # Add contact info if available
        contact = insights.get('contact_info', {})
        if contact.get('emails'):
            context_parts.append(f"- Emails: {', '.join(contact['emails'])}")
        if contact.get('phones'):
            context_parts.append(f"- Phones: {', '.join(contact['phones'])}")
        
        # Add main content snippet
        main_content = scraped.get('main_content', '')[:1500]
        if main_content:
            context_parts.append(f"\nContent Snippet:\n{main_content}")
        
        return "\n".join(context_parts)
