from typing import Dict, Optional, List
import requests
from unstructured.partition.html import partition_html
from unstructured.chunking.title import chunk_by_title
from unstructured.chunking.basic import chunk_elements
import re
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
import os
from flashrank import Ranker, RerankRequest
from bs4 import BeautifulSoup
import json

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

        # Initialize FlashRank reranker
        self.ranker = Ranker(model_name="ms-marco-TinyBERT-L-2-v2", cache_dir=".cache")
    
    def scrape_website(self, url: str) -> Dict:
        """Scrape website content using Unstructured with improved chunking and reranking"""
        try:
            # Fetch the HTML content
            response = requests.get(url, headers=self.headers, timeout=15)
            response.raise_for_status()

            # Keep the full HTML content
            full_html = response.text

            # Use Unstructured to partition the HTML into document elements
            elements = partition_html(text=full_html, url=url, include_metadata=True)

            # Create chunks using basic chunking for better control
            chunks = chunk_elements(
                elements,
                max_characters=1500,  # Smaller chunks for better reranking
                overlap=200,  # Some overlap to maintain context
                new_after_n_chars=1400
            )

            # Convert chunks to text for processing
            chunk_texts = [str(chunk) for chunk in chunks]

            # Clean and filter chunks to remove code-heavy content
            cleaned_chunks = self._clean_chunks(chunk_texts)

            # Use FlashRank to rerank chunks by relevance to business analysis
            reranked_chunks = self._rerank_chunks(cleaned_chunks, url)

            # Extract all links from the page
            all_links = self._extract_all_links(full_html, url)
            
            # Extract structured data
            data = {
                'url': url,
                'title': self._extract_title(elements),
                'headings': self._extract_headings(elements),
                'main_content': self._extract_content(reranked_chunks),
                'footer_content': self._extract_footer_content(elements),
                'metadata': self._extract_metadata(elements),
                'contact_info': self._extract_contact_info(full_html, elements),
                'all_links': all_links,  # All extracted links with categories
                'full_html': full_html,  # Keep the complete HTML
                'structured_chunks': reranked_chunks[:15],  # Top 15 reranked chunks
                'total_chunks': len(reranked_chunks)
            }

            return data

        except Exception as e:
            raise Exception(f"Failed to scrape website: {str(e)}")

    def _rerank_chunks(self, chunks: List[str], url: str) -> List[str]:
        """Rerank chunks using FlashRank for better relevance to business analysis"""
        try:
            # Create query for business analysis relevance
            query = "business company information products services contact details industry analysis"

            # Prepare passages for reranking
            passages = []
            for i, chunk in enumerate(chunks):
                passages.append({
                    "id": str(i),
                    "text": chunk[:2000],  # Limit chunk size for reranking
                    "meta": {"url": url, "chunk_id": i}
                })

            # Create rerank request
            rerank_request = RerankRequest(
                query=query,
                passages=passages
            )

            # Perform reranking
            results = self.ranker.rerank(rerank_request)

            # Sort chunks by reranking score (highest first)
            sorted_chunks = []
            for result in results:
                chunk_index = int(result["id"])
                sorted_chunks.append(chunks[chunk_index])

            return sorted_chunks

        except Exception as e:
            print(f"Reranking failed, using original order: {str(e)}")
            return chunks
    
    def _clean_chunks(self, chunks: List[str]) -> List[str]:
        """Clean and filter chunks to remove code-heavy or irrelevant content"""
        cleaned_chunks = []
        
        for chunk in chunks:
            # Skip chunks that are too short
            if len(chunk.strip()) < 50:
                continue
            
            # Skip chunks that appear to be mostly code
            code_indicators = ['<script', '<style', 'function(', 'var ', 'const ', 'let ', 'import ', 'export ', 'class ', 'def ', 'if __name__']
            code_lines = 0
            total_lines = max(1, len(chunk.split('\n')))
            
            for line in chunk.split('\n'):
                line = line.strip()
                if any(indicator in line for indicator in code_indicators):
                    code_lines += 1
            
            # Skip if more than 30% of lines appear to be code
            if code_lines / total_lines > 0.3:
                continue
            
            # Skip chunks with excessive HTML tags
            html_tags = len(re.findall(r'<[^>]+>', chunk))
            if html_tags > len(chunk.split()) * 0.5:  # More tags than words
                continue
            
            # Clean up the chunk text
            # Remove excessive whitespace
            cleaned_chunk = re.sub(r'\s+', ' ', chunk.strip())
            
            # Remove HTML tags but keep content
            cleaned_chunk = re.sub(r'<[^>]+>', ' ', cleaned_chunk)
            
            # Clean up again
            cleaned_chunk = re.sub(r'\s+', ' ', cleaned_chunk).strip()
            
            if len(cleaned_chunk) >= 100:  # Keep chunks with substantial content
                cleaned_chunks.append(cleaned_chunk)
        
        return cleaned_chunks[:20]  # Limit to top 20 cleaned chunks
    
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
    
    def _extract_content(self, reranked_chunks: List[str]) -> str:
        """Extract main content from reranked chunks"""
        # Use top chunks for main content (reranked for relevance)
        content_parts = []
        for chunk in reranked_chunks[:12]:  # Top 12 reranked chunks
            content_parts.append(chunk)
        return "\n\n".join(content_parts)
    
    def _extract_footer_content(self, elements) -> str:
        """Extract footer content from document elements"""
        footer_parts = []
        for element in elements:
            # Check if element is in footer based on category or metadata
            if hasattr(element, 'category') and element.category in ['Footer', 'FooterText']:
                footer_parts.append(str(element))
            elif hasattr(element, 'metadata') and element.metadata:
                # Check metadata for footer indicators
                if hasattr(element.metadata, 'tag') and element.metadata.tag and 'footer' in element.metadata.tag.lower():
                    footer_parts.append(str(element))
                elif hasattr(element.metadata, 'element_id') and element.metadata.element_id and 'footer' in element.metadata.element_id.lower():
                    footer_parts.append(str(element))
                elif hasattr(element.metadata, 'class_name') and element.metadata.class_name and any('footer' in cls.lower() for cls in element.metadata.class_name):
                    footer_parts.append(str(element))

        return "\n".join(footer_parts) if footer_parts else ""
    
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
    
    def _extract_contact_info(self, html_text: str, elements) -> dict:
        """Extract contact information using regex, with LLM fallback that includes footer content"""
        # First try regex extraction
        contact_info = self._extract_contact_info_regex(html_text)
        
        # Validate phone numbers with LLM if we found any
        if contact_info.get('phones'):
            print(f"[API] Validating {len(contact_info['phones'])} phone numbers with LLM...")
            validated_phones = self._validate_phones_with_llm(
                contact_info['phones'], 
                html_text[:2000]  # Provide some context
            )
            contact_info['phones'] = validated_phones
        
        # Check if we found minimal information
        has_emails = len(contact_info.get('emails', [])) > 0
        has_phones = len(contact_info.get('phones', [])) > 0
        has_social = any(contact_info.get('social_media', {}).values())
        
        # If regex found good information, return it
        if has_emails or has_phones or has_social:
            return contact_info
        
        # Otherwise, try LLM extraction as fallback with footer content
        print("[API] Regex extraction found limited contact info, trying LLM fallback with footer content...")
        footer_content = self._extract_footer_content(elements)
        llm_contact_info = self._extract_contact_info_with_llm(html_text, footer_content)
        
        # Merge results, preferring regex results where available
        merged = {
            'emails': contact_info.get('emails', []) + llm_contact_info.get('emails', []),
            'phones': contact_info.get('phones', []) + llm_contact_info.get('phones', []),
            'social_media': {**contact_info.get('social_media', {}), **llm_contact_info.get('social_media', {})}
        }
        
        # Remove duplicates
        merged['emails'] = list(set(merged['emails']))[:3]
        
        # Validate merged phone numbers if any
        if merged.get('phones'):
            merged['phones'] = self._validate_phones_with_llm(
                list(set(merged['phones'])), 
                html_text[:2000]
            )
        else:
            merged['phones'] = []
        
        return merged
    
    def _extract_contact_info_regex(self, html_text: str) -> dict:
        """Extract contact information using regex patterns"""
        # Extract emails
        emails = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', html_text)
        
        # Extract phone numbers with improved patterns to avoid timestamps
        phone_patterns = [
            r'\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b',  # (123) 456-7890, 123-456-7890, 123.456.7890
            r'\b\+?\d{1,3}[-.\s]?\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b',  # +1 123 456 7890, +61 123 456 789
            r'\b\d{4}[-.\s]?\d{3}[-.\s]?\d{3}\b',  # Australian format: 1234 567 890
        ]
        
        phones = []
        for pattern in phone_patterns:
            matches = re.findall(pattern, html_text)
            phones.extend(matches)
        
        # Filter out obvious non-phone numbers (timestamps, IDs, etc.)
        filtered_phones = []
        for phone in phones:
            # Remove all non-digit characters for validation
            digits_only = re.sub(r'\D', '', phone)
            
            # Skip Unix timestamps (10-13 digits, common ranges for 2000s-2020s)
            if len(digits_only) >= 10 and len(digits_only) <= 13:
                # Check if it looks like a Unix timestamp (seconds since 1970)
                try:
                    timestamp = int(digits_only)
                    # Unix timestamps from 2000-2025 are roughly 946684800 to 1735689600
                    if 946684800 <= timestamp <= 1735689600:
                        continue
                except ValueError:
                    pass
            
            # Skip if it looks like an ID or timestamp (too many identical digits, sequential, etc.)
            if len(digits_only) >= 10:
                # Check for obvious patterns that aren't phone numbers
                if digits_only.isdigit():
                    # Skip sequential numbers (1234567890, 9876543210, etc.)
                    if digits_only in ['1234567890', '0987654321', '0123456789', '9876543210']:
                        continue
                    # Skip numbers with too many repeated digits
                    if any(digits_only.count(d) > 6 for d in '0123456789'):
                        continue
            
            filtered_phones.append(phone)
        
        phones = filtered_phones
        
        # Extract social media links - Enhanced with more platforms
        social_patterns = {
            'twitter': r'https?://(?:www\.)?(?:twitter|x)\.com/[\w]+',
            'linkedin': r'https?://(?:www\.)?linkedin\.com/(?:company|in)/[\w-]+',
            'facebook': r'https?://(?:www\.)?facebook\.com/[\w.]+',
            'instagram': r'https?://(?:www\.)?instagram\.com/[\w.]+',
            'youtube': r'https?://(?:www\.)?youtube\.com/(?:channel|c|user)/[\w-]+',
            'github': r'https?://(?:www\.)?github\.com/[\w-]+',
            'tiktok': r'https?://(?:www\.)?tiktok\.com/@[\w.]+',
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
    
    def _extract_contact_info_with_llm(self, html_text: str, footer_content: str = "") -> dict:
        """Extract contact information using LLM when regex fails, including footer content"""
        try:
            # Truncate HTML text to reasonable length for LLM
            truncated_text = html_text[:12000]  # Limit to 20000 characters
            
            # Prepare context with footer content prioritized
            context_parts = [truncated_text]
            if footer_content:
                context_parts.insert(0, f"FOOTER CONTENT (HIGH PRIORITY FOR CONTACT INFO):\n{footer_content[:4000]}")
                context_parts.insert(1, "\nMAIN CONTENT:")
            
            full_context = "\n\n".join(context_parts)
            
            prompt = ChatPromptTemplate.from_messages([
                ("system", """You are an expert at extracting contact information from website content. 
Extract emails, phone numbers, and social media links from the provided HTML content.
Pay special attention to footer content as it often contains contact information.

Return the information in a structured JSON format with these keys:
- emails: array of email addresses found
- phones: array of phone numbers found  
- social_media: object with keys like 'twitter', 'linkedin', 'facebook', 'instagram' containing arrays of URLs

Only extract information that appears to be legitimate contact information. Be precise and don't make assumptions.
Prioritize footer content over main content for contact information."""),
                ("human", f"Extract contact information from this website content:\n\n{full_context}")
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
    
    def _extract_all_links(self, html_text: str, base_url: str) -> Dict:
        """Extract all links from the page and categorize them"""
        try:
            soup = BeautifulSoup(html_text, 'html.parser')
            links = {
                'social_media': [],
                'contact_pages': [],
                'internal_pages': [],
                'external_links': [],
                'email_links': []
            }
            
            # Social media patterns
            social_domains = ['twitter.com', 'x.com', 'facebook.com', 'linkedin.com', 
                            'instagram.com', 'youtube.com', 'github.com', 'tiktok.com',
                            'pinterest.com', 'medium.com']
            
            # Contact page patterns
            contact_keywords = ['contact', 'about', 'team', 'support', 'help', 'reach-us']
            
            for link in soup.find_all('a', href=True):
                href = link.get('href', '').strip()
                text = link.get_text().strip()
                
                if not href:
                    continue
                
                # Handle mailto links
                if href.startswith('mailto:'):
                    email = href.replace('mailto:', '').split('?')[0]
                    if email:
                        links['email_links'].append({'email': email, 'text': text})
                    continue
                
                # Handle tel links
                if href.startswith('tel:'):
                    continue
                
                # Make relative URLs absolute
                if href.startswith('/'):
                    href = f"{base_url.rstrip('/')}{href}"
                elif not href.startswith('http'):
                    continue
                
                # Categorize the link
                is_social = any(domain in href.lower() for domain in social_domains)
                is_contact = any(keyword in href.lower() for keyword in contact_keywords)
                is_internal = base_url.split('/')[2] in href
                
                link_data = {'url': href, 'text': text}
                
                if is_social:
                    links['social_media'].append(link_data)
                elif is_contact:
                    links['contact_pages'].append(link_data)
                elif is_internal:
                    links['internal_pages'].append(link_data)
                else:
                    links['external_links'].append(link_data)
            
            # Remove duplicates and limit results
            for category in links:
                seen = set()
                unique_links = []
                for link in links[category]:
                    url_key = link.get('url') or link.get('email')
                    if url_key and url_key not in seen:
                        seen.add(url_key)
                        unique_links.append(link)
                links[category] = unique_links[:10]  # Limit to 10 per category
            
            return links
            
        except Exception as e:
            print(f"[API] Error extracting links: {str(e)}")
            return {
                'social_media': [],
                'contact_pages': [],
                'internal_pages': [],
                'external_links': [],
                'email_links': []
            }
    
    def _validate_phones_with_llm(self, phone_candidates: List[str], context: str = "") -> List[str]:
        """Use LLM to validate which phone numbers are actually valid contact numbers"""
        if not phone_candidates:
            return []
        
        try:
            prompt = ChatPromptTemplate.from_messages([
                ("system", """You are a phone number validator. Your job is to identify which numbers from a list are valid business contact phone numbers.

Invalid numbers include:
- Unix timestamps
- Random number sequences
- Order numbers or IDs
- Dates in numeric format
- Price numbers
- Product codes

Valid numbers typically:
- Have proper phone formatting (parentheses, dashes, spaces, + signs)
- Are 10-11 digits (with country code)
- Follow standard patterns for business phones

Return ONLY a JSON array of valid phone numbers from the input list."""),
                ("human", """Phone number candidates: {phones}

Context (if available): {context}

Return valid phone numbers as a JSON array. Example: ["123-456-7890", "+1-555-123-4567"]""")
            ])
            
            chain = prompt | self.llm
            response = chain.invoke({
                "phones": ", ".join(phone_candidates[:10]),  # Limit to first 10
                "context": context[:500]  # Brief context
            })
            
            # Parse the response
            content = response.content.strip()
            
            # Try to extract JSON from the response
            json_match = re.search(r'\[.*\]', content, re.DOTALL)
            if json_match:
                validated = json.loads(json_match.group())
                return validated[:3]  # Return top 3
            
            return phone_candidates[:3]  # Fallback to original
            
        except Exception as e:
            print(f"[API] Phone validation with LLM failed: {str(e)}")
            return phone_candidates[:3]  # Fallback to original
