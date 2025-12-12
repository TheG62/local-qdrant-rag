"""Pure full-text retrieval strategy using Qdrant Full-Text-Index."""

import logging
import re
from typing import List, Optional
from qdrant_client.models import Filter, FieldCondition, MatchText

from .base import RetrievalStrategy
from .types import RetrievalResult
from ..vectorstore import get_qdrant_client
from ..settings import settings

logger = logging.getLogger(__name__)


class PureFullTextRetrieval(RetrievalStrategy):
    """
    Pure full-text retrieval using Qdrant Full-Text-Index.
    
    Note: Qdrant Full-Text is not true BM25, but an inverted index
    with TF-based scoring. Results may differ from true BM25.
    
    The MatchText filter performs tokenized text matching on the
    indexed field. Results are returned based on token overlap.
    """
    
    def __init__(self, min_score: Optional[float] = None):
        """
        Initialize full-text retrieval.
        
        Args:
            min_score: Minimum score threshold (filters low-relevance results)
        """
        self.client = get_qdrant_client()
        self.collection_name = settings.qdrant.collection_name
        self.min_score = min_score
    
    def search(self, query: str, top_k: int = 10) -> List[RetrievalResult]:
        """
        Search using full-text index.
        
        Args:
            query: Search query string
            top_k: Number of results to return
            
        Returns:
            List of RetrievalResult objects
        """
        # NOTE:
        # Qdrant's MatchText behaves like a strict token match on the provided text.
        # For multi-term queries this can be "AND-like" (all tokens must be present),
        # which is too strict for German inflections ("kurzer" vs "kurzen").
        # We therefore:
        #  1) tokenize the query
        #  2) perform a broad OR-style MatchText over tokens
        #  3) re-rank locally by token overlap

        q = (query or "").strip()
        # Tokenize: words/numbers/umlauts; ignore very short tokens
        query_tokens = [t.lower() for t in re.findall(r"[\wÄÖÜäöüß]+", q) if len(t) >= 3]
        if not query_tokens:
            return []

        # Broad match: OR across tokens
        filter_condition = Filter(
            should=[
                FieldCondition(key="content", match=MatchText(text=t))
                for t in query_tokens
            ]
        )
        
        # Scroll through matching results
        # Qdrant's full-text is filter-based, not scoring-based like BM25
        # Fetch more than top_k so local re-ranking can pick best overlap
        fetch_k = max(top_k * 20, top_k)
        results, _ = self.client.scroll(
            collection_name=self.collection_name,
            scroll_filter=filter_condition,
            limit=fetch_k,
            with_payload=True,
            with_vectors=False,
        )
        
        # Local re-ranking by token overlap on payload['content']
        scored = []
        for result in results:
            payload = result.payload or {}
            content = payload.get("content", "") or ""
            content_tokens = set(t.lower() for t in re.findall(r"[\wÄÖÜäöüß]+", content))
            overlap = len(set(query_tokens) & content_tokens)
            if overlap <= 0:
                continue

            # score in [0..1]
            score = overlap / max(len(set(query_tokens)), 1)
            if self.min_score is not None and score < self.min_score:
                continue

            scored.append((score, payload))

        scored.sort(key=lambda x: x[0], reverse=True)

        retrieval_results: List[RetrievalResult] = []
        for score, payload in scored[:top_k]:
            retrieval_results.append(
                RetrievalResult(
                    content=payload.get("content", ""),
                    source=payload.get("source"),
                    doc_id=payload.get("doc_id"),
                    chunk_id=payload.get("chunk_id"),
                    page=payload.get("page"),
                    score=float(score),
                    metadata=payload,
                )
            )
        
        logger.debug(f"Full-text search returned {len(retrieval_results)} results")
        return retrieval_results
