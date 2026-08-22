import logging
import re
from typing import List

from backend.rag.retriever import search_neighborhood_info
from backend.rag.reranker import rerank_results

logger = logging.getLogger(__name__)


def _clean_chunk_text(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", text).strip()
    if len(cleaned) > 320:
        cleaned = cleaned[:317].rstrip() + "..."
    return cleaned


def format_insights_for_display(locality: str, topic: str = "general") -> str:
    """
    Returns concise, user-facing neighborhood copy for property cards.
    """
    raw_results = search_neighborhood_info(locality, topic, limit=6)
    logger.debug(
        "format_insights_for_display: locality=%s topic=%s raw_results=%d",
        locality, topic, len(raw_results) if raw_results else 0,
    )
    if not raw_results:
        logger.warning("No RAG results found for locality: %s", locality)
        return ""

    top_results = rerank_results(raw_results, query=f"{locality} {topic}")
    # If reranker filtered everything out, fall back to raw results by score
    if not top_results:
        logger.warning(
            "Reranker returned 0 results for %s — falling back to raw results", locality
        )
        top_results = sorted(raw_results, key=lambda r: r.get("score", 0), reverse=True)

    snippets: List[str] = []
    seen = set()

    for result in top_results[:3]:
        snippet = _clean_chunk_text(result.get("text", ""))
        if not snippet or snippet in seen:
            continue
        seen.add(snippet)
        snippets.append(f"• {snippet}")

    if not snippets:
        logger.warning("All snippets were empty or duplicate for locality: %s", locality)
        return ""

    header = f"What residents say about {locality}:"
    return f"{header}\n" + "\n".join(snippets)




def synthesize_neighborhood_info(locality: str, topic: str = "general") -> str:
    """
    Returns RAG context for the LLM orchestrator tool calls.
    """
    raw_results = search_neighborhood_info(locality, topic, limit=10)
    if not raw_results:
        return (
            f"No verified neighborhood information is available for {locality} "
            f"on {topic}. Tell the user explicitly rather than guessing."
        )

    top_results = rerank_results(raw_results, query=f"{locality} {topic}")
    context = f"Neighborhood context for {locality} (topic: {topic}):\n\n"
    for index, result in enumerate(top_results, start=1):
        context += (
            f"--- Source [{index}] ({result.get('url', 'Unknown URL')}) ---\n"
            f"{result.get('text', '')}\n\n"
        )
    context += (
        "Use only the information above. Cite sources as [1], [2], etc. "
        "If the context does not answer the question, say you are unsure."
    )
    return context
