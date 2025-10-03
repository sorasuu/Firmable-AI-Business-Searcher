from typing import Dict, List, Optional
import os
from langchain_groq import ChatGroq
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.schema import HumanMessage, AIMessage, SystemMessage
from langchain.memory import ConversationBufferMemory
from api.agent_tools import create_agent_executor
from api.groq_services import GroqCompoundClient

class ConversationalAgent:
    def __init__(self, groq_client: Optional[GroqCompoundClient] = None):
        self.llm = ChatGroq(
            model=os.environ.get("GROQ_MODEL", "openai/gpt-oss-20b"),
            temperature=0.2,
            groq_api_key=os.environ.get("GROQ_API_KEY", "")
        )
        self.groq_client = groq_client or GroqCompoundClient()
        
        # Simple in-memory cache for website data
        self.website_cache = {}
        self.use_agent_tools = True  # Enable agent with tool calling
    
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
        Handle conversational queries about a website using agent with tool calling.
        Uses cached data if available, otherwise returns error.
        """
        
        # Get cached data
        cached = self.get_cached_data(url)
        
        if not cached:
            return "I don't have information about this website yet. Please analyze it first using the /api/analyze endpoint."
        
        try:
            # Create agent executor with the scraped data
            agent_executor = create_agent_executor(
                self.llm,
                cached.get('scraped_data', {}),
                cached.get('insights', {}),
                groq_client=self.groq_client
            )
            
            # Convert history to LangChain format
            chat_history = []
            if conversation_history:
                for msg in conversation_history[-5:]:  # Keep last 5 messages
                    if msg.get('role') == 'user':
                        chat_history.append(HumanMessage(content=msg.get('content', '')))
                    elif msg.get('role') == 'assistant':
                        chat_history.append(AIMessage(content=msg.get('content', '')))
            
            # Invoke agent with tool calling
            result = agent_executor.invoke({
                "input": query,
                "chat_history": chat_history
            })
            
            return result['output']
            
        except Exception as e:
            print(f"[API] Agent error: {str(e)}")
            import traceback
            traceback.print_exc()
            
            # Fallback to basic LLM response
            context = self._prepare_conversation_context(cached)
            messages = [
                SystemMessage(content=f"""You are an AI assistant that helps users understand websites and businesses. 
You have analyzed a website and have the following information:

{context}

IMPORTANT FORMATTING RULES:
- Always format your responses using Markdown syntax
- Use Markdown tables (| column | column |) instead of HTML tables
- NEVER use HTML tags like <br>, <table>, <td>, <tr>, <div>, <span>, etc.
- For line breaks in table cells, just use a single line or separate with commas
- Use **bold** and *italic* for emphasis
- Use `code` for inline code
- Use - or * for bullet lists on new lines
- Use # ## ### for headings

Answer user questions based on this information. Be conversational, helpful, and concise. 
If you don't have specific information to answer a question, say so honestly.""")
            ]
            
            if conversation_history:
                for msg in conversation_history[-5:]:
                    role = msg.get("role", "user")
                    content = msg.get("content", "")
                    if role == "user":
                        messages.append(HumanMessage(content=content))
                    elif role == "assistant":
                        messages.append(AIMessage(content=content))
            
            messages.append(HumanMessage(content=query))
            
            try:
                response = self.llm.invoke(messages)
                return response.content.strip()
            except Exception as fallback_error:
                return f"I encountered an error processing your question: {str(fallback_error)}"
    
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

        live_visit = insights.get('groq_live_visit')
        if isinstance(live_visit, dict) and live_visit.get('content'):
            context_parts.append("\nLive Website Snapshot (Groq Visit):")
            context_parts.append(live_visit['content'][:1500])

        live_browser = insights.get('groq_browser_research')
        if isinstance(live_browser, dict) and live_browser:
            context_parts.append("\nLive Browser Research Highlights:")
            for question, data in list(live_browser.items())[:2]:
                if isinstance(data, dict) and data.get('content'):
                    context_parts.append(f"- {question}: {data['content'][:400]}")
        
        # Add main content snippet
        main_content = scraped.get('main_content', '')[:1500]
        if main_content:
            context_parts.append(f"\nContent Snippet:\n{main_content}")
        
        return "\n".join(context_parts)
