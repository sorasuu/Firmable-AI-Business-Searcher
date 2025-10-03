from __future__ import annotations

from typing import Any, Dict, List, Optional

from api.chat import ConversationalAgent
from api.scraper import WebsiteScraper
from api.analyzer import AIAnalyzer


class AnalysisOrchestrator:
    """Coordinates scraping, analysis, and enrichment steps for a website."""

    def __init__(
        self,
        scraper: WebsiteScraper,
        analyzer: AIAnalyzer,
        chat_agent: ConversationalAgent,
    ) -> None:
        self._scraper = scraper
        self._analyzer = analyzer
        self._chat_agent = chat_agent

    @property
    def chat_agent(self) -> ConversationalAgent:
        return self._chat_agent

    def analyze(self, url: str, questions: Optional[List[str]] = None) -> Dict[str, Any]:
        scraped_data = self._scraper.scrape_website(url)
        insights = self._analyzer.analyze_website(scraped_data, questions)

        # Cache website data for conversational follow-ups
        self._chat_agent.cache_website_data(url, scraped_data, insights)

        if questions:
            self._augment_custom_answers(url, questions, insights)

        self._augment_contact_profile(url, insights)
        return insights

    def _augment_custom_answers(self, url: str, questions: List[str], insights: Dict[str, Any]) -> None:
        existing_answers = dict(insights.get("custom_answers") or {})
        updated_answers = dict(existing_answers)
        source_chunks = dict(insights.get("source_chunks") or {})

        for question in questions[:5]:
            result = self._chat_agent.answer_question_with_sources(url, question)
            if result:
                updated_answers[question] = result["answer"]
                source_chunks[question] = result.get("source_chunks", [])
            elif question not in updated_answers and question in existing_answers:
                updated_answers[question] = existing_answers[question]

        if updated_answers:
            insights["custom_answers"] = updated_answers
        if source_chunks:
            insights["source_chunks"] = source_chunks

    def _augment_contact_profile(self, url: str, insights: Dict[str, Any]) -> None:
        contact_result = self._chat_agent.extract_contact_profile(url)
        if not contact_result:
            return

        contact_info = contact_result.get("contact_info")
        if not contact_info:
            return

        existing_contact = dict(insights.get("contact_info") or {})
        merged_contact = self._merge_contact_info(existing_contact, contact_info)
        insights["contact_info"] = merged_contact

        source_chunks = dict(insights.get("source_chunks") or {})
        source_chunks["contact_info"] = contact_result.get("source_chunks", [])
        insights["source_chunks"] = source_chunks

    @staticmethod
    def _merge_contact_info(existing: Dict[str, Any], updates: Dict[str, Any]) -> Dict[str, Any]:
        merged: Dict[str, Any] = dict(existing)

        def merge_list(key: str) -> None:
            existing_list = existing.get(key) or []
            update_list = updates.get(key) or []
            if not isinstance(existing_list, list):
                existing_list = [existing_list] if existing_list else []
            if not isinstance(update_list, list):
                update_list = [update_list] if update_list else []

            combined: List[str] = []
            seen: set[str] = set()
            for item in [*existing_list, *update_list]:
                if not item:
                    continue
                text = str(item).strip()
                if not text:
                    continue
                lowered = text.lower()
                if lowered not in seen:
                    seen.add(lowered)
                    combined.append(text)

            if combined:
                merged[key] = combined

        for key in ("emails", "phones", "contact_urls", "addresses"):
            merge_list(key)

        existing_social = existing.get("social_media") or {}
        update_social = updates.get("social_media") or {}

        social_merged: Dict[str, List[str]] = {}
        if isinstance(existing_social, dict):
            for network, links in existing_social.items():
                if links:
                    social_merged[network] = list(links) if isinstance(links, list) else [links]
        if isinstance(update_social, dict):
            for network, links in update_social.items():
                existing_links = social_merged.get(network, [])
                combined_links = existing_links + (
                    list(links) if isinstance(links, list) else ([links] if links else [])
                )
                deduped: List[str] = []
                seen_links: set[str] = set()
                for link in combined_links:
                    text = str(link).strip()
                    if not text:
                        continue
                    lowered = text.lower()
                    if lowered not in seen_links:
                        seen_links.add(lowered)
                        deduped.append(text)
                if deduped:
                    social_merged[network] = deduped
        if social_merged:
            merged["social_media"] = social_merged

        return merged
