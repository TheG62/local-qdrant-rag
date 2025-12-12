"""Hybrid retrieval with RRF (Reciprocal Rank Fusion) merge."""

import logging
from typing import List, Dict, Optional
from collections import defaultdict

from .base import RetrievalStrategy
from .semantic import PureSemanticRetrieval
from .fulltext import PureFullTextRetrieval
from .types import RetrievalResult
from ..settings import settings

logger = logging.getLogger(__name__)

# Default minimum score threshold for relevance filtering
DEFAULT_MIN_SCORE = 0.01


class HybridRRFRetrieval(RetrievalStrategy):
    """
    Hybrid retrieval combining semantic and full-text search with RRF merge.
    
    Performs parallel queries (semantic + full-text) and merges results
    using Reciprocal Rank Fusion (RRF).
    
    Note: Qdrant Full-Text uses TF-based scoring, not true BM25.
    RRF-merge behavior may differ from true BM25-based hybrid search.
    """
    
    def __init__(
        self, 
        rrf_k: Optional[int] = None,
        min_score: Optional[float] = DEFAULT_MIN_SCORE,
    ):
        """
        Initialize hybrid RRF retrieval.
        
        Args:
            rrf_k: RRF constant (defaults to settings)
            min_score: Minimum RRF score threshold (filters low-relevance results)
        """
        self.semantic_retrieval = PureSemanticRetrieval()
        self.fulltext_retrieval = PureFullTextRetrieval()
        self.rrf_k = rrf_k or settings.retrieval.rrf_k
        self.min_score = min_score
    
    def search(self, query: str, top_k: int = 10) -> List[RetrievalResult]:
        """
        Perform hybrid search with RRF merge.
        
        Args:
            query: Search query string
            top_k: Number of results to return
            
        Returns:
            List of RetrievalResult objects, merged and ranked by RRF
        """
        # Perform parallel searches
        # We fetch more results than top_k to ensure good coverage after merge
        fetch_k = max(top_k * 2, 50)
        
        semantic_results = self.semantic_retrieval.search(query, top_k=fetch_k)
        fulltext_results = self.fulltext_retrieval.search(query, top_k=fetch_k)
        
        logger.debug(
            f"Hybrid search: semantic={len(semantic_results)}, "
            f"fulltext={len(fulltext_results)}"
        )
        
        # Merge using RRF
        merged_results = self._rrf_merge(semantic_results, fulltext_results, top_k)
        
        logger.debug(f"RRF merge returned {len(merged_results)} results")
        return merged_results
    
    def _rrf_merge(
        self,
        semantic_results: List[RetrievalResult],
        fulltext_results: List[RetrievalResult],
        top_k: int,
    ) -> List[RetrievalResult]:
        """
        Merge results using Reciprocal Rank Fusion (RRF).
        
        RRF score = sum(1 / (k + rank)) for each result list
        
        Args:
            semantic_results: Results from semantic search
            fulltext_results: Results from full-text search
            top_k: Number of final results to return
            
        Returns:
            Merged and ranked list of RetrievalResult objects
        """
        # Create a map of chunk_id -> result for deduplication
        result_map: Dict[str, RetrievalResult] = {}
        rrf_scores: Dict[str, float] = defaultdict(float)
        
        # Process semantic results
        for rank, result in enumerate(semantic_results, start=1):
            chunk_id = result.chunk_id or result.content[:50]  # Fallback ID
            rrf_score = 1.0 / (self.rrf_k + rank)
            rrf_scores[chunk_id] += rrf_score
            
            if chunk_id not in result_map:
                result_map[chunk_id] = result
        
        # Process full-text results
        for rank, result in enumerate(fulltext_results, start=1):
            chunk_id = result.chunk_id or result.content[:50]  # Fallback ID
            rrf_score = 1.0 / (self.rrf_k + rank)
            rrf_scores[chunk_id] += rrf_score
            
            if chunk_id not in result_map:
                result_map[chunk_id] = result
        
        # Sort by RRF score
        sorted_chunk_ids = sorted(
            rrf_scores.keys(),
            key=lambda cid: rrf_scores[cid],
            reverse=True,
        )
        
        # Build result list with score filtering
        final_results = []
        for chunk_id in sorted_chunk_ids:
            score = rrf_scores[chunk_id]
            
            # Apply minimum score threshold
            if self.min_score is not None and score < self.min_score:
                continue
            
            result = result_map[chunk_id]
            result.score = score
            final_results.append(result)
            
            if len(final_results) >= top_k:
                break
        
        return final_results
