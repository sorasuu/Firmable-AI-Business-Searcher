"""Tools for the conversational agent to use"""
from typing import Dict, Optional, List, Any
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
import os
from api.scraper import WebsiteScraper


class AgentTools:
    """Collection of tools for the conversational agent"""
    
    def __init__(self, scraper: Optional[WebsiteScraper] = None):
        self.scraper = scraper or WebsiteScraper()
        self.cached_data = {}
        self.base_url = ""
    
    def create_tools(self, url: str, cached_data: Dict) -> List:
        """Create tools for the agent to use"""
        self.cached_data = cached_data
        self.base_url = url
        
        @tool
        def get_business_info(query: str) -> str:
            """Get general business information like industry, company size, location, products, services, or target audience."""
            return self._get_business_info(query)
        
        @tool
        def get_contact_info(query: str) -> str:
            """Get contact information like emails, phone numbers, or social media links."""
            return self._get_contact_info(query)
        
        @tool
        def search_website_content(query: str) -> str:
            """Search the website content for specific information not found in structured data."""
            return self._search_content(query)
        
        @tool
        def get_social_media_links(query: str) -> str:
            """Get social media profiles and links. Use 'all' for all platforms or specify platform name."""
            return self._get_social_links(query)
        
        @tool
        def get_internal_pages(query: str) -> str:
            """Find internal pages like 'about', 'contact', 'team', 'careers', 'pricing'."""
            return self._get_internal_pages(query)
        
        @tool
        def scrape_additional_page(page_url: str) -> str:
            """Scrape a specific page URL when user mentions it. Input should be the URL or path like '/pricing'."""
            return self._scrape_additional_page(page_url)
        
        return [
            get_business_info,
            get_contact_info,
            search_website_content,
            get_social_media_links,
            get_internal_pages,
            scrape_additional_page,
        ]
    
    def _get_business_info(self, query: str) -> str:
        """Get business information from cached insights"""
        insights = self.cached_data.get('insights', {})
        
        query_lower = query.lower()
        
        if 'industry' in query_lower:
            return f"Industry: {insights.get('industry', 'Not available')}"
        elif 'size' in query_lower or 'company' in query_lower:
            return f"Company Size: {insights.get('company_size', 'Not available')}"
        elif 'location' in query_lower or 'where' in query_lower:
            return f"Location: {insights.get('location', 'Not available')}"
        elif 'product' in query_lower or 'service' in query_lower:
            return f"Products/Services: {insights.get('products_services', 'Not available')}"
        elif 'audience' in query_lower or 'customer' in query_lower:
            return f"Target Audience: {insights.get('target_audience', 'Not available')}"
        elif 'usp' in query_lower or 'unique' in query_lower:
            return f"USP: {insights.get('usp', 'Not available')}"
        else:
            # Return a summary
            return f"""Business Summary:
- Industry: {insights.get('industry', 'N/A')}
- Company Size: {insights.get('company_size', 'N/A')}
- Location: {insights.get('location', 'N/A')}
- USP: {insights.get('usp', 'N/A')}"""
    
    def _get_contact_info(self, query: str) -> str:
        """Get contact information"""
        insights = self.cached_data.get('insights', {})
        contact = insights.get('contact_info', {})
        
        query_lower = query.lower()
        
        if 'email' in query_lower:
            emails = contact.get('emails', [])
            return f"Emails: {', '.join(emails) if emails else 'No emails found'}"
        elif 'phone' in query_lower or 'number' in query_lower:
            phones = contact.get('phones', [])
            return f"Phone Numbers: {', '.join(phones) if phones else 'No phone numbers found'}"
        elif 'social' in query_lower:
            social = contact.get('social_media', {})
            if social:
                social_list = [f"{platform}: {links[0]}" for platform, links in social.items() if links]
                return "Social Media:\n" + "\n".join(social_list)
            return "No social media links found"
        else:
            # Return all contact info
            result = []
            if contact.get('emails'):
                result.append(f"Emails: {', '.join(contact['emails'])}")
            if contact.get('phones'):
                result.append(f"Phones: {', '.join(contact['phones'])}")
            if contact.get('social_media'):
                social_list = [f"{platform}: {links[0]}" for platform, links in contact['social_media'].items() if links]
                result.append("Social Media:\n  " + "\n  ".join(social_list))
            return "\n".join(result) if result else "No contact information found"
    
    def _search_content(self, query: str) -> str:
        """Search website content for specific information"""
        scraped = self.cached_data.get('scraped_data', {})
        
        # Search in main content
        main_content = scraped.get('main_content', '')
        chunks = scraped.get('structured_chunks', [])
        
        # Simple keyword search in chunks
        query_lower = query.lower()
        relevant_chunks = []
        
        for chunk in chunks[:10]:  # Search top 10 chunks
            if any(word in chunk.lower() for word in query_lower.split()):
                relevant_chunks.append(chunk)
        
        if relevant_chunks:
            # Return most relevant chunk
            return f"Found information: {relevant_chunks[0][:500]}..."
        
        # Fallback to main content search
        if query_lower in main_content.lower():
            # Find the context around the query
            start_idx = main_content.lower().index(query_lower)
            context_start = max(0, start_idx - 200)
            context_end = min(len(main_content), start_idx + 300)
            return f"Found: ...{main_content[context_start:context_end]}..."
        
        return f"Could not find specific information about '{query}' in the website content."
    
    def _get_social_links(self, query: str) -> str:
        """Get social media links from all_links data"""
        scraped = self.cached_data.get('scraped_data', {})
        all_links = scraped.get('all_links', {})
        social_links = all_links.get('social_media', [])
        
        if not social_links:
            return "No social media links found on the website"
        
        query_lower = query.lower()
        
        if 'all' in query_lower or not query.strip():
            # Return all social links
            result = ["Social Media Links:"]
            for link in social_links[:10]:
                result.append(f"- {link['url']} ({link.get('text', 'Link')})")
            return "\n".join(result)
        else:
            # Filter by platform
            filtered = [link for link in social_links if query_lower in link['url'].lower()]
            if filtered:
                result = [f"Found {len(filtered)} {query} link(s):"]
                for link in filtered[:5]:
                    result.append(f"- {link['url']}")
                return "\n".join(result)
            return f"No {query} links found"
    
    def _get_internal_pages(self, query: str) -> str:
        """Get internal page links"""
        scraped = self.cached_data.get('scraped_data', {})
        all_links = scraped.get('all_links', {})
        
        query_lower = query.lower()
        
        # Check for specific page types
        if 'contact' in query_lower or 'about' in query_lower or 'team' in query_lower:
            contact_pages = all_links.get('contact_pages', [])
            if contact_pages:
                result = ["Contact/About Pages:"]
                for page in contact_pages[:5]:
                    result.append(f"- {page['text']}: {page['url']}")
                return "\n".join(result)
            return "No contact/about pages found"
        
        # Check for pricing, careers, or other specific pages
        if 'pricing' in query_lower or 'price' in query_lower or 'plan' in query_lower:
            internal_pages = all_links.get('internal_pages', [])
            pricing_pages = [p for p in internal_pages if 'pric' in p.get('text', '').lower() or 'pric' in p['url'].lower()]
            if pricing_pages:
                result = ["Pricing Pages Found:"]
                for page in pricing_pages[:5]:
                    result.append(f"- {page.get('text', 'Pricing')}: {page['url']}")
                return "\n".join(result)
            return "No pricing pages found in the internal links. Try using scrape_additional_page with '/pricing' or similar."
        
        if 'career' in query_lower or 'job' in query_lower:
            internal_pages = all_links.get('internal_pages', [])
            career_pages = [p for p in internal_pages if 'career' in p.get('text', '').lower() or 'job' in p.get('text', '').lower() or 'career' in p['url'].lower()]
            if career_pages:
                result = ["Career Pages Found:"]
                for page in career_pages[:5]:
                    result.append(f"- {page.get('text', 'Careers')}: {page['url']}")
                return "\n".join(result)
            return "No career pages found in the internal links."
        
        # Return general internal pages
        internal_pages = all_links.get('internal_pages', [])
        if internal_pages:
            result = ["Internal Pages:"]
            for page in internal_pages[:10]:
                result.append(f"- {page.get('text', 'Page')}: {page['url']}")
            return "\n".join(result)
        
        return "No internal pages found"
    
    def _scrape_additional_page(self, page_url: str) -> str:
        """Scrape an additional page on demand"""
        try:
            from urllib.parse import urlparse
            
            # Handle relative URLs
            if page_url.startswith('/'):
                # Extract base domain from cached URL
                parsed = urlparse(self.base_url)
                page_url = f"{parsed.scheme}://{parsed.netloc}{page_url}"
            elif not page_url.startswith('http'):
                # Assume it's a path relative to base
                page_url = f"{self.base_url.rstrip('/')}/{page_url.lstrip('/')}"
            
            # Validate that we're scraping the same domain as the cached data
            page_parsed = urlparse(page_url)
            base_parsed = urlparse(self.base_url)
            
            if page_parsed.netloc != base_parsed.netloc:
                return f"Error: Cannot scrape {page_url} - it's a different domain than the analyzed website ({self.base_url}). Please ask about pages on {base_parsed.netloc} only."
            
            print(f"[API] Scraping additional page: {page_url}")
            
            # Scrape the page
            page_data = self.scraper.scrape_website(page_url)
            
            # Extract relevant content
            main_content = page_data.get('main_content', '')
            title = page_data.get('title', '')
            
            if not main_content:
                return f"Successfully accessed {page_url} but found no main content."
            
            # Return a summary
            content_preview = main_content[:1500]  # First 1500 chars
            return f"Page: {title}\n\nContent:\n{content_preview}...\n\n[Full page scraped and available]"
            
        except Exception as e:
            return f"Error scraping page {page_url}: {str(e)}"


def create_agent_executor(llm: ChatOpenAI, cached_data: Dict, insights: Dict) -> AgentExecutor:
    """Create an agent executor with tools - using tool calling instead of ReAct"""
    
    # Extract URL from cached_data
    url = cached_data.get('url', '')
    
    # Extract URL from cached_data
    url = cached_data.get('url', '')
    
    # Create agent tools
    agent_tools = AgentTools()
    tools = agent_tools.create_tools(url, cached_data)
    
    # Create prompt
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a helpful AI assistant analyzing website information. 
Use the available tools to answer user questions accurately.

IMPORTANT FORMATTING RULES:
- Always format your responses using Markdown syntax
- Use Markdown tables (| column | column |) for structured data
- NEVER use HTML tags like <br>, <table>, <td>, <tr>, <div>, <span>, etc.
- For multiple items in a table cell, use commas or keep on one line (NO <br> tags)
- Use **bold** and *italic* for emphasis (NOT <b> or <i>)
- Use `code` for inline code and ``` for code blocks
- Use > for blockquotes
- Use - or * for bullet lists on separate lines
- Use 1. 2. 3. for numbered lists
- Use # ## ### for headings

When a user asks about pricing, careers, or any specific page, use the scrape_additional_page tool.
Always provide complete, helpful answers based on the tools' results."""),
        MessagesPlaceholder(variable_name="chat_history", optional=True),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])
    
    # Create the tool calling agent
    agent = create_tool_calling_agent(llm, tools, prompt)
    
    # Create the executor
    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        max_iterations=5,
        handle_parsing_errors=True,
        return_intermediate_steps=False
    )
    
    return agent_executor
