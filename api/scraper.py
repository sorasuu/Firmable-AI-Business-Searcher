from typing import Dict, Optional
import requests
from unstructured.partition.html import partition_html
from unstructured.chunking.title import chunk_by_title
import re
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
import os

class WebsiteScraper:
    def __init__(self, llm=None):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        self.llm = llm or ChatOpenAI(
            model="openai/gpt-oss-20b",
            temperature=0.1,
            api_key=os.environ.get("GROQ_API_KEY", ""),
            base_url="https://api.groq.com/openai/v1"
        )
    
    def scrape_website(self, url: str) -> Dict:
        """Scrape website content using Unstructured for better parsing"""
        try:
            # Fetch the HTML content
            response = requests.get(url, headers=self.headers, timeout=15)
            response.raise_for_status()
            
            # Use Unstructured to partition the HTML
            elements = partition_html(text=response.text, url=url)
            
            # Chunk the content by title for better organization
            chunks = chunk_by_title(elements, max_characters=2000)
            
            # Extract structured data
            data = {
                'url': url,
                'title': self._extract_title(elements),
                'headings': self._extract_headings(elements),
                'main_content': self._extract_content(chunks),
                'metadata': self._extract_metadata(elements),
                'contact_info': self._extract_contact_info(response.text),
                'structured_chunks': [str(chunk) for chunk in chunks[:10]]  # First 10 chunks
            }
            
            return data
            
        except Exception as e:
            raise Exception(f"Failed to scrape website: {str(e)}")
    
    def _extract_title(self, elements) -> str:
        """Extract title from elements"""
        for element in elements:
            if hasattr(element, 'category') and element.category == 'Title':
                return str(element)
        return ""
    
    def _extract_headings(self, elements) -> list:
        """Extract all headings"""
        headings = []
        for element in elements:
            if hasattr(element, 'category') and element.category in ['Title', 'Header']:
                headings.append({
                    'type': element.category,
                    'text': str(element)
                })
        return headings[:15]
    
    def _extract_content(self, chunks) -> str:
        """Extract main content from chunks"""
        content_parts = []
        for chunk in chunks[:8]:  # First 8 chunks
            content_parts.append(str(chunk))
        return "\n\n".join(content_parts)
    
    def _extract_metadata(self, elements) -> dict:
        """Extract metadata from elements"""
        metadata = {}
        for element in elements:
            if hasattr(element, 'metadata') and element.metadata:
                if hasattr(element.metadata, 'page_name'):
                    metadata['page_name'] = element.metadata.page_name
                if hasattr(element.metadata, 'languages'):
                    metadata['languages'] = element.metadata.languages
                break
        return metadata
    
    def _extract_contact_info(self, html_text: str) -> dict:
        """Extract contact information using regex, with LLM fallback"""
        # First try regex extraction
        contact_info = self._extract_contact_info_regex(html_text)
        
        # Check if we found minimal information
        has_emails = len(contact_info.get('emails', [])) > 0
        has_phones = len(contact_info.get('phones', [])) > 0
        has_social = any(contact_info.get('social_media', {}).values())
        
        # If regex found good information, return it
        if has_emails or has_phones or has_social:
            return contact_info
        
        # Otherwise, try LLM extraction as fallback
        print("[API] Regex extraction found limited contact info, trying LLM fallback...")
        llm_contact_info = self._extract_contact_info_with_llm(html_text)
        
        # Merge results, preferring regex results where available
        merged = {
            'emails': contact_info.get('emails', []) + llm_contact_info.get('emails', []),
            'phones': contact_info.get('phones', []) + llm_contact_info.get('phones', []),
            'social_media': {**contact_info.get('social_media', {}), **llm_contact_info.get('social_media', {})}
        }
        
        # Remove duplicates
        merged['emails'] = list(set(merged['emails']))[:3]
        merged['phones'] = list(set(merged['phones']))[:3]
        
        return merged
    
    def _extract_contact_info_regex(self, html_text: str) -> dict:
        """Extract contact information using regex patterns"""
        # Extract emails
        emails = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', html_text)
        
        # Extract phone numbers
        phones = re.findall(r'\b(?:\+?1[-.]?)?\d{3}[-.]?\d{3}[-.]?\d{4}\b', html_text)
        
        # Extract social media links
        social_patterns = {
            'twitter': r'https?://(?:www\.)?(?:twitter|x)\.com/[\w]+',
            'linkedin': r'https?://(?:www\.)?linkedin\.com/(?:company|in)/[\w-]+',
            'facebook': r'https?://(?:www\.)?facebook\.com/[\w.]+',
            'instagram': r'https?://(?:www\.)?instagram\.com/[\w.]+',
        }
        
        social_media = {}
        for platform, pattern in social_patterns.items():
            matches = re.findall(pattern, html_text)
            if matches:
                social_media[platform] = list(set(matches))[:2]
        
        return {
            'emails': list(set(emails))[:3],
            'phones': list(set(phones))[:3],
            'social_media': social_media
        }
    
    def _extract_contact_info_with_llm(self, html_text: str) -> dict:
        """Extract contact information using LLM when regex fails"""
        try:
            # Truncate HTML text to reasonable length for LLM
            truncated_text = html_text[:8000]  # Limit to 8000 characters
            
            prompt = ChatPromptTemplate.from_messages([
                ("system", """You are an expert at extracting contact information from website content. 
Extract emails, phone numbers, and social media links from the provided HTML content.
Return the information in a structured JSON format with these keys:
- emails: array of email addresses found
- phones: array of phone numbers found  
- social_media: object with keys like 'twitter', 'linkedin', 'facebook', 'instagram' containing arrays of URLs

Only extract information that appears to be legitimate contact information. Be precise and don't make assumptions."""),
                ("human", f"Extract contact information from this website content:\n\n{truncated_text}")
            ])
            
            chain = prompt | self.llm
            
            response = chain.invoke({})
            content = response.content.strip()
            
            # Try to parse JSON response
            try:
                import json
                parsed = json.loads(content)
                return {
                    'emails': parsed.get('emails', [])[:3],
                    'phones': parsed.get('phones', [])[:3],
                    'social_media': parsed.get('social_media', {})
                }
            except json.JSONDecodeError:
                # If JSON parsing fails, try to extract manually from text
                return self._parse_llm_response_text(content)
                
        except Exception as e:
            print(f"[API] LLM contact extraction failed: {str(e)}")
            return {'emails': [], 'phones': [], 'social_media': {}}
    
    def _parse_llm_response_text(self, response_text: str) -> dict:
        """Parse LLM response when JSON parsing fails"""
        emails = []
        phones = []
        social_media = {}
        
        # Simple text parsing as fallback
        lines = response_text.lower().split('\n')
        for line in lines:
            line = line.strip()
            if '@' in line and '.' in line:
                # Look for email patterns
                email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', line)
                if email_match and email_match.group() not in emails:
                    emails.append(email_match.group())
            
            # Look for phone patterns
            phone_match = re.search(r'\b(?:\+?1[-.]?)?\d{3}[-.]?\d{3}[-.]?\d{4}\b', line)
            if phone_match and phone_match.group() not in phones:
                phones.append(phone_match.group())
            
            # Look for social media
            if 'twitter' in line or 'x.com' in line:
                url_match = re.search(r'https?://(?:www\.)?(?:twitter|x)\.com/[\w]+', line)
                if url_match:
                    social_media['twitter'] = social_media.get('twitter', []) + [url_match.group()]
            
            if 'linkedin' in line:
                url_match = re.search(r'https?://(?:www\.)?linkedin\.com/(?:company|in)/[\w-]+', line)
                if url_match:
                    social_media['linkedin'] = social_media.get('linkedin', []) + [url_match.group()]
            
            if 'facebook' in line:
                url_match = re.search(r'https?://(?:www\.)?facebook\.com/[\w.]+', line)
                if url_match:
                    social_media['facebook'] = social_media.get('facebook', []) + [url_match.group()]
            
            if 'instagram' in line:
                url_match = re.search(r'https?://(?:www\.)?instagram\.com/[\w.]+', line)
                if url_match:
                    social_media['instagram'] = social_media.get('instagram', []) + [url_match.group()]
        
        # Remove duplicates
        for platform in social_media:
            social_media[platform] = list(set(social_media[platform]))[:2]
        
        return {
            'emails': emails[:3],
            'phones': phones[:3],
            'social_media': social_media
        }
