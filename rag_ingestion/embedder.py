import json
import logging
import os
import time
from typing import Any, Dict, List, Optional

import requests

from backend.config import settings

logger = logging.getLogger(__name__)

_EMBED_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-embedding-2:embedContent"
)
_EMBEDDINGS_CACHE: Optional[List[Dict[str, Any]]] = None


def embed_text(text: str, max_retries: int = 3) -> List[float]:
    """Generate a Gemini embedding vector for a single text query with retry logic."""
    if not settings.GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is not set.")

    url = f"{_EMBED_URL}?key={settings.GEMINI_API_KEY}"
    payload = {
        "model": "models/gemini-embedding-2",
        "content": {"parts": [{"text": text}]},
    }
    
    for attempt in range(1, max_retries + 1):
        try:
            response = requests.post(url, headers={"Content-Type": "application/json"}, json=payload, timeout=30)
            if response.status_code == 200:
                embedding = response.json().get("embedding", {}).get("values", [])
                if embedding:
                    return embedding
                raise ValueError("Gemini embedding API returned an empty vector.")
            elif response.status_code == 429:
                wait_time = attempt * 2
                logger.warning(f"Rate limited (429) on embedding, sleeping {wait_time}s (attempt {attempt}/{max_retries})...")
                time.sleep(wait_time)
            else:
                response.raise_for_status()
        except Exception as e:
            if attempt == max_retries:
                logger.error(f"Embedding failed after {max_retries} attempts: {e}")
                raise e
            time.sleep(attempt * 1.5)

    raise ValueError("Failed to retrieve embedding vector.")


def get_model():
    """Compatibility shim — retriever should call embed_text() directly."""
    return None


def embed_chunks(chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Generates embeddings for ingestion chunks using Gemini."""
    logger.info("Generating embeddings for %s chunks...", len(chunks))
    embedded_chunks: List[Dict[str, Any]] = []

    for index, chunk in enumerate(chunks, start=1):
        try:
            chunk["embedding"] = embed_text(chunk["text"])
            embedded_chunks.append(chunk)
            if index % 10 == 0 or index == len(chunks):
                logger.info(f"Embedded [{index}/{len(chunks)}] chunks...")
            time.sleep(0.2)
        except Exception as exc:
            logger.error("Failed to embed chunk %s: %s", index, exc)

    try:
        output_path = os.path.join(os.path.dirname(__file__), "embeddings.json")
        with open(output_path, "w", encoding="utf-8") as handle:
            json.dump(embedded_chunks, handle)
        logger.info("Saved embeddings to %s", output_path)
    except Exception as exc:
        logger.error("Failed to save embeddings.json: %s", exc)

    return embedded_chunks
