from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict, Optional, Sequence
import re

from rank_bm25 import BM25Okapi


_DEFAULT_STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to",
    "for", "of", "with", "by", "is", "are", "was", "were", "be", "been",
    "being", "have", "has", "had", "do", "does", "did", "will", "would",
    "could", "should", "may", "might", "must", "can", "what", "when",
    "where", "why", "how", "who", "which", "from", "this", "that", "these",
    "those", "into", "about", "as", "it", "its", "their", "they", "them",
    "we", "our", "you", "your"
}


@dataclass
class ChunkSearchResult:
    index: int
    text: str
    score: float


class ChunkSearcher:
    """Lightweight in-memory BM25 searcher over markdown chunks."""

    def __init__(self, chunks: Sequence[str], stopwords: Optional[Sequence[str]] = None):
        self._chunks: List[str] = [chunk or "" for chunk in chunks]
        self._stopwords = set(stopwords or _DEFAULT_STOPWORDS)
        self._tokenized_chunks: List[List[str]] = [self._tokenize(chunk) for chunk in self._chunks]
        self._bm25: Optional[BM25Okapi] = None

        # Build BM25 index only if we have at least one non-empty token list
        if any(tokens for tokens in self._tokenized_chunks):
            # Replace empty token lists with a placeholder token to avoid zero-length docs
            normalized_docs = [tokens or ["content"] for tokens in self._tokenized_chunks]
            self._bm25 = BM25Okapi(normalized_docs)

    def search(self, query: str, top_k: int = 5) -> List[ChunkSearchResult]:
        if not query or not query.strip():
            return []
        if not self._bm25:
            return []

        tokenized_query = self._tokenize(query)
        if not tokenized_query:
            return []

        scores = self._bm25.get_scores(tokenized_query)
        ranked = sorted(enumerate(scores), key=lambda item: item[1], reverse=True)

        results: List[ChunkSearchResult] = []
        for idx, score in ranked[:top_k]:
            if score <= 0:
                continue
            results.append(ChunkSearchResult(index=idx, text=self._chunks[idx], score=float(score)))
        return results

    def _tokenize(self, text: str) -> List[str]:
        words = re.findall(r"\b\w+\b", (text or "").lower())
        filtered = [word for word in words if word and word not in self._stopwords]

        if filtered:
            return filtered

        # Fallback: split on whitespace to capture symbols like emails
        fallback = [(token or "").lower().strip() for token in (text or "").split() if token]
        if fallback:
            return fallback

        return []

    @property
    def chunks(self) -> Sequence[str]:
        return self._chunks
