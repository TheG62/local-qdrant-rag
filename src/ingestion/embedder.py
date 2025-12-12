"""Embedding generation using sentence-transformers with caching."""

import logging
import torch
from typing import List, Union, Optional
from sentence_transformers import SentenceTransformer

from ..settings import settings

logger = logging.getLogger(__name__)

# Singleton-Cache für das Embedding-Modell
_embedder_instance: Optional["Embedder"] = None


def get_embedder() -> "Embedder":
    """
    Get cached Embedder instance (Singleton pattern).
    
    Avoids reloading the model (~3s) on every search.
    
    Returns:
        Cached Embedder instance
    """
    global _embedder_instance
    if _embedder_instance is None:
        _embedder_instance = Embedder()
    return _embedder_instance


def clear_embedder_cache() -> None:
    """Clear the cached Embedder instance (useful for testing)."""
    global _embedder_instance
    _embedder_instance = None


class Embedder:
    """Embedding generator using sentence-transformers."""
    
    def __init__(self, model_name: Optional[str] = None, device: Optional[str] = None):
        """
        Initialize embedder.
        
        Args:
            model_name: Model name (defaults to settings)
            device: Device to use ('cpu', 'cuda', 'mps'). Auto-detects if None.
        """
        self.model_name = model_name or settings.embedding.model
        
        # Auto-detect device
        if device is None:
            if torch.backends.mps.is_available():
                device = "mps"
            elif torch.cuda.is_available():
                device = "cuda"
            else:
                device = "cpu"
        
        self.device = device
        logger.info(f"Loading embedding model '{self.model_name}' on device '{self.device}'")
        
        self.model = SentenceTransformer(self.model_name, device=self.device)
        logger.info(f"Embedding model loaded. Dimension: {self.model.get_sentence_embedding_dimension()}")
    
    def embed(self, texts: Union[str, List[str]]) -> Union[List[float], List[List[float]]]:
        """
        Generate embeddings for text(s).
        
        Args:
            texts: Single text string or list of texts
            
        Returns:
            Single embedding vector or list of embedding vectors
        """
        is_single = isinstance(texts, str)
        if is_single:
            texts = [texts]
        
        embeddings = self.model.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=True,  # For cosine similarity
        )
        
        # Convert to list of lists
        embeddings = embeddings.tolist()
        
        if is_single:
            return embeddings[0]
        return embeddings
    
    def get_dimension(self) -> int:
        """Get the embedding dimension."""
        return self.model.get_sentence_embedding_dimension()
