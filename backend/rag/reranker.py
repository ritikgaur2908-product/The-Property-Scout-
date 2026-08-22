from typing import List, Dict, Any

def rerank_results(results: List[Dict[str, Any]], query: str = "") -> List[Dict[str, Any]]:
    """
    Reranks the results retrieved from Qdrant based on relevance to the query.
    For Phase 3, we simply sort by the vector search score returned by Qdrant.
    We return the top 5 results to keep the context window tight.
    """
    # Sort by score descending
    sorted_results = sorted(results, key=lambda x: x.get("score", 0.0), reverse=True)
    return sorted_results[:5]
