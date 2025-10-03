from __future__ import annotations

import logging
import os
import threading
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional

import numpy as np
import requests

try:  # pragma: no cover - optional dependency guard
    import faiss  # type: ignore
except ImportError:  # pragma: no cover - handled gracefully
    faiss = None  # type: ignore


logger = logging.getLogger(__name__)


def _batched(iterable: Iterable[str], batch_size: int) -> Iterable[List[str]]:
    batch: List[str] = []
    for item in iterable:
        batch.append(item)
        if len(batch) == batch_size:
            yield batch
            batch = []
    if batch:
        yield batch


class DeepInfraEmbeddingClient:
    """Client for fetching embeddings from DeepInfra's hosted models."""

    def __init__(self, model: str = "BAAI/bge-m3", timeout: int = 60, batch_size: int = 16) -> None:
        self.model = model
        self.timeout = timeout
        self.batch_size = max(1, batch_size)
        self.api_key = os.environ.get("DEEPINFRA_API_KEY")
        self.available = bool(self.api_key)
        self.endpoint = f"https://api.deepinfra.com/v1/inference/{self.model}"

        if not self.available:
            logger.warning("DEEPINFRA_API_KEY not set; semantic search will be disabled.")

    def embed_texts(self, texts: List[str]) -> np.ndarray:
        filtered = [text.strip() for text in texts if text and text.strip()]
        if not filtered:
            return np.zeros((0, 0), dtype=np.float32)

        if not self.available:
            return np.zeros((0, 0), dtype=np.float32)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        embeddings: List[List[float]] = []

        for batch in _batched(filtered, self.batch_size):
            payload = {"inputs": batch}
            try:
                response = requests.post(
                    self.endpoint,
                    headers=headers,
                    json=payload,
                    timeout=self.timeout,
                )
                response.raise_for_status()
            except requests.RequestException as exc:  # pragma: no cover - network dependent
                logger.error("DeepInfra embedding request failed: %s", exc)
                return np.zeros((0, 0), dtype=np.float32)

            try:
                data = response.json()
            except ValueError as exc:  # pragma: no cover - unexpected payload
                logger.error("Invalid JSON from DeepInfra: %s", exc)
                return np.zeros((0, 0), dtype=np.float32)

            vectors = self._extract_embeddings(data)
            if len(vectors) != len(batch):
                logger.error(
                    "Embedding count mismatch (expected %s, got %s)",
                    len(batch),
                    len(vectors),
                )
                return np.zeros((0, 0), dtype=np.float32)

            embeddings.extend(vectors)

        array = np.asarray(embeddings, dtype=np.float32)
        if array.ndim == 1:
            array = array.reshape(1, -1)
        return array

    @staticmethod
    def _extract_embeddings(payload: Any) -> List[List[float]]:
        """Handle multiple possible response formats from DeepInfra."""
        if isinstance(payload, dict):
            if "outputs" in payload and isinstance(payload["outputs"], list):
                return [DeepInfraEmbeddingClient._extract_vector(item) for item in payload["outputs"]]
            if "data" in payload and isinstance(payload["data"], list):
                return [DeepInfraEmbeddingClient._extract_vector(item) for item in payload["data"]]
            if "embedding" in payload and isinstance(payload["embedding"], (list, tuple)):
                return [list(payload["embedding"])]
            if "embeddings" in payload and isinstance(payload["embeddings"], list):
                return [DeepInfraEmbeddingClient._extract_vector(item) for item in payload["embeddings"]]
        elif isinstance(payload, list):
            return [DeepInfraEmbeddingClient._extract_vector(item) for item in payload]

        return []

    @staticmethod
    def _extract_vector(item: Any) -> List[float]:
        if isinstance(item, dict):
            if "embedding" in item and isinstance(item["embedding"], (list, tuple)):
                return [float(value) for value in item["embedding"]]
            if "vector" in item and isinstance(item["vector"], (list, tuple)):
                return [float(value) for value in item["vector"]]
            if "outputs" in item and isinstance(item["outputs"], (list, tuple)):
                return [float(value) for value in item["outputs"]]
        if isinstance(item, (list, tuple)):
            return [float(value) for value in item]
        raise ValueError("Unsupported embedding item format")


@dataclass
class WebsiteEntry:
    url: str
    scraped_data: Dict[str, Any] = field(default_factory=dict)
    insights: Dict[str, Any] = field(default_factory=dict)
    chunks: List[str] = field(default_factory=list)
    index: Any = None
    dimension: Optional[int] = None

    def has_index(self) -> bool:
        return self.index is not None and self.dimension is not None and self.dimension > 0


class AnalysisStore:
    """In-memory store for analyzed websites and their semantic indexes."""

    def __init__(self, embedder: Optional[DeepInfraEmbeddingClient] = None) -> None:
        self._embedder = embedder or DeepInfraEmbeddingClient()
        self._data: Dict[str, WebsiteEntry] = {}
        self._lock = threading.RLock()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def prepare_site(self, url: str, scraped_data: Dict[str, Any]) -> WebsiteEntry:
        url = (url or scraped_data.get("url") or "").strip()
        if not url:
            raise ValueError("URL is required to prepare site data")

        entry = WebsiteEntry(url=url, scraped_data=scraped_data)
        entry.chunks = self._prepare_chunks(scraped_data.get("structured_chunks", []))

        if faiss is None:
            logger.warning("faiss-cpu is not installed; semantic search disabled.")
        elif entry.chunks:
            vectors = self._embedder.embed_texts(entry.chunks)
            if vectors.size > 0:
                faiss.normalize_L2(vectors)
                index = faiss.IndexFlatIP(vectors.shape[1])
                index.add(vectors)
                entry.index = index
                entry.dimension = vectors.shape[1]
            else:
                logger.info("No embeddings generated for %s; index will be unavailable.", url)

        with self._lock:
            existing = self._data.get(url)
            if existing and existing.insights:
                entry.insights = existing.insights
            self._data[url] = entry

        return entry

    def update_insights(self, url: str, insights: Dict[str, Any]) -> None:
        if not url:
            return
        with self._lock:
            entry = self._data.get(url)
            if entry:
                entry.insights = insights
            else:
                self._data[url] = WebsiteEntry(url=url, insights=insights)

    def store_analysis(self, url: str, scraped_data: Dict[str, Any], insights: Dict[str, Any]) -> WebsiteEntry:
        entry = self.prepare_site(url, scraped_data)
        self.update_insights(url, insights)
        return entry

    def get(self, url: str) -> Optional[WebsiteEntry]:
        with self._lock:
            entry = self._data.get(url)
            if entry:
                return entry
        return None

    def search_chunks(self, url: str, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        if not query or not query.strip():
            return []
        entry = self.get(url)
        if not entry or not entry.has_index() or faiss is None:
            return []

        vectors = self._embedder.embed_texts([query])
        if vectors.size == 0:
            return []
        if vectors.ndim == 1:
            vectors = vectors.reshape(1, -1)

        if entry.dimension and vectors.shape[1] != entry.dimension:
            logger.warning(
                "Embedding dimension mismatch for %s (expected %s, got %s)",
                url,
                entry.dimension,
                vectors.shape[1],
            )
            return []

        faiss.normalize_L2(vectors)
        limit = min(top_k, len(entry.chunks))
        if limit <= 0:
            return []

        scores, indices = entry.index.search(vectors, limit)
        results: List[Dict[str, Any]] = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0 or idx >= len(entry.chunks):
                continue
            results.append(
                {
                    "chunk_index": int(idx),
                    "chunk_text": entry.chunks[idx],
                    "score": float(score),
                }
            )
        return results

    def get_chunks(self, url: str) -> List[str]:
        entry = self.get(url)
        return entry.chunks if entry else []

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _prepare_chunks(chunks: Optional[List[str]]) -> List[str]:
        cleaned: List[str] = []
        seen: set[str] = set()
        if not chunks:
            return cleaned

        for chunk in chunks:
            if not chunk:
                continue
            trimmed = chunk.strip()
            if len(trimmed) < 40:
                continue
            if trimmed in seen:
                continue
            seen.add(trimmed)
            cleaned.append(trimmed)

        return cleaned


analysis_store = AnalysisStore()
