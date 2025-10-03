"""Tools for the conversational agent to use"""
from typing import Dict, Optional, List, Any
from langchain_core.tools import tool
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.language_models import BaseChatModel
import os
from urllib.parse import urljoin
from api.scraper import WebsiteScraper
from api.groq_services import GroqCompoundClient


class AgentTools:
    """Collection of tools for the conversational agent"""
    
    def __init__(self, scraper: Optional[WebsiteScraper] = None, groq_client: Optional[GroqCompoundClient] = None):
        self.scraper = scraper or WebsiteScraper()
        self.cached_data = {}
        self.base_url = ""
        self.additional_pages = {}  # Store additional scraped pages
        self.groq_client = groq_client
    
    def create_tools(self, url: str, cached_data: Dict) -> List:
        """Create tools for the agent to use"""
        self.cached_data = cached_data
        self.base_url = url
        
        @tool
        def get_business_info(query: str) -> str:
            """Get business information like industry, company size, location, products, services, or target audience. Use this for business overview questions."""
            return self._get_business_info(query)
        
        @tool
        def get_contact_info(query: str) -> str:
            """Get contact information like emails, phone numbers, or social media links. Use this for contact-related questions."""
            return self._get_contact_info(query)
        
        @tool
        def search_website_content(query: str) -> str:
            """Search all website content for specific information. This is the most comprehensive search tool - use it first for most queries."""
            return self._search_content(query)
        
        @tool
        def get_social_media_links(query: str) -> str:
            """Get social media profiles and links. Use 'all' for all platforms or specify platform name."""
            return self._get_social_links(query)
        
        @tool
        def get_internal_pages(query: str) -> str:
            """Find internal pages like 'about', 'contact', 'team', 'careers', 'pricing'. Use this to discover available pages."""
            return self._get_internal_pages(query)
        
        @tool
        def scrape_additional_page(page_url: str) -> str:
            """Scrape a specific page URL when user mentions it. Input should be the URL or path like '/pricing'. Use this when you need content from a specific page."""
            return self._scrape_additional_page(page_url)
        
        tools_list = [
            get_business_info,
            get_contact_info,
            search_website_content,
            get_social_media_links,
            get_internal_pages,
            scrape_additional_page,
        ]

        groq_tools = []

        if self._is_live_visit_enabled():
            @tool
            def live_visit_page(instructions: str) -> str:
                """Run a live Groq Visit Website call. Provide optional instructions or a URL path (defaults to base URL)."""
                return self._live_visit(instructions)

            groq_tools.append(live_visit_page)

        if self._is_browser_automation_enabled():
            @tool
            def live_browser_research(question: str) -> str:
                """Use Groq browser automation for up-to-date answers. Provide the research question."""
                return self._live_browser_research(question)

            groq_tools.append(live_browser_research)

        return tools_list + groq_tools
    
    def _get_business_info(self, query: str) -> str:
        """Get business information from cached insights and content"""
        insights = self.cached_data.get('insights', {})
        scraped = self.cached_data.get('scraped_data', {})
        
        query_lower = query.lower()
        
        # First check insights
        if 'industry' in query_lower:
            industry = insights.get('industry', 'Not available')
            if industry != 'Not available':
                return f"Industry: {industry}"
        elif 'size' in query_lower or 'company' in query_lower:
            size = insights.get('company_size', 'Not available')
            if size != 'Not available':
                return f"Company Size: {size}"
        elif 'location' in query_lower or 'where' in query_lower or 'office' in query_lower or 'address' in query_lower:
            location = insights.get('location', 'Not available')
            if location != 'Not available':
                return f"Location: {location}"
        elif 'product' in query_lower or 'service' in query_lower:
            products = insights.get('products_services', 'Not available')
            if products != 'Not available':
                return f"Products/Services: {products}"
        elif 'audience' in query_lower or 'customer' in query_lower:
            audience = insights.get('target_audience', 'Not available')
            if audience != 'Not available':
                return f"Target Audience: {audience}"
        elif 'usp' in query_lower or 'unique' in query_lower:
            usp = insights.get('usp', 'Not available')
            if usp != 'Not available':
                return f"USP: {usp}"
        
        # If not found in insights, search content
        return self._search_content(query)
    
    def _get_contact_info(self, query: str) -> str:
        """Get contact information from insights and content"""
        insights = self.cached_data.get('insights', {})
        contact = insights.get('contact_info', {})
        
        query_lower = query.lower()
        
        # Check insights first
        if 'email' in query_lower:
            emails = contact.get('emails', [])
            if emails:
                return f"Emails: {', '.join(emails)}"
        elif 'phone' in query_lower or 'number' in query_lower:
            phones = contact.get('phones', [])
            if phones:
                return f"Phone Numbers: {', '.join(phones)}"
        elif 'social' in query_lower:
            social = contact.get('social_media', {})
            if social:
                social_list = [f"{platform}: {links[0]}" for platform, links in social.items() if links]
                return "Social Media:\n" + "\n".join(social_list)
        
        # If not found in insights, search content
        return self._search_content(query)
    
    def _search_content(self, query: str) -> str:
        """Search website content for specific information using Firecrawl data"""
        scraped = self.cached_data.get('scraped_data', {})
        
        # Search in markdown content (cleaner than HTML)
        markdown_content = scraped.get('markdown_content', '')
        chunks = scraped.get('structured_chunks', [])
        
        # Also search additional pages
        all_content = [markdown_content]
        all_chunks = list(chunks)
        
        for page_url, page_data in self.additional_pages.items():
            page_markdown = page_data.get('markdown_content', '')
            page_chunks = page_data.get('structured_chunks', [])
            all_content.append(page_markdown)
            all_chunks.extend(page_chunks)
        
        # Enhanced search with synonyms and related terms
        query_lower = query.lower().strip()
        search_terms = [query_lower]
        
        # Add related terms for common queries
        if query_lower in ['plan', 'plans', 'pricing', 'price', 'cost', 'subscription', 'package']:
            search_terms.extend(['plan', 'plans', 'pricing', 'price', 'cost', 'subscription', 'package', 'tier', 'rate', 'fee'])
        elif query_lower in ['contact', 'email', 'phone', 'reach']:
            search_terms.extend(['contact', 'email', 'phone', 'reach', 'support', 'help'])
        elif query_lower in ['about', 'company', 'team', 'story']:
            search_terms.extend(['about', 'company', 'team', 'story', 'mission', 'vision'])
        elif query_lower in ['career', 'job', 'work', 'employment']:
            search_terms.extend(['career', 'job', 'work', 'employment', 'position', 'opening'])
        
        # Simple keyword search in chunks
        relevant_chunks = []
        
        for i, chunk in enumerate(all_chunks[:50]):  # Search more chunks
            chunk_lower = chunk.lower()
            if any(term in chunk_lower for term in search_terms):
                relevant_chunks.append((i, chunk))
        
        if relevant_chunks:
            # Return most relevant chunk with context
            chunk_idx, chunk_text = relevant_chunks[0]
            page_info = ""
            if chunk_idx >= len(chunks):
                # This chunk is from an additional page
                additional_pages = list(self.additional_pages.keys())
                page_idx = (chunk_idx - len(chunks)) // 10  # Rough estimate
                if page_idx < len(additional_pages):
                    page_info = f" (from {additional_pages[page_idx]})"
            
            return f"Found information{page_info} (from chunk {chunk_idx + 1}):\n\n{chunk_text[:1000]}..."
        
        # Fallback to searching all markdown content with enhanced terms
        combined_content = '\n\n'.join(all_content)
        combined_lower = combined_content.lower()
        
        for term in search_terms:
            if term in combined_lower:
                # Find the context around the first matching term
                term_idx = combined_lower.index(term)
                context_start = max(0, term_idx - 300)
                context_end = min(len(combined_content), term_idx + 600)
                
                # Extract the relevant section
                context = combined_content[context_start:context_end]
                
                # Try to find sentence or paragraph boundaries for better context
                start_pos = context.find('\n\n')
                if start_pos != -1 and start_pos < 100:
                    context = context[start_pos+2:]
                
                return f"Found information about '{query}':\n\n...{context}..."
        
        return f"Could not find specific information about '{query}' in the website content. Try rephrasing your question or ask about a different topic."
    
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
            
            # Store the full page data for future searches
            self.additional_pages[page_url] = page_data
            
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

    # ------------------------------------------------------------------
    # Live Groq helpers
    # ------------------------------------------------------------------
    def _is_live_visit_enabled(self) -> bool:
        return bool(self.groq_client and self.groq_client.is_available and self.groq_client.enable_visit)

    def _is_browser_automation_enabled(self) -> bool:
        return bool(self.groq_client and self.groq_client.is_available and self.groq_client.enable_browser_automation)

    def _derive_target_url_and_instructions(self, instructions: str) -> tuple[str, Optional[str]]:
        instructions = (instructions or "").strip()
        target_url = self.base_url
        extra_instructions = instructions or None

        if instructions:
            tokens = instructions.split()
            url_token = next((t for t in tokens if t.startswith("http://") or t.startswith("https://")), None)
            if url_token:
                target_url = url_token
                extra_instructions = instructions.replace(url_token, "").strip() or None
            else:
                path_token = next((t for t in tokens if t.startswith("/")), None)
                if path_token:
                    target_url = urljoin(self.base_url, path_token)
                    extra_instructions = instructions.replace(path_token, "").strip() or None
                else:
                    if instructions.startswith("/"):
                        target_url = urljoin(self.base_url, instructions)
                        extra_instructions = None
                    elif instructions.lower().startswith("url:"):
                        specified = instructions[4:].strip()
                        if specified.startswith("http"):
                            target_url = specified
                            extra_instructions = None
                        else:
                            target_url = urljoin(self.base_url, specified)
                            extra_instructions = None

        return target_url, extra_instructions

    def _live_visit(self, instructions: str) -> str:
        if not self._is_live_visit_enabled():
            return "Live Groq Visit tooling is disabled or unavailable."

        url, extra = self._derive_target_url_and_instructions(instructions)
        result = self.groq_client.visit_website(url, extra)
        if not result or not result.get('content'):
            return "Unable to retrieve live website content right now."

        response_lines = [result['content'].strip()]
        executed = result.get('executed_tools') or []
        if executed:
            response_lines.append("\n_Live visit executed via Groq Compound tools._")
        return "\n".join([line for line in response_lines if line]).strip()

    def _live_browser_research(self, question: str) -> str:
        if not self._is_browser_automation_enabled():
            return "Browser automation tooling is disabled or unavailable."

        question = (question or "").strip()
        if not question:
            return "Please provide a research question or topic."

        research = self.groq_client.browser_research(question, focus_url=self.base_url)
        if not research or not research.get('content'):
            return "No live research results were returned."

        response_lines = [research['content'].strip()]
        executed = research.get('executed_tools') or []
        if executed:
            response_lines.append("\n_Live browser automation executed for additional context._")
        return "\n".join([line for line in response_lines if line]).strip()


def create_agent_executor(llm: BaseChatModel, cached_data: Dict, insights: Dict, *, groq_client: Optional[GroqCompoundClient] = None) -> AgentExecutor:
    """Create an agent executor with tools - using tool calling instead of ReAct"""
    
    # Extract URL from cached_data
    url = cached_data.get('url', '')
    
    # Extract URL from cached_data
    url = cached_data.get('url', '')
    
    # Create agent tools
    agent_tools = AgentTools(groq_client=groq_client)
    tools = agent_tools.create_tools(url, cached_data)
    
    live_tool_notes: List[str] = []
    if groq_client and groq_client.is_available and groq_client.enable_visit:
        live_tool_notes.append("6. Use live_visit_page for the freshest version of a page or to confirm details that might have changed.")
    if groq_client and groq_client.is_available and groq_client.enable_browser_automation:
        live_tool_notes.append("7. Use live_browser_research when you need up-to-date information from across the web.")
    live_tool_text = ("\n" + "\n".join(live_tool_notes)) if live_tool_notes else ""

    # Create prompt
    prompt = ChatPromptTemplate.from_messages([
        ("system", f"""You are a helpful AI assistant analyzing website information.

TOOL USAGE STRATEGY:
1. Start with search_website_content for most queries - it searches all available content
2. Use get_business_info only for specific business questions (industry, size, location, products)
3. Use get_contact_info only for contact-related questions (email, phone, social media)
4. Use scrape_additional_page when you need content from specific pages like /pricing, /about, /contact
5. Use get_internal_pages to discover what pages are available{live_tool_text}

IMPORTANT RULES:
- If search_website_content finds the information, use that answer
- Don't call multiple search tools for the same query
- When you have enough information to answer, provide a complete answer and stop
- If you can't find information, say so clearly rather than trying more tools
- For location/address questions, try search_website_content first, then get_business_info

IMPORTANT FORMATTING RULES:
- Always format your responses using Markdown syntax
- Use Markdown tables (| column | column |) for structured data
- NEVER use HTML tags like <br>, <table>, <td>, <tr>, <div>, <span>, etc.
- For multiple items in a table cell, use commas or keep on one line
- Use **bold** and *italic* for emphasis
- Use `code` for inline code and ``` for code blocks
- Use > for blockquotes
- Use - or * for bullet lists on separate lines
- Use 1. 2. 3. for numbered lists
- Use # ## ### for headings

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
        max_iterations=10,
        handle_parsing_errors=True,
        return_intermediate_steps=False
    )
    
    return agent_executor
