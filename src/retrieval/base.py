"""Base retrieval strategy interface."""

from abc import ABC, abstractmethod
from typing import List
from .types import RetrievalResult


class RetrievalStrategy(ABC):
    """Base class for retrieval strategies."""
    
    @abstractmethod
    def search(self, query: str, top_k: int = 10) -> List[RetrievalResult]:
        """
        Search for relevant documents.
        
        Args:
            query: Search query string
            top_k: Number of results to return
            
        Returns:
            List of RetrievalResult objects
        """
        pass

