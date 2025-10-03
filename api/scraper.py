from __future__ import annotations

from typing import Dict, Optional, List, Tuple, Any
import ast
import os
import re
import json
from collections import OrderedDict

import requests
from bs4 import BeautifulSoup  # type: ignore[import-not-found]
import html2text  # type: ignore[import-not-found]
from dotenv import load_dotenv

try:
    from firecrawl.firecrawl import FirecrawlApp  # type: ignore[import-not-found]
except ImportError:
    from firecrawl import FirecrawlApp  # type: ignore[import-not-found]

from langchain_groq import ChatGroq  # type: ignore[import-not-found]
from langchain.prompts import ChatPromptTemplate
from urllib.parse import urlparse, urljoin


load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env.local"))


class WebsiteScraper:
    """Web scraper using Firecrawl API with BeautifulSoup fallback"""

    def __init__(self, llm=None):
        # Initialize Firecrawl if available
        self.use_firecrawl = False
        self.app = None

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

                        payload = self._prepare_cache_payload(url_value, data_value)
                        cache[url_value] = payload

                        sanitized_entry = {'url': url_value, 'data': payload}
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
        """Save scraped raw data to cache"""
        try:
            payload = self._prepare_cache_payload(url, data)
            entry = {
                'url': url,
                'data': payload,
                'timestamp': json.dumps({'timestamp': None})  # Could add actual timestamp
            }
            with open(self.cache_file, 'a', encoding='utf-8') as f:
                json.dump(entry, f, ensure_ascii=False)
                f.write('\n')
            self.cache[url] = payload
            print(f"[CACHE] Saved {url} to cache")
        except Exception as e:
            print(f"[CACHE] Error saving to cache: {e}")

    def _prepare_cache_payload(self, url: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a minimal cache payload from raw or structured data."""
        payload: Dict[str, Any] = {
            'url': url or data.get('url', '')
        }

        markdown = data.get('markdown_content') or data.get('markdown') or ''
        payload['markdown_content'] = markdown

        html_content = data.get('html_content') or data.get('html') or ''
        payload['html_content'] = html_content

        metadata = data.get('metadata')
        if isinstance(metadata, dict) and metadata:
            payload['metadata'] = metadata

        links = data.get('links')
        if not links and isinstance(data.get('all_links'), dict):
            aggregated: List[str] = []
            for group in data['all_links'].values():
                if not isinstance(group, list):
                    continue
                for entry in group:
                    if isinstance(entry, dict):
                        href = entry.get('url') or entry.get('href')
                        if href:
                            aggregated.append(str(href))
            if aggregated:
                links = aggregated
        if links:
            if isinstance(links, (list, tuple, set)):
                sanitized_links = []
                for item in links:
                    if isinstance(item, (str, dict)):
                        sanitized_links.append(item)
                    else:
                        sanitized_links.append(str(item))
                payload['links'] = sanitized_links
            else:
                payload['links'] = [str(links)]

        scraper_used = data.get('scraper_used') or data.get('scraper')
        if scraper_used:
            payload['scraper_used'] = scraper_used

        return payload

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
    
    def _normalize_links_list(self, links_raw: Any, html_content: str) -> List[str]:
        normalized: List[str] = []
        seen: set[str] = set()

        if isinstance(links_raw, (list, tuple, set)):
            for item in links_raw:
                href: Optional[str] = None
                if isinstance(item, str):
                    href = item
                elif isinstance(item, dict):
                    href_value = item.get('url') or item.get('href')
                    if href_value:
                        href = str(href_value)
                if href:
                    href = href.strip()
                    if href and href not in seen:
                        seen.add(href)
                        normalized.append(href)

        if not normalized and html_content:
            try:
                soup = BeautifulSoup(html_content, 'lxml')
                for anchor in soup.find_all('a', href=True):
                    href = anchor['href'].strip()
                    if href and href not in seen:
                        seen.add(href)
                        normalized.append(href)
            except Exception as exc:
                print(f"[SCRAPER] Link normalization failed: {exc}")

        return normalized

    def _build_structured_data(self, raw_payload: Dict[str, Any]) -> Dict[str, Any]:
        if not raw_payload:
            return {}

        url = raw_payload.get('url', '')
        markdown = raw_payload.get('markdown_content') or ''
        html_content = raw_payload.get('html_content') or ''

        if not markdown and html_content:
            try:
                markdown = self.html_converter.handle(html_content)
            except Exception as exc:
                print(f"[SCRAPER] Failed to convert HTML to markdown from cache: {exc}")
                markdown = ''

        metadata = raw_payload.get('metadata') or {}
        links_raw = raw_payload.get('links') or []
        normalized_links = self._normalize_links_list(links_raw, html_content)
        links_for_contact = links_raw if links_raw else normalized_links

        headings = self._extract_headings_from_markdown(markdown)
        chunks = self._create_smart_chunks(markdown)
        main_content = self._extract_main_content(markdown)
        all_links = self._categorize_links(normalized_links, url)
        contact_info = self._extract_contact_info(
            markdown,
            html_content,
            links_for_contact,
            chunks,
            url
        )

        structured_data = {
            "url": url,
            "title": metadata.get("title", ""),
            "description": metadata.get("description", ""),
            "keywords": metadata.get("keywords", ""),
            "og_title": metadata.get("og_title", ""),
            "og_description": metadata.get("og_description", ""),
            "markdown_content": markdown,
            "html_content": html_content,
            "main_content": main_content,
            "headings": headings,
            "structured_chunks": chunks,
            "chunks": chunks,
            "total_chunks": len(chunks),
            "all_links": all_links,
            "internal_pages": all_links.get("internal", []),
            "external_links": all_links.get("external", []),
            "contact_info": contact_info,
            "metadata": metadata,
            "language": metadata.get("language", "en"),
            "scraper_used": raw_payload.get('scraper_used', 'cache')
        }

        return structured_data

    def _get_from_cache(self, url: str) -> Optional[Dict]:
        """Get structured data from cache if available"""
        raw_payload = self.cache.get(url)
        if not raw_payload:
            return None

        if not isinstance(raw_payload, dict) or 'markdown_content' not in raw_payload:
            raw_payload = self._prepare_cache_payload(url, raw_payload or {})
            self.cache[url] = raw_payload

        try:
            return self._build_structured_data(raw_payload)
        except Exception as exc:
            print(f"[CACHE] Failed to rebuild structured data for {url}: {exc}")
            return None
    
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
            
            raw_payload = {
                "url": url,
                "markdown_content": markdown_content,
                "html_content": html_content,
                "metadata": metadata,
                "links": links,
                "scraper_used": "firecrawl"
            }

            structured_data = self._build_structured_data(raw_payload)

            print(f"[SCRAPER] Processed {structured_data.get('total_chunks', 0)} content chunks")

            # Save to cache
            self._save_to_cache(url, raw_payload)
            
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
            
            raw_payload = {
                "url": url,
                "markdown_content": markdown_content,
                "html_content": str(soup),
                "metadata": metadata,
                "links": links,
                "scraper_used": "beautifulsoup"
            }

            structured_data = self._build_structured_data(raw_payload)

            print(f"[SCRAPER] BeautifulSoup fallback processed {structured_data.get('total_chunks', 0)} content chunks")

            # Save to cache
            self._save_to_cache(url, raw_payload)
            
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
        """Create section-aware chunks from markdown content."""

        if not markdown:
            return []

        max_chunk_size = 1500
        min_chunk_length = 80

        def split_section(section_text: str, heading: Optional[str]) -> List[str]:
            text = section_text.strip()
            if not text:
                return []

            if len(text) <= max_chunk_size:
                return [text]

            paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
            if not paragraphs:
                # Fallback to fixed-width splitting
                return [text[i:i + max_chunk_size] for i in range(0, len(text), max_chunk_size)]

            parts: List[str] = []
            current: List[str] = []

            for paragraph in paragraphs:
                candidate = "\n\n".join(current + [paragraph]).strip()
                if len(candidate) > max_chunk_size and current:
                    parts.append("\n\n".join(current))
                    current = [paragraph]
                else:
                    current.append(paragraph)

            if current:
                parts.append("\n\n".join(current))

            formatted: List[str] = []
            for idx, part in enumerate(parts):
                part_text = part.strip()
                if not part_text:
                    continue
                if heading and not part_text.startswith(heading):
                    prefix = heading if idx == 0 else f"{heading} (cont.)"
                    formatted.append(f"{prefix}\n{part_text}".strip())
                else:
                    formatted.append(part_text)
            return formatted

        chunks: List[str] = []
        lines = markdown.splitlines()
        current_heading: Optional[str] = None
        current_lines: List[str] = []

        def flush_current_section():
            if not current_lines and not current_heading:
                return
            section_lines: List[str] = []
            if current_heading:
                section_lines.append(current_heading)
            section_lines.extend(current_lines)
            section_text = "\n".join(section_lines)
            chunks.extend(split_section(section_text, current_heading))

        heading_pattern = re.compile(r"^(#{1,6}\s+.+)")

        for line in lines:
            heading_match = heading_pattern.match(line.strip())
            if heading_match:
                flush_current_section()
                current_heading = heading_match.group(1).strip()
                current_lines = []
            else:
                current_lines.append(line)

        flush_current_section()

        # If there was content before the first heading, make sure it's captured
        if not chunks and current_lines:
            chunks.extend(split_section("\n".join(current_lines), None))

        cleaned_chunks = []
        seen: set[str] = set()
        for chunk in chunks:
            trimmed = chunk.strip()
            if len(trimmed) < min_chunk_length:
                continue
            if trimmed in seen:
                continue
            seen.add(trimmed)
            cleaned_chunks.append(trimmed)

        return cleaned_chunks
    
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
    
    def _extract_contact_info(
        self,
        markdown: str,
        html: str,
        links: List[Any],
        chunks: Optional[List[str]] = None,
        base_url: str = ""
    ) -> Dict:
        """Collect footer/contact page context and let the LLM summarise it into structured data."""

        default_info = {
            "emails": [],
            "phones": [],
            "addresses": [],
            "social_media": {},
            "other_contacts": []
        }

        context_chunks: List[str] = []

        if html:
            try:
                soup = BeautifulSoup(html, "lxml")
                footer = soup.find("footer")
                if footer:
                    footer_text = footer.get_text(" ", strip=True)
                    if footer_text:
                        context_chunks.append(f"Footer\n{footer_text}")
            except Exception as exc:
                print(f"[SCRAPER] Footer extraction failed: {exc}")

        contact_links = self._find_contact_links(links, base_url)
        for contact_url in contact_links[:2]:
            page_text = self._fetch_contact_page_text(contact_url)
            if page_text:
                context_chunks.append(f"Contact page ({contact_url})\n{page_text}")

        if not context_chunks and markdown:
            tail = markdown[-1800:]
            if tail:
                context_chunks.append(f"Page excerpt\n{tail}")

        if not context_chunks:
            return default_info

        combined_context = "\n\n---\n\n".join(context_chunks)
        combined_context = combined_context[:8000]

        system_prompt = (
            "You analyse website contact information. "
            "Return concise details that appear in the provided context only."
        )
        human_prompt = (
            "Extract contact details from the context below. "
            "If a field is missing, return an empty list/dict. Respond with valid JSON only, matching this schema exactly:\n"
            "{{\n"
            "  \"emails\": [string],\n"
            "  \"phones\": [string],\n"
            "  \"addresses\": [string],\n"
            "  \"social_media\": {{platform: [string]}},\n"
            "  \"other_contacts\": [string]\n"
            "}}\n\n"
            "Context:\n{context}"
        )

        try:
            prompt = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                ("human", human_prompt)
            ])
            messages = prompt.format_messages(context=combined_context)
            response = self.llm.invoke(messages)
            parsed = self._parse_contact_response(response.content)
            if parsed:
                return self._normalize_contact_result(parsed, default_info)
        except Exception as exc:
            print(f"[SCRAPER] Contact extraction via LLM failed: {exc}")

        return default_info

    def _find_contact_links(self, links: List[Any], base_url: str) -> List[str]:
        candidates: List[str] = []
        if not links:
            return candidates

        keywords = ["contact", "support", "help", "customer", "about"]
        for raw_link in links:
            if isinstance(raw_link, dict):
                href = str(raw_link.get("url") or raw_link.get("href") or "")
            else:
                href = str(raw_link or "")

            if not href:
                continue

            combined = urljoin(base_url, href) if base_url else href
            parsed = urlparse(combined)
            scheme = parsed.scheme.lower()
            if scheme and scheme not in ("http", "https"):
                continue

            lower = combined.lower()
            if any(keyword in lower for keyword in keywords):
                candidates.append(combined)

        # Preserve order but remove duplicates
        seen = set()
        ordered: List[str] = []
        for url_candidate in candidates:
            if url_candidate not in seen:
                seen.add(url_candidate)
                ordered.append(url_candidate)
        return ordered

    def _fetch_contact_page_text(self, url: str) -> Optional[str]:
        if not url:
            return None

        parsed = urlparse(url)
        scheme = parsed.scheme.lower()
        if scheme and scheme not in ("http", "https"):
            return None

        try:
            if self.use_firecrawl and self.app:
                page = self.app.scrape(url, formats=["markdown"], only_main_content=True, wait_for=1500)
                if page:
                    markdown = getattr(page, "markdown", "")
                    if markdown:
                        return markdown

            response = requests.get(url, headers=self.headers, timeout=8)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "lxml")
            return soup.get_text(" ", strip=True)
        except Exception as exc:
            print(f"[SCRAPER] Could not fetch contact page {url}: {exc}")
            return None

    def _parse_contact_response(self, content: str) -> Optional[Dict[str, Any]]:
        if not content:
            return None

        text = content.strip()

        fence_match = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
        if fence_match:
            text = fence_match.group(1).strip()

        start = text.find("{")
        end = text.rfind("}") + 1
        if start == -1 or end <= start:
            return None

        candidate = text[start:end]

        def _normalise_quotes(payload: str) -> str:
            replacements = {
                "\u201c": '"',
                "\u201d": '"',
                "\u2018": "'",
                "\u2019": "'",
            }
            for bad, good in replacements.items():
                payload = payload.replace(bad, good)
            return payload

        attempts = []

        base_candidate = candidate.strip()
        if base_candidate:
            attempts.append(base_candidate)

        cleaned_trailing_commas = re.sub(r",\s*([}\]])", r"\1", base_candidate)
        if cleaned_trailing_commas != base_candidate:
            attempts.append(cleaned_trailing_commas)

        normalized_quotes = _normalise_quotes(base_candidate)
        if normalized_quotes not in attempts:
            attempts.append(normalized_quotes)

        normalized_quotes_cleaned = re.sub(r",\s*([}\]])", r"\1", normalized_quotes)
        if normalized_quotes_cleaned not in attempts:
            attempts.append(normalized_quotes_cleaned)

        last_error: Optional[Exception] = None
        for attempt in attempts:
            try:
                return json.loads(attempt)
            except json.JSONDecodeError as exc:
                last_error = exc
                continue

        if last_error:
            try:
                literal_candidate = ast.literal_eval(base_candidate)
                if isinstance(literal_candidate, dict):
                    return literal_candidate
            except Exception:
                pass

        if last_error:
            print(f"[SCRAPER] Contact JSON parse failed: {last_error}")
            if hasattr(last_error, "doc"):
                snippet = last_error.doc
                if snippet:
                    print(f"[SCRAPER] Contact JSON snippet: {snippet[:200]}")

        return None

    def _normalize_contact_result(self, data: Dict[str, Any], default_info: Dict[str, Any]) -> Dict[str, Any]:
        result = {key: default_info.get(key, []) for key in default_info}

        def _extract_list(key: str) -> List[str]:
            raw_value = data.get(key)
            if isinstance(raw_value, list):
                cleaned = []
                for item in raw_value:
                    if isinstance(item, str):
                        value = item.strip()
                        if value and value not in cleaned:
                            cleaned.append(value)
                return cleaned
            return []

        result["emails"] = _extract_list("emails")[:8]
        result["phones"] = _extract_list("phones")[:8]
        result["addresses"] = _extract_list("addresses")[:5]
        result["other_contacts"] = _extract_list("other_contacts")[:5]

        social_media: Dict[str, List[str]] = {}
        raw_social = data.get("social_media")
        if isinstance(raw_social, dict):
            for platform, entries in raw_social.items():
                if not isinstance(platform, str):
                    continue
                if isinstance(entries, list):
                    cleaned_entries = []
                    for entry in entries:
                        if isinstance(entry, str):
                            value = entry.strip()
                            if value and value not in cleaned_entries:
                                cleaned_entries.append(value)
                    if cleaned_entries:
                        social_media[platform.strip().lower()] = cleaned_entries[:5]
                elif isinstance(entries, str):
                    value = entries.strip()
                    if value:
                        social_media.setdefault(platform.strip().lower(), []).append(value)

        result["social_media"] = social_media
        return result
