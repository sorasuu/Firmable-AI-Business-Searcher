from typing import Dict, Optional, List, Tuple, Any
import os
import re
import json
from collections import OrderedDict
import requests
from bs4 import BeautifulSoup
import html2text
try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env.local"))
except ImportError:
    pass
try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env.local"))
except ImportError:
    pass
try:
    from firecrawl.firecrawl import FirecrawlApp
    FIRECRAWL_AVAILABLE = True
except ImportError:
    try:
        from firecrawl import FirecrawlApp
        FIRECRAWL_AVAILABLE = True
    except ImportError:
        FIRECRAWL_AVAILABLE = False
        FirecrawlApp = None
from langchain_groq import ChatGroq
from langchain.prompts import ChatPromptTemplate
from urllib.parse import urlparse, urljoin


class WebsiteScraper:
    """Web scraper using Firecrawl API with BeautifulSoup fallback"""
    
    def __init__(self, llm=None):
        # Initialize Firecrawl if available
        self.use_firecrawl = False
        self.app = None
        
        if FIRECRAWL_AVAILABLE:
            firecrawl_api_key = os.environ.get("FIRECRAWL_API_KEY", "")
            if firecrawl_api_key:
                try:
                    self.app = FirecrawlApp(api_key=firecrawl_api_key)
                    self.use_firecrawl = True
                    print("[SCRAPER] Firecrawl initialized successfully")
                except Exception as e:
                    print(f"[SCRAPER] Firecrawl initialization failed: {e}. Will use fallback scraper.")
            else:
                print("[SCRAPER] No FIRECRAWL_API_KEY found. Using fallback scraper.")
        else:
            print("[SCRAPER] Firecrawl not available. Using fallback scraper.")
        
        # Initialize BeautifulSoup fallback tools
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        self.html_converter = html2text.HTML2Text()
        self.html_converter.ignore_links = False
        
        # Initialize cache
        self.cache_file = os.path.join(os.path.dirname(__file__), "scraper_cache.jsonl")
        self.cache = self._load_cache()
        self.html_converter.ignore_images = True
        self.html_converter.ignore_emphasis = False
        
        # Initialize LLM for additional processing
        self.llm = llm or ChatGroq(
            model=os.environ.get("GROQ_MODEL", "openai/gpt-oss-20b"),
            temperature=0.1,
            groq_api_key=os.environ.get("GROQ_API_KEY", "")
        )
    
    def _load_cache(self) -> Dict:
        """Load cache from JSONL file with recovery for malformed lines"""
        cache: Dict[str, Dict] = {}
        if not os.path.exists(self.cache_file):
            return cache

        sanitized_entries: "OrderedDict[str, Dict[str, Any]]" = OrderedDict()
        needs_rewrite = False

        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                for line_number, raw_line in enumerate(f, start=1):
                    stripped = raw_line.strip()
                    if not stripped:
                        continue

                    entries, complete = self._parse_cache_line(stripped)
                    if len(entries) != 1 or not complete:
                        needs_rewrite = True

                    if not entries:
                        needs_rewrite = True
                        print(f"[CACHE] Skipping unreadable line {line_number}: {stripped[:80]}...")
                        continue

                    for entry in entries:
                        if not isinstance(entry, dict):
                            needs_rewrite = True
                            print(f"[CACHE] Invalid cache entry on line {line_number}; expected object, got {type(entry)}")
                            continue

                        url_value = entry.get('url')
                        data_value = entry.get('data')

                        if not url_value or data_value is None:
                            needs_rewrite = True
                            print(f"[CACHE] Missing url or data in cache entry on line {line_number}")
                            continue

                        cache[url_value] = data_value

                        sanitized_entry = {'url': url_value, 'data': data_value}
                        if 'timestamp' in entry:
                            sanitized_entry['timestamp'] = entry['timestamp']
                        sanitized_entries[url_value] = sanitized_entry
                        sanitized_entries.move_to_end(url_value)

            if needs_rewrite:
                self._rewrite_cache_file(list(sanitized_entries.values()))

            print(f"[CACHE] Loaded {len(cache)} cached entries")
        except Exception as e:
            print(f"[CACHE] Error loading cache: {e}")

        return cache
    
    def _save_to_cache(self, url: str, data: Dict):
        """Save scraped data to cache"""
        try:
            entry = {
                'url': url,
                'data': data,
                'timestamp': json.dumps({'timestamp': None})  # Could add actual timestamp
            }
            with open(self.cache_file, 'a', encoding='utf-8') as f:
                json.dump(entry, f, ensure_ascii=False)
                f.write('\n')
            self.cache[url] = data
            print(f"[CACHE] Saved {url} to cache")
        except Exception as e:
            print(f"[CACHE] Error saving to cache: {e}")

    def _parse_cache_line(self, line: str) -> Tuple[List[Dict[str, Any]], bool]:
        """Parse one or more JSON objects from a cache line."""
        stripped = line.strip()
        if not stripped:
            return [], True

        decoder = json.JSONDecoder()
        entries: List[Dict[str, Any]] = []
        idx = 0
        length = len(stripped)

        while idx < length:
            try:
                obj, next_idx = decoder.raw_decode(stripped, idx)
            except json.JSONDecodeError:
                # Return whatever we managed to parse; caller decides on rewrite
                return entries, False

            entries.append(obj)
            idx = next_idx
            while idx < length and stripped[idx] in (' ', '\t'):
                idx += 1

        return entries, True

    def _rewrite_cache_file(self, entries: List[Dict[str, Any]]):
        """Rewrite cache file with sanitized entries to prevent future parse errors."""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                for entry in entries:
                    json.dump(entry, f, ensure_ascii=False)
                    f.write('\n')
            print(f"[CACHE] Rewrote cache with {len(entries)} entries")
        except Exception as e:
            print(f"[CACHE] Failed to rewrite cache: {e}")
    
    def _get_from_cache(self, url: str) -> Optional[Dict]:
        """Get data from cache if available"""
        return self.cache.get(url)
    
    def scrape_website(self, url: str) -> Dict:
        """
        Scrape website using Firecrawl's intelligent extraction.
        Firecrawl handles JavaScript rendering, anti-bot detection, and smart content extraction.
        """
        # Check cache first
        cached_data = self._get_from_cache(url)
        if cached_data:
            print(f"[CACHE] Using cached data for {url}")
            return cached_data
        
        try:
            print(f"[SCRAPER] Starting Firecrawl scrape for: {url}")
            
            # Use Firecrawl's scrape endpoint with all features enabled
            scrape_result = self.app.scrape(
                url,
                formats=["markdown", "html", "links"],
                only_main_content=False,
                wait_for=2000,
            )
            
            print(f"[SCRAPER] Firecrawl scrape completed successfully")
            
            # Firecrawl returns a Document object with attributes
            # Access the attributes directly
            markdown_content = getattr(scrape_result, "markdown", "")
            html_content = getattr(scrape_result, "html", "")
            metadata_obj = getattr(scrape_result, "metadata", None)
            links = getattr(scrape_result, "links", [])
            
            # Convert metadata object to dictionary
            metadata = {}
            if metadata_obj:
                # DocumentMetadata object has attributes like title, description, etc.
                metadata = {
                    "title": getattr(metadata_obj, "title", ""),
                    "description": getattr(metadata_obj, "description", ""),
                    "url": getattr(metadata_obj, "url", ""),
                    "language": getattr(metadata_obj, "language", ""),
                    "keywords": getattr(metadata_obj, "keywords", ""),
                    "og_title": getattr(metadata_obj, "og_title", ""),
                    "og_description": getattr(metadata_obj, "og_description", ""),
                    "og_url": getattr(metadata_obj, "og_url", ""),
                    "og_image": getattr(metadata_obj, "og_image", ""),
                    "status_code": getattr(metadata_obj, "status_code", ""),
                    "content_type": getattr(metadata_obj, "content_type", ""),
                }
            
            # Process and structure the data
            headings = self._extract_headings_from_markdown(markdown_content)
            chunks = self._create_smart_chunks(markdown_content)
            all_links = self._categorize_links(links, url)
            
            structured_data = {
                "url": url,
                "title": metadata.get("title", ""),
                "description": metadata.get("description", ""),
                "keywords": metadata.get("keywords", ""),
                "og_title": metadata.get("og_title", ""),
                "og_description": metadata.get("og_description", ""),
                "markdown_content": markdown_content,
                "html_content": html_content,
                "main_content": self._extract_main_content(markdown_content),
                "headings": headings,
                "structured_chunks": chunks,
                "chunks": chunks,
                "total_chunks": len(chunks),
                "all_links": all_links,
                "internal_pages": all_links.get("internal", []),
                "external_links": all_links.get("external", []),
                "contact_info": self._extract_contact_info(markdown_content, html_content, links, chunks),
                "metadata": metadata,
                "language": metadata.get("language", "en"),
                "scraper_used": "firecrawl"
            }
            
            print(f"[SCRAPER] Processed {len(structured_data['chunks'])} content chunks")
            
            # Save to cache
            self._save_to_cache(url, structured_data)
            
            return structured_data
            
        except Exception as e:
            print(f"[SCRAPER] Error during Firecrawl scrape: {str(e)}")
            # Try fallback scraper
            return self._scrape_with_beautifulsoup(url)
    
    def _scrape_with_beautifulsoup(self, url: str) -> Dict:
        """Fallback scraper using BeautifulSoup"""
        try:
            print(f"[SCRAPER] Using BeautifulSoup fallback for: {url}")
            
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'lxml')
            
            # Extract title
            title = soup.title.string if soup.title else ""
            
            # Convert HTML to markdown
            markdown_content = self.html_converter.handle(str(soup))
            
            # Extract metadata
            metadata = {
                "title": title,
                "description": soup.find('meta', attrs={'name': 'description'}) or soup.find('meta', attrs={'property': 'og:description'}),
                "keywords": soup.find('meta', attrs={'name': 'keywords'}),
                "og_title": soup.find('meta', attrs={'property': 'og:title'}),
                "og_description": soup.find('meta', attrs={'property': 'og:description'}),
                "status_code": response.status_code,
                "content_type": response.headers.get('content-type', ''),
            }
            
            # Clean metadata
            for key, value in metadata.items():
                if hasattr(value, 'get'):
                    metadata[key] = value.get('content', '') if value else ''
                elif hasattr(value, 'string'):
                    metadata[key] = value.string or ''
                else:
                    metadata[key] = str(value) if value else ''
            
            # Extract links
            links = []
            for a_tag in soup.find_all('a', href=True):
                links.append(a_tag['href'])
            
            # Process and structure the data
            headings = self._extract_headings_from_markdown(markdown_content)
            chunks = self._create_smart_chunks(markdown_content)
            all_links = self._categorize_links(links, url)
            
            structured_data = {
                "url": url,
                "title": metadata.get("title", ""),
                "description": metadata.get("description", ""),
                "keywords": metadata.get("keywords", ""),
                "og_title": metadata.get("og_title", ""),
                "og_description": metadata.get("og_description", ""),
                "markdown_content": markdown_content,
                "html_content": str(soup),
                "main_content": self._extract_main_content(markdown_content),
                "headings": headings,
                "structured_chunks": chunks,
                "chunks": chunks,
                "total_chunks": len(chunks),
                "all_links": all_links,
                "internal_pages": all_links.get("internal", []),
                "external_links": all_links.get("external", []),
                "contact_info": self._extract_contact_info(markdown_content, str(soup), links, chunks),
                "metadata": metadata,
                "language": metadata.get("language", "en"),
                "scraper_used": "beautifulsoup"
            }
            
            print(f"[SCRAPER] BeautifulSoup fallback processed {len(structured_data['chunks'])} content chunks")
            
            # Save to cache
            self._save_to_cache(url, structured_data)
            
            return structured_data
            
        except Exception as e:
            print(f"[SCRAPER] BeautifulSoup fallback also failed: {str(e)}")
            raise
            
        except Exception as e:
            print(f"[SCRAPER] Error during Firecrawl scrape: {str(e)}")
            raise Exception(f"Failed to scrape website with Firecrawl: {str(e)}")
    
    def _extract_headings_from_markdown(self, markdown: str) -> List[Dict]:
        """Extract headings from markdown content"""
        headings = []
        lines = markdown.split("\n")
        
        for line in lines:
            line = line.strip()
            if line.startswith("#"):
                level = 0
                for char in line:



                    if char == "#":
                        level += 1
                    else:
                        break
                
                text = line.lstrip("#").strip()
                if text:
                    headings.append({"level": level, "text": text, "type": f"h{level}"})
        
        return headings
    
    def _extract_headings_from_soup(self, soup) -> List[Dict]:
        """Extract headings from BeautifulSoup object"""
        headings = []
        for i in range(1, 7):  # h1 to h6
            for heading in soup.find_all(f'h{i}'):
                text = heading.get_text().strip()
                if text:
                    headings.append({
                        'level': i,
                        'text': text,
                        'type': f'h{i}'
                    })
        return headings
    
    def _extract_main_content(self, markdown: str) -> str:
        """Extract and clean main content from markdown"""
        content = re.sub(r"\n{3,}", "\n\n", markdown)
        content = re.sub(r"(?i)^#+\s*(navigation|menu|footer|copyright).*$", "", content, flags=re.MULTILINE)
        return content.strip()
    
    def _create_smart_chunks(self, markdown: str) -> List[str]:
        """Create intelligent chunks from markdown content"""
        chunks = []
        current_chunk = []
        current_length = 0
        max_chunk_size = 1500
        
        lines = markdown.split("\n")
        
        for line in lines:
            line_length = len(line)
            
            if line.strip().startswith("# ") and current_chunk and current_length > 300:
                chunks.append("\n".join(current_chunk))
                current_chunk = []
                current_length = 0
            
            current_chunk.append(line)
            current_length += line_length
            
            if current_length >= max_chunk_size:
                chunks.append("\n".join(current_chunk))
                current_chunk = []
                current_length = 0
        
        if current_chunk:
            chunks.append("\n".join(current_chunk))
        
        chunks = [chunk.strip() for chunk in chunks if len(chunk.strip()) > 100]
        return chunks
    
    def _categorize_links(self, links: List[str], base_url: str) -> Dict[str, List[Dict]]:
        """Categorize links into different types"""
        categorized = {
            "internal": [],
            "external": [],
            "social_media": [],
            "contact_pages": [],
            "resource_pages": []
        }
        
        base_domain = urlparse(base_url).netloc
        social_domains = ["facebook.com", "twitter.com", "linkedin.com", "instagram.com", "youtube.com", "tiktok.com", "pinterest.com", "github.com", "x.com", "medium.com"]
        contact_keywords = ["contact", "about", "team", "careers", "jobs", "company"]
        resource_keywords = ["blog", "resources", "docs", "documentation", "pricing", "plans"]
        
        for link in links:
            try:
                if not link or not isinstance(link, str):
                    continue
                
                full_url = urljoin(base_url, link)
                parsed = urlparse(full_url)
                
                link_info = {"url": full_url, "text": parsed.path.split("/")[-1] or parsed.netloc, "domain": parsed.netloc}
                
                if any(social in parsed.netloc for social in social_domains):
                    categorized["social_media"].append(link_info)
                elif parsed.netloc == base_domain or not parsed.netloc:
                    categorized["internal"].append(link_info)
                    path_lower = parsed.path.lower()
                    if any(keyword in path_lower for keyword in contact_keywords):
                        categorized["contact_pages"].append(link_info)
                    if any(keyword in path_lower for keyword in resource_keywords):
                        categorized["resource_pages"].append(link_info)
                else:
                    categorized["external"].append(link_info)
            except Exception as e:
                print(f"[SCRAPER] Error processing link {link}: {str(e)}")
                continue
        
        return categorized
    
    def _extract_contact_info(self, markdown: str, html: str, links: List[str], chunks: Optional[List[str]] = None) -> Dict:
        """Extract contact information"""
        contact_info = {"emails": [], "phones": [], "addresses": [], "social_media": {}}
        links = links or []
        
        text_sources = [markdown or ""]
        if chunks:
            text_sources.extend(chunks[:20])

        if not any(text_sources) and html:
            try:
                text_sources.append(self.html_converter.handle(html))
            except Exception:
                text_sources.append(html)

        combined_text = "\n".join([source for source in text_sources if source])

        email_pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
        emails = set(re.findall(email_pattern, combined_text))

        for link in links:
            href = ""
            if isinstance(link, dict):
                href = str(link.get("url") or link.get("href") or "")
            else:
                href = str(link)
            if href.startswith("mailto:"):
                emails.add(href.split(":", 1)[1])

        filtered_emails = [email for email in emails if not any(skip in email.lower() for skip in ["example.com", "test.com", "domain.com", "yourcompany.com"])]
        contact_info["emails"] = sorted(filtered_emails)[:8]

        phone_pattern = r"(?:(?:\+\d{1,3}[\s-]?)?(?:\(\d{2,4}\)|\d{2,4})[\s-]?)?(?:\d{3,4}[\s-]?){2,3}\d{3,4}"
        raw_phone_matches = re.findall(phone_pattern, combined_text)

        cleaned_phones = set()
        for match in raw_phone_matches:
            digits = re.sub(r"\D", "", match)
            if 9 <= len(digits) <= 15:
                normalized = self._format_phone_number(match)
                if normalized:
                    cleaned_phones.add(normalized)

        contact_info["phones"] = sorted(cleaned_phones)[:8]

        contact_info["addresses"] = self._extract_addresses_from_markdown(combined_text)

        social_platforms = {
            "facebook": "facebook.com",
            "twitter": "twitter.com",
            "x": "x.com",
            "linkedin": "linkedin.com",
            "instagram": "instagram.com",
            "youtube": "youtube.com",
            "github": "github.com",
            "tiktok": "tiktok.com"
        }

        for platform, domain in social_platforms.items():
            platform_links = []
            for link in links:
                link_url = ""
                if isinstance(link, dict):
                    link_url = str(link.get("url") or link.get("href") or "")
                    display = link.get("url") or link.get("text") or link_url
                else:
                    link_url = str(link)
                    display = link_url
                if domain in link_url.lower():
                    platform_links.append(display)
            if platform_links:
                contact_info["social_media"][platform] = platform_links[:8]

        validation_context = combined_text[:6000]
        contact_info["emails"] = self._validate_contact_field("email addresses", contact_info["emails"], validation_context)
        contact_info["phones"] = self._validate_contact_field("phone numbers", contact_info["phones"], validation_context)
        contact_info["addresses"] = self._validate_contact_field("physical addresses", contact_info["addresses"], validation_context)

        flat_social = []
        for platform, entries in contact_info["social_media"].items():
            for entry in entries:
                flat_social.append(f"{platform}:{entry}")

        validated_social = self._validate_contact_field("social media links", flat_social, validation_context)
        rebuilt_social = {}
        for item in validated_social:
            if ":" in item:
                platform, link_value = item.split(":", 1)
                platform = platform.strip()
                rebuilt_social.setdefault(platform, [])
                link = link_value.strip()
                if link and link not in rebuilt_social[platform]:
                    rebuilt_social[platform].append(link)

        if rebuilt_social:
            for platform in rebuilt_social:
                rebuilt_social[platform] = rebuilt_social[platform][:5]
            contact_info["social_media"] = rebuilt_social

        return contact_info

    def _format_phone_number(self, phone: str) -> Optional[str]:
        digits = re.sub(r"\D", "", phone)
        if not digits:
            return None
        if len(digits) == 10:
            return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
        if len(digits) == 11 and digits.startswith("1"):
            return f"+1 {digits[1:4]}-{digits[4:7]}-{digits[7:]}"
        if len(digits) >= 11:
            return f"+{digits[:len(digits)-10]} {digits[-10:-7]}-{digits[-7:-4]}-{digits[-4:]}"
        return phone.strip()

    def _extract_addresses_from_markdown(self, text: str) -> List[str]:
        lines = [line.strip() for line in text.splitlines()]
        addresses = []
        for idx, line in enumerate(lines):
            if not line:
                continue
            if re.search(r"\b(address|location|headquarters|office|hq)\b", line, re.IGNORECASE):
                collected = []
                base_line = re.sub(r"(?i)^(address|location|headquarters|office|hq)[:\-]*", "", line).strip()
                if base_line:
                    collected.append(base_line)
                j = idx + 1
                while j < len(lines) and lines[j] and len(collected) < 4:
                    collected.append(lines[j])
                    j += 1
                candidate = " ".join(collected).strip()
                if candidate and self._looks_like_address(candidate):
                    addresses.append(candidate)

        unique_addresses = []
        seen = set()
        for address in addresses:
            key = address.lower()
            if key not in seen:
                seen.add(key)
                unique_addresses.append(address)

        return unique_addresses[:3]

    def _looks_like_address(self, candidate: str) -> bool:
        if len(candidate) < 10:
            return False
        if re.search(r"\d{1,5}\s+\w+", candidate) and re.search(r"(street|st\.?|avenue|ave\.?|road|rd\.?|boulevard|blvd\.?|suite|floor|drive|dr\.?|lane|ln\.?|city|state|zip|postal|country)", candidate, re.IGNORECASE):
            return True
        if re.search(r"\b[A-Z][a-z]+,\s*[A-Z]{2}\b", candidate):
            return True
        if re.search(r"\b\d{5}(-\d{4})?\b", candidate):
            return True
        return False

    def _validate_contact_field(self, field_name: str, candidates: List[str], context: str) -> List[str]:
        if not candidates:
            return []
        try:
            prompt = ChatPromptTemplate.from_template(
                """You are validating contact details extracted from a website.
Context:
{context}

Candidates ({field_name}):
{candidates}

Return ONLY a JSON array of the candidates that are explicitly supported by the context text. Use the exact text for each confirmed entry. If none are valid, return []."""
            )

            messages = prompt.format_messages(context=context, field_name=field_name, candidates=json.dumps(candidates))
            response = self.llm.invoke(messages)
            content = response.content.strip()

            json_start = content.find('[')
            json_end = content.rfind(']') + 1
            if json_start != -1 and json_end > json_start:
                try:
                    parsed = json.loads(content[json_start:json_end])
                    if isinstance(parsed, list):
                        cleaned = []
                        seen = set()
                        for item in parsed:
                            if not isinstance(item, str):
                                continue
                            value = item.strip()
                            if value and value in candidates and value not in seen:
                                seen.add(value)
                                cleaned.append(value)
                        return cleaned
                except json.JSONDecodeError:
                    pass
        except Exception as e:
            print(f"[SCRAPER] Contact validation error for {field_name}: {e}")
        return candidates[:5]
