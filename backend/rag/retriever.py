import json
import logging
import math
import os
import re
from typing import Any, Dict, List, Optional

from qdrant_client import QdrantClient
from qdrant_client.models import FieldCondition, Filter, MatchValue

from backend.config import settings
from rag_ingestion.embedder import embed_text

logger = logging.getLogger(__name__)

_CHUNKS_CACHE: Optional[List[Dict[str, Any]]] = None


def get_qdrant_client() -> QdrantClient:
    url = settings.VECTOR_DB_URL
    api_key = settings.VECTOR_DB_API_KEY
    if not url or not api_key:
        raise ValueError("VECTOR_DB_URL and VECTOR_DB_API_KEY must be set in .env")
    return QdrantClient(url=url, api_key=api_key, timeout=15)


def _load_local_chunks() -> List[Dict[str, Any]]:
    global _CHUNKS_CACHE
    if _CHUNKS_CACHE is not None:
        return _CHUNKS_CACHE

    # retriever.py lives at: <root>/backend/rag/retriever.py
    # rag_ingestion/ lives at: <root>/rag_ingestion/
    # So we need to go up 3 levels: rag/ -> backend/ -> <root>
    _this_dir = os.path.dirname(os.path.abspath(__file__))  # backend/rag/
    _backend_dir = os.path.dirname(_this_dir)               # backend/
    _root_dir = os.path.dirname(_backend_dir)               # <project root>

    chunks_path = os.path.join(_root_dir, "rag_ingestion", "chunks.json")
    embeddings_path = os.path.join(_root_dir, "rag_ingestion", "embeddings.json")

    try:
        if os.path.exists(embeddings_path):
            with open(embeddings_path, encoding="utf-8") as handle:
                _CHUNKS_CACHE = json.load(handle)
                logger.info("Loaded %d entries from embeddings.json", len(_CHUNKS_CACHE))
                return _CHUNKS_CACHE
        if os.path.exists(chunks_path):
            with open(chunks_path, encoding="utf-8") as handle:
                _CHUNKS_CACHE = json.load(handle)
                logger.info("Loaded %d entries from chunks.json", len(_CHUNKS_CACHE))
                return _CHUNKS_CACHE
    except Exception as exc:
        logger.error("Failed to load local RAG chunks: %s", exc)

    _CHUNKS_CACHE = []
    return _CHUNKS_CACHE


def _cosine_similarity(a: List[float], b: List[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _normalize_locality_name(locality: str) -> str:
    cleaned = locality.strip()
    aliases = {
        # Koramangala
        "core mangla": "Koramangala",
        "koramangla": "Koramangala",
        "kormangala": "Koramangala",
        "koramangala": "Koramangala",
        # Indiranagar
        "indira nagar": "Indiranagar",
        "indiranagar": "Indiranagar",
        "indranagar": "Indiranagar",
        "indira nagar": "Indiranagar",
        # HSR Layout
        "hsr": "HSR Layout",
        "hsr layout": "HSR Layout",
        # Whitefield
        "whitefield": "Whitefield",
        "whitfield": "Whitefield",
        "whitefeild": "Whitefield",
        "white field": "Whitefield",
        # Bellandur
        "bellandur": "Bellandur",
        "bellanduru": "Bellandur",
        # Marathahalli
        "marathahalli": "Marathahalli",
        "marathalli": "Marathahalli",
        "marathon halli": "Marathahalli",
    }
    return aliases.get(cleaned.lower(), cleaned)


def _search_local_chunks(locality: str, topic: str, limit: int = 5) -> List[Dict[str, Any]]:
    locality = _normalize_locality_name(locality)
    chunks = _load_local_chunks()
    if not chunks:
        return []

    locality_lower = locality.lower()
    topic_lower = topic.lower()
    matched: List[Dict[str, Any]] = []

    for chunk in chunks:
        chunk_locality = str(chunk.get("locality", "")).lower()
        text = chunk.get("text", "")
        themes = " ".join(chunk.get("themes", [])).lower()

        locality_match = (
            chunk_locality == locality_lower
            or locality_lower in chunk_locality
            or locality_lower in text.lower()
            or chunk_locality in locality_lower
        )
        if not locality_match:
            continue

        score = 1.0
        if topic_lower != "general" and topic_lower in themes:
            score += 0.5
        if topic_lower != "general" and topic_lower in text.lower():
            score += 0.25

        matched.append(
            {
                "text": text,
                "url": chunk.get("url", ""),
                "score": score,
            }
        )

    matched.sort(key=lambda item: item["score"], reverse=True)
    return matched[:limit]


def search_neighborhood_info(
    locality: str, topic: str = "general", limit: int = 5
) -> List[Dict[str, Any]]:
    """Search Qdrant first, then fall back to local chunks.json / embeddings.json."""
    locality = _normalize_locality_name(locality)
    query = f"{locality} {topic} neighborhood living safety transport culture"

    try:
        client = get_qdrant_client()
        query_vector = embed_text(query)

        locality_filter = Filter(
            should=[
                FieldCondition(key="locality", match=MatchValue(value=locality)),
                FieldCondition(key="locality", match=MatchValue(value=locality.lower())),
            ]
        )

        # Query Qdrant with locality filter
        hits = []
        if hasattr(client, "query_points"):
            res = client.query_points(
                collection_name="neighborhoods",
                query=query_vector,
                query_filter=locality_filter,
                limit=limit,
                score_threshold=0.35,
            )
            hits = res.points
        elif hasattr(client, "search"):
            hits = client.search(
                collection_name="neighborhoods",
                query_vector=query_vector,
                query_filter=locality_filter,
                limit=limit,
                score_threshold=0.35,
            )

        if hits:
            return [
                {
                    "text": hit.payload.get("text", ""),
                    "url": hit.payload.get("url", ""),
                    "score": hit.score,
                }
                for hit in hits
            ]

        # Broader vector search without strict locality filter
        if hasattr(client, "query_points"):
            res = client.query_points(
                collection_name="neighborhoods",
                query=query_vector,
                limit=limit,
                score_threshold=0.45,
            )
            hits = res.points
        elif hasattr(client, "search"):
            hits = client.search(
                collection_name="neighborhoods",
                query_vector=query_vector,
                limit=limit,
                score_threshold=0.45,
            )

        filtered = [
            {
                "text": hit.payload.get("text", ""),
                "url": hit.payload.get("url", ""),
                "score": hit.score,
            }
            for hit in hits
            if locality.lower() in hit.payload.get("text", "").lower()
            or locality.lower() in hit.payload.get("locality", "").lower()
        ]
        if filtered:
            return filtered
    except Exception as exc:
        logger.warning("Qdrant retrieval failed, using local chunk fallback: %s", exc)

    return _search_local_chunks(locality, topic, limit=limit)
