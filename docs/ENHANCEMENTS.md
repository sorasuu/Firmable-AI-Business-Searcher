# Recent Enhancements

## Overview
This document describes the latest enhancements made to the Firmable AI Searcher Proto application.

## 1. Enhanced Link Extraction (Scraping Phase)

### What Changed
- Added comprehensive href extraction during the scraping phase
- All links are now categorized for better analysis and retrieval

### Categories
- **Social Media Links**: Twitter, LinkedIn, Facebook, Instagram, YouTube, GitHub, TikTok, Pinterest, Medium
- **Contact Pages**: About, Contact, Team, Support pages
- **Internal Pages**: All internal website pages
- **External Links**: Links to external websites
- **Email Links**: mailto: links extracted separately

### Benefits
- Better social contact detection
- More comprehensive social media profile discovery
- Easier navigation to important pages (contact, about, team)
- Enhanced context for the chat agent

### Usage
```python
scraped_data = scraper.scrape_website(url)
all_links = scraped_data['all_links']

# Access categorized links
social_links = all_links['social_media']
contact_pages = all_links['contact_pages']
email_links = all_links['email_links']
```

## 2. LLM-Powered Phone Number Validation

### What Changed
- Phone numbers are now validated using an LLM before being returned
- Filters out false positives like Unix timestamps, order IDs, and random numbers

### How It Works
1. Regex extracts potential phone numbers
2. Numbers are sent to the LLM with context
3. LLM validates which numbers are actual contact numbers
4. Only validated numbers are returned

### Benefits
- More accurate phone number extraction
- Eliminates timestamps and IDs that look like phone numbers
- Better quality contact information

### Example
```python
# Before: ['1417607487', '1633561860866', '+1-555-123-4567']
# After: ['+1-555-123-4567']
```

## 3. Smart Chat with Dynamic Page Scraping

### What Changed
- Chat interface now intelligently detects when users ask about pages not yet scraped
- Automatically scrapes additional pages (like pricing, careers, about) on demand
- Falls back gracefully without complex ReAct agent overhead

### How It Works

**Automatic Page Detection**
```
User: "Is there any pricing?"
System: *Detects 'pricing' keyword*
System: *Searches internal links for pricing page*
System: *Scrapes https://example.com/pricing*
System: *Responds with pricing information*
```

**Supported Keywords**
- `pricing`, `price`, `pricing page` → Scrapes pricing page
- More keywords can be added easily

### Benefits
- Users can ask about any page on the website
- No need to pre-scrape entire website
- Saves time and resources
- More natural conversation flow
- Context-aware responses

### Example Conversation
```
User: "What do they do with CRM?"
Assistant: "Firmable works directly with your CRM to super‑charge..."

User: "Is there any pricing?"
Assistant: *scrapes pricing page*
           "Yes! Here are their pricing plans:
           - Starter: $X/month
           - Professional: $Y/month  
           - Enterprise: Custom"

User: "What's included in Professional?"
Assistant: *uses cached pricing data*
           "The Professional plan includes..."
```

### Advantages Over ReAct Agent
- **Simpler**: No complex agent reasoning chains
- **Faster**: Direct tool calling, no multiple LLM calls
- **More Reliable**: Fewer points of failure
- **Cost Effective**: Fewer tokens used
- **Easier to Debug**: Clear execution path

## 4. Updated Dependencies

### New Dependencies
- `beautifulsoup4>=4.12.0` - For HTML parsing and link extraction
- `lxml>=4.9.0` - Fast XML/HTML processor

### Updated in
- `requirements.txt`
- `pyproject.toml`

## Migration Guide

### For Existing Deployments

1. **Update Dependencies**
   ```bash
   cd api
   uv sync
   ```

2. **No Database Changes Required**
   - All changes are in-memory processing
   - No schema migrations needed

3. **Backward Compatible**
   - All existing API endpoints work the same
   - New features are additive
   - Can disable ReAct agent if needed

4. **Test the Changes**
   ```bash
   # Test phone validation
   python -c "from scraper import WebsiteScraper; s = WebsiteScraper(); print('OK')"
   
   # Test agent tools
   python -c "from agent_tools import AgentTools; print('OK')"
   ```

## Configuration Options

### Enable/Disable ReAct Agent
The ReAct agent is currently disabled by default due to tool calling compatibility issues. The system uses a simpler, more reliable direct tool approach.

```python
# In chat.py
agent = ConversationalAgent()
agent.use_react_agent = False  # Recommended: False (default)
```

### Add More Keyword Detection
To detect more page types, edit `_standard_chat()` in `chat.py`:

```python
# Add more keywords
if any(keyword in query_lower for keyword in ['pricing', 'careers', 'jobs', 'team']):
    # Scraping logic
```

## Performance Considerations

### Phone Validation
- Adds ~1-2 seconds to scraping time
- Only runs when phone numbers are found
- Can be disabled by modifying `_extract_contact_info()` method

### Link Extraction
- Minimal performance impact (<0.5s)
- Processes HTML once during scraping
- Results cached with scraped data

### Dynamic Page Scraping
- Only scrapes when user asks about a specific page
- ~2-4 seconds per additional page
- Results can be cached for the session
- Much faster than pre-scraping entire site

## Troubleshooting

### "Import bs4 could not be resolved"
```bash
cd api
uv sync
# or
pip install beautifulsoup4 lxml
```

### "Phone validation taking too long"
Disable LLM validation in `scraper.py`:
```python
# Comment out these lines in _extract_contact_info():
# validated_phones = self._validate_phones_with_llm(...)
# contact_info['phones'] = validated_phones
```

### "Chat not finding pricing information"
1. Check if pricing page exists in internal links:
   ```python
   # In scraped_data
   all_links['internal_pages']  # Look for pricing URL
   ```

2. Verify keyword detection is working:
   ```python
   # The system looks for: 'pricing', '/pricing', 'price page', 'pricing page'
   ```

3. Add more keywords in `chat.py` if needed

### "Additional page scraping failing"
- Check URL format (should be absolute or start with /)
- Verify the page exists and is accessible
- Check scraper logs for specific errors

## Future Enhancements

Potential future improvements:
- [ ] Multi-page scraping tool for the agent
- [ ] Web search capability
- [ ] Document download and analysis
- [ ] Screenshot capture and vision analysis
- [ ] Competitive analysis tools
- [ ] Historical data tracking

## Testing

Run the test suite to verify all changes:
```bash
pytest api/test_api.py -v
```

Test specific features:
```bash
# Test scraping with link extraction
curl -X POST http://localhost:8000/api/analyze \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-secret-key" \
  -d '{"url": "https://example.com"}'

# Test chat with ReAct agent
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-secret-key" \
  -d '{"url": "https://example.com", "query": "What are their social media links?"}'
```

## Questions?

For issues or questions about these enhancements:
1. Check the logs for detailed error messages
2. Review the code comments in `scraper.py`, `agent_tools.py`, and `chat.py`
3. Test with `verbose=True` in the agent executor to see reasoning steps
