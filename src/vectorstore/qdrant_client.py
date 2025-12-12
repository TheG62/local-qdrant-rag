"""Qdrant client factory with health checks and connection management."""

import logging
from typing import Optional
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
from qdrant_client.http import models

from ..settings import settings

logger = logging.getLogger(__name__)


def get_qdrant_client() -> QdrantClient:
    """
    Create and return a Qdrant client instance.
    
    Returns:
        QdrantClient: Configured Qdrant client
        
    Raises:
        ConnectionError: If Qdrant is not reachable
    """
    client = QdrantClient(url=settings.qdrant.url)
    
    # Health check
    try:
        health = client.get_collections()
        logger.info(f"Connected to Qdrant at {settings.qdrant.url}")
        return client
    except Exception as e:
        raise ConnectionError(
            f"Failed to connect to Qdrant at {settings.qdrant.url}. "
            f"Make sure Qdrant is running (docker compose up -d). Error: {e}"
        ) from e


def ensure_collection_exists(
    client: Optional[QdrantClient] = None,
    collection_name: Optional[str] = None,
    vector_size: Optional[int] = None,
) -> None:
    """
    Ensure the Qdrant collection exists with proper schema.
    
    Args:
        client: Qdrant client instance (creates new if None)
        collection_name: Collection name (uses settings default if None)
        vector_size: Vector dimension (uses settings default if None)
    """
    if client is None:
        client = get_qdrant_client()
    
    if collection_name is None:
        collection_name = settings.qdrant.collection_name
    
    if vector_size is None:
        vector_size = settings.get_embedding_dimension()
    
    # Check if collection exists
    collections = client.get_collections().collections
    collection_exists = any(c.name == collection_name for c in collections)
    
    if not collection_exists:
        logger.info(f"Creating collection '{collection_name}' with vector size {vector_size}")
        from .schema import create_collection_schema
        create_collection_schema(client, collection_name, vector_size)
    else:
        logger.debug(f"Collection '{collection_name}' already exists")

