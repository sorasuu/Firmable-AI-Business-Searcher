# Quick Guide: Adding New Keyword Detection

## Overview
The chat system can automatically scrape additional pages when users ask about them. This guide shows how to add detection for new page types.

## Step-by-Step Instructions

### 1. Identify the Page Type
Decide what page you want to detect (e.g., careers, team, about, blog, etc.)

### 2. Choose Keywords
List the words/phrases users might use:
- **Careers**: "careers", "jobs", "job openings", "work with us", "join our team"
- **About**: "about", "about us", "who are you", "team", "company info"
- **Blog**: "blog", "articles", "news", "latest posts"

### 3. Add Detection Logic

Open `api/chat.py` and find the `_standard_chat()` method. Add your detection block:

```python
def _standard_chat(self, cached: Dict, query: str, conversation_history: Optional[List[Dict]] = None) -> str:
    """Standard chat approach with smart tool detection"""
    query_lower = query.lower()
    
    # EXISTING: Pricing page detection
    if any(keyword in query_lower for keyword in ['pricing', '/pricing', 'price page', 'pricing page']):
        # ... existing pricing logic
    
    # NEW: Add your detection here
    # Example: Careers page
    if any(keyword in query_lower for keyword in ['careers', 'jobs', '/careers', 'job openings', 'hiring']):
        scraped = cached.get('scraped_data', {})
        all_links = scraped.get('all_links', {})
        internal_pages = all_links.get('internal_pages', [])
        contact_pages = all_links.get('contact_pages', [])
        
        # Look for careers page
        careers_url = None
        for page in internal_pages + contact_pages:
            page_url = page.get('url', '')
            if 'career' in page_url.lower() or 'job' in page_url.lower():
                careers_url = page_url
                break
        
        if careers_url:
            try:
                from api.scraper import WebsiteScraper
                scraper = WebsiteScraper()
                print(f"[API] Detected careers page request, scraping: {careers_url}")
                careers_data = scraper.scrape_website(careers_url)
                
                # Add careers info to context
                careers_content = careers_data.get('main_content', '')
                if careers_content:
                    context = self._prepare_conversation_context(cached)
                    context += f"\\n\\nCareers Page Information:\\n{careers_content[:2000]}"
                    
                    # Build messages with careers context
                    messages = [
                        SystemMessage(content=f"""You are an AI assistant that helps users understand websites and businesses. 
You have analyzed a website and just scraped additional information about their careers/jobs.

{context}

Answer user questions based on this information. Be conversational, helpful, and concise.""")
                    ]
                    
                    # Add conversation history
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
                    except Exception as e:
                        return f"I encountered an error: {str(e)}"
            except Exception as e:
                print(f"[API] Error scraping careers page: {str(e)}")
    
    # Continue with standard context...
```

## Template for Copy-Paste

Replace `PAGE_TYPE`, `KEYWORDS`, and `URL_PATTERNS` with your values:

```python
# Detect PAGE_TYPE page
if any(keyword in query_lower for keyword in KEYWORDS):
    scraped = cached.get('scraped_data', {})
    all_links = scraped.get('all_links', {})
    internal_pages = all_links.get('internal_pages', [])
    contact_pages = all_links.get('contact_pages', [])
    
    # Look for PAGE_TYPE page
    target_url = None
    for page in internal_pages + contact_pages:
        page_url = page.get('url', '')
        if any(pattern in page_url.lower() for pattern in URL_PATTERNS):
            target_url = page_url
            break
    
    if target_url:
        try:
            from api.scraper import WebsiteScraper
            scraper = WebsiteScraper()
            print(f"[API] Detected PAGE_TYPE page request, scraping: {target_url}")
            page_data = scraper.scrape_website(target_url)
            
            # Add info to context
            page_content = page_data.get('main_content', '')
            if page_content:
                context = self._prepare_conversation_context(cached)
                context += f"\\n\\nPAGE_TYPE Page Information:\\n{page_content[:2000]}"
                
                # Build messages
                messages = [
                    SystemMessage(content=f"""You are an AI assistant. 
You just scraped PAGE_TYPE information.

{context}

Answer based on this information.""")
                ]
                
                # Add history
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
                except Exception as e:
                    return f"Error: {str(e)}"
        except Exception as e:
            print(f"[API] Error scraping PAGE_TYPE page: {str(e)}")
```

## Examples

### Example 1: Careers Page
```python
# Keywords to detect
KEYWORDS = ['careers', 'jobs', '/careers', 'job openings', 'hiring', 'work with us']

# URL patterns to match
URL_PATTERNS = ['career', 'job', 'hiring']

# Page type for messages
PAGE_TYPE = "careers"
```

### Example 2: About Page
```python
KEYWORDS = ['about', 'about us', '/about', 'who are you', 'team', 'company info']
URL_PATTERNS = ['about', 'team', 'company']
PAGE_TYPE = "about"
```

### Example 3: Blog
```python
KEYWORDS = ['blog', 'articles', 'news', '/blog', 'latest posts', 'insights']
URL_PATTERNS = ['blog', 'article', 'news', 'post']
PAGE_TYPE = "blog"
```

## Testing Your Addition

1. Start the backend:
```bash
cd api
uvicorn index:app --reload --port 8000
```

2. Test with curl:
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-secret-key" \
  -d '{
    "url": "https://example.com",
    "query": "Are they hiring?"  # Use your keyword here
  }'
```

3. Check logs:
```
[API] Detected careers page request, scraping: https://example.com/careers
```

## Tips

1. **Order Matters**: Place more specific detections before general ones
2. **Test Keywords**: Try different phrasings users might use
3. **URL Patterns**: Make patterns specific enough to avoid false matches
4. **Content Limit**: Keep `[:2000]` to avoid token limits
5. **Error Handling**: Always wrap in try-except for reliability

## Common Pitfalls

❌ **Too Generic Keywords**
```python
# Bad: Will trigger on many queries
if 'page' in query_lower:
```

✅ **Specific Keywords**
```python
# Good: Clear intent
if any(keyword in query_lower for keyword in ['pricing page', 'price page']):
```

❌ **Too Broad URL Patterns**
```python
# Bad: Matches too much
if 'page' in page_url.lower():
```

✅ **Specific URL Patterns**
```python
# Good: Clear matching
if 'pricing' in page_url.lower() or 'price' in page_url.lower():
```

## Performance Optimization

If you're adding many detections, consider:

1. **Early Returns**: Check most common queries first
2. **Caching**: Store scraped pages in session
3. **Lazy Loading**: Only scrape if not already cached

```python
# Example with caching
if not hasattr(self, '_page_cache'):
    self._page_cache = {}

if careers_url in self._page_cache:
    careers_content = self._page_cache[careers_url]
else:
    careers_data = scraper.scrape_website(careers_url)
    careers_content = careers_data.get('main_content', '')
    self._page_cache[careers_url] = careers_content
```

## Need Help?

- Check `docs/CHAT_FIX.md` for the overall approach
- Review `docs/ENHANCEMENTS.md` for full feature documentation
- Look at existing pricing detection as a reference
- Test thoroughly with different phrasings

Happy coding! 🚀
