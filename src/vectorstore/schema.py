"""Qdrant collection schema definition with Full-Text-Index support."""

import logging
from typing import Optional
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    CollectionStatus,
    PayloadSchemaType,
)

logger = logging.getLogger(__name__)


def create_collection_schema(
    client: QdrantClient,
    collection_name: str,
    vector_size: int,
) -> None:
    """
    Create a Qdrant collection with vector search and full-text index.
    
    Important: Qdrant Full-Text is not true BM25, but an inverted index
    with TF-based scoring. RRF-merge behavior may differ from true BM25.
    
    Args:
        client: Qdrant client instance
        collection_name: Name of the collection
        vector_size: Dimension of the embedding vectors (must match model)
    """
    from qdrant_client.http import models
    
    # Create collection with vector configuration
    client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(
            size=vector_size,
            distance=Distance.COSINE,
        ),
    )
    
    logger.info(f"Created collection '{collection_name}' with vector size {vector_size}")
    
    # Create full-text index on 'content' field (Qdrant v1.7+)
    # This enables full-text search capabilities
    try:
        client.create_payload_index(
            collection_name=collection_name,
            field_name="content",
            field_schema=models.PayloadSchemaType.TEXT,
        )
        logger.info(f"Created full-text index on 'content' field for collection '{collection_name}'")
    except Exception as e:
        logger.warning(
            f"Failed to create full-text index (may not be supported in this Qdrant version): {e}"
        )
        logger.info("Full-text search may not be available, but vector search will work")
    
    # Wait for collection to be ready
    import time
    max_wait = 30
    wait_time = 0
    while wait_time < max_wait:
        collection_info = client.get_collection(collection_name)
        if collection_info.status == CollectionStatus.GREEN:
            logger.info(f"Collection '{collection_name}' is ready")
            return
        time.sleep(1)
        wait_time += 1
    
    logger.warning(f"Collection '{collection_name}' may not be fully ready yet")


def get_collection_payload_schema() -> dict:
    """
    Return the expected payload schema for documents in the collection.
    
    Returns:
        dict: Payload schema definition
    """
    return {
        "content": "text",  # Full-text indexed
        "source": "keyword",  # Source file path
        "doc_id": "keyword",  # Document ID
        "chunk_id": "keyword",  # Chunk ID within document
        "page": "integer",  # Page number (if applicable)
        "title": "keyword",  # Document title
        "tags": "keyword[]",  # Tags array
        "created_at": "keyword",  # ISO timestamp
    }

