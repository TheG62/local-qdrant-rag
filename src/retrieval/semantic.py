"""Pure semantic (vector) retrieval strategy."""

import logging
from typing import List, Optional

from .base import RetrievalStrategy
from .types import RetrievalResult
from ..vectorstore import get_qdrant_client
from ..ingestion import get_embedder
from ..settings import settings

logger = logging.getLogger(__name__)


class PureSemanticRetrieval(RetrievalStrategy):
    """Pure semantic retrieval using vector similarity search."""
    
    def __init__(self, min_score: Optional[float] = None):
        """
        Initialize semantic retrieval.
        
        Args:
            min_score: Minimum score threshold (filters low-relevance results)
        """
        self.client = get_qdrant_client()
        self.embedder = get_embedder()  # Cached singleton
        self.collection_name = settings.qdrant.collection_name
        self.min_score = min_score
    
    def search(self, query: str, top_k: int = 10) -> List[RetrievalResult]:
        """
        Search using vector similarity.
        
        Args:
            query: Search query string
            top_k: Number of results to return
            
        Returns:
            List of RetrievalResult objects
        """
        # Generate query embedding (uses cached model)
        query_embedding = self.embedder.embed(query)
        
        # Perform vector search using query_points (correct Qdrant API)
        search_results = self.client.query_points(
            collection_name=self.collection_name,
            query=query_embedding,
            limit=top_k,
            with_payload=True,
            with_vectors=False,
        )
        
        # Convert to RetrievalResult objects
        retrieval_results = []
        for result in search_results.points:
            # Get score from result (Qdrant returns score in result.score)
            score = getattr(result, 'score', 0.0)
            
            # Apply score threshold if set
            if self.min_score is not None and score < self.min_score:
                continue
                
            payload = result.payload or {}
            retrieval_results.append(
                RetrievalResult(
                    content=payload.get("content", ""),
                    source=payload.get("source"),
                    doc_id=payload.get("doc_id"),
                    chunk_id=payload.get("chunk_id"),
                    page=payload.get("page"),
                    score=score,
                    metadata=payload,
                )
            )
        
        logger.debug(f"Semantic search returned {len(retrieval_results)} results")
        return retrieval_results
