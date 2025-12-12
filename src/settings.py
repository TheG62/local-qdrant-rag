"""Settings configuration for Local Qdrant RAG Agent."""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class QdrantSettings:
    """Qdrant configuration settings."""
    url: str = "http://localhost:6333"
    collection_name: str = "chunks"
    
    @classmethod
    def from_env(cls) -> "QdrantSettings":
        """Load Qdrant settings from environment variables."""
        return cls(
            url=os.getenv("QDRANT_URL", "http://localhost:6333"),
            collection_name=os.getenv("QDRANT_COLLECTION_NAME", "chunks"),
        )


@dataclass
class OllamaSettings:
    """Ollama LLM configuration settings."""
    base_url: str = "http://localhost:11434"
    model: str = "qwen2.5:32b"
    
    @classmethod
    def from_env(cls) -> "OllamaSettings":
        """Load Ollama settings from environment variables."""
        return cls(
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            model=os.getenv("OLLAMA_MODEL", "qwen2.5:32b"),
        )


@dataclass
class EmbeddingSettings:
    """Embedding model configuration settings."""
    model: str = "BAAI/bge-m3"
    dimension: int = 1024  # Critical: Must match model dimension
    
    @classmethod
    def from_env(cls) -> "EmbeddingSettings":
        """Load embedding settings from environment variables."""
        dimension_str = os.getenv("EMBEDDING_DIMENSION", "1024")
        try:
            dimension = int(dimension_str)
        except ValueError:
            raise ValueError(
                f"EMBEDDING_DIMENSION must be an integer, got: {dimension_str}"
            )
        return cls(
            model=os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3"),
            dimension=dimension,
        )


@dataclass
class ChunkingSettings:
    """Chunking configuration settings."""
    chunk_size: int = 1000
    chunk_overlap: int = 200
    
    @classmethod
    def from_env(cls) -> "ChunkingSettings":
        """Load chunking settings from environment variables."""
        return cls(
            chunk_size=int(os.getenv("CHUNK_SIZE", "1000")),
            chunk_overlap=int(os.getenv("CHUNK_OVERLAP", "200")),
        )


@dataclass
class RetrievalSettings:
    """Retrieval configuration settings."""
    top_k: int = 10
    rrf_k: int = 60
    min_score: float = 0.01  # Minimum relevance score threshold
    strategy: str = "hybrid_rrf"  # pure_semantic, pure_fulltext, hybrid_rrf
    
    @classmethod
    def from_env(cls) -> "RetrievalSettings":
        """Load retrieval settings from environment variables."""
        return cls(
            top_k=int(os.getenv("TOP_K", "10")),
            rrf_k=int(os.getenv("RRF_K", "60")),
            min_score=float(os.getenv("MIN_SCORE", "0.01")),
            strategy=os.getenv("RETRIEVAL_STRATEGY", "hybrid_rrf"),
        )


@dataclass
class Settings:
    """Main settings class combining all configuration."""
    qdrant: QdrantSettings
    ollama: OllamaSettings
    embedding: EmbeddingSettings
    chunking: ChunkingSettings
    retrieval: RetrievalSettings
    
    @classmethod
    def from_env(cls) -> "Settings":
        """Load all settings from environment variables."""
        return cls(
            qdrant=QdrantSettings.from_env(),
            ollama=OllamaSettings.from_env(),
            embedding=EmbeddingSettings.from_env(),
            chunking=ChunkingSettings.from_env(),
            retrieval=RetrievalSettings.from_env(),
        )
    
    def get_embedding_dimension(self) -> int:
        """Get embedding dimension - critical for Qdrant collection creation."""
        return self.embedding.dimension


# Global settings instance
settings = Settings.from_env()

