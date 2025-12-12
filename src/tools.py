"""Search tools wrapper for agent integration."""

import logging
from typing import List, Optional
from .retrieval import get_retrieval_strategy, RetrievalResult
from .settings import settings

logger = logging.getLogger(__name__)


def search_knowledge_base(
    query: str,
    strategy: Optional[str] = None,
    top_k: Optional[int] = None,
) -> List[RetrievalResult]:
    """
    Search the knowledge base using the specified retrieval strategy.
    
    This is a thin wrapper around the retrieval module, designed to be
    compatible with agent tool interfaces (e.g., PydanticAI).
    
    Args:
        query: Search query string
        strategy: Retrieval strategy name (defaults to settings)
        top_k: Number of results to return (defaults to settings)
        
    Returns:
        List of RetrievalResult objects
    """
    if strategy is None:
        strategy = settings.retrieval.strategy
    
    if top_k is None:
        top_k = settings.retrieval.top_k
    
    retrieval_strategy = get_retrieval_strategy(strategy)
    results = retrieval_strategy.search(query, top_k=top_k)
    
    logger.info(f"Knowledge base search returned {len(results)} results")
    return results


def format_search_results(results: List[RetrievalResult]) -> str:
    """
    Format search results as a string for display or prompt inclusion.
    
    Args:
        results: List of RetrievalResult objects
        
    Returns:
        Formatted string
    """
    if not results:
        return "No results found."
    
    formatted = []
    for i, result in enumerate(results, 1):
        source_info = result.source or result.doc_id or "Unknown"
        formatted.append(
            f"[{i}] {source_info} (Score: {result.score:.4f})\n"
            f"{result.content[:200]}..."
        )
    
    return "\n\n".join(formatted)

