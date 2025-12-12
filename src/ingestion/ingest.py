"""Main ingestion pipeline with Docling integration.

This pipeline uses Docling for document processing and structure-aware chunking:
1. DocumentConverter: Parse documents (PDF, Word, Excel, etc.)
2. HybridChunker: Structure-aware chunking
3. Embedder: Generate embeddings with bge-m3
4. Qdrant: Store vectors and metadata
"""

import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
from qdrant_client.models import PointStruct

from .chunker import Chunker
from .embedder import Embedder, get_embedder
from ..vectorstore import get_qdrant_client, ensure_collection_exists
from ..settings import settings

logger = logging.getLogger(__name__)


def get_document_converter():
    """Get Docling DocumentConverter."""
    try:
        from docling.document_converter import DocumentConverter
        return DocumentConverter()
    except ImportError:
        raise ImportError(
            "Docling is required. Install with: pip install docling"
        )


def ingest_documents(
    documents: List[Dict[str, Any]],
    batch_size: int = 100,
) -> Dict[str, int]:
    """
    Ingest pre-processed documents into Qdrant.
    
    Args:
        documents: List of document dicts with 'content' and 'metadata'
        batch_size: Number of chunks to process in each batch
        
    Returns:
        Dict with 'processed' and 'failed' counts
    """
    client = get_qdrant_client()
    ensure_collection_exists(client)
    
    chunker = Chunker()
    embedder = get_embedder()  # Cached singleton
    
    # Process all documents into chunks
    all_chunks = []
    for doc in documents:
        chunks = chunker.chunk_document(doc)
        all_chunks.extend(chunks)
    
    logger.info(f"Processing {len(all_chunks)} chunks from {len(documents)} documents")
    
    return _upsert_chunks(client, embedder, all_chunks, batch_size)


def ingest_with_docling(
    file_paths: List[str],
    batch_size: int = 100,
) -> Dict[str, int]:
    """
    Ingest documents using Docling's full pipeline.
    
    This is the recommended method - uses Docling's structure-aware
    chunking for better retrieval quality.
    
    Args:
        file_paths: List of file paths to process
        batch_size: Batch size for embedding/upsert
        
    Returns:
        Dict with 'processed' and 'failed' counts
    """
    client = get_qdrant_client()
    ensure_collection_exists(client)
    
    converter = get_document_converter()
    chunker = Chunker(use_docling=True)
    embedder = get_embedder()
    
    all_chunks = []
    failed_files = 0
    
    for file_path in file_paths:
        try:
            logger.info(f"Processing: {file_path}")
            result = converter.convert(file_path)
            
            # Use Docling's structure-aware chunking
            chunks = chunker.chunk_docling_document(result)
            all_chunks.extend(chunks)
            
            logger.info(f"  → {len(chunks)} chunks extracted")
            
        except Exception as e:
            logger.error(f"Failed to process {file_path}: {e}")
            failed_files += 1
    
    if not all_chunks:
        logger.warning("No chunks to ingest")
        return {"processed": 0, "failed": failed_files}
    
    logger.info(f"Total: {len(all_chunks)} chunks from {len(file_paths) - failed_files} documents")
    
    result = _upsert_chunks(client, embedder, all_chunks, batch_size)
    result["failed_files"] = failed_files
    return result


def ingest_directory(
    directory: str,
    recursive: bool = False,
    batch_size: int = 100,
) -> Dict[str, int]:
    """
    Ingest all documents from a directory using Docling.
    
    Args:
        directory: Directory path
        recursive: Whether to search recursively
        batch_size: Batch size for processing
        
    Returns:
        Dict with 'processed' and 'failed' counts
    """
    from .document_loader import DOCLING_EXTENSIONS
    
    path = Path(directory)
    if not path.exists():
        raise FileNotFoundError(f"Directory not found: {directory}")
    
    pattern = "**/*" if recursive else "*"
    
    file_paths = [
        str(f) for f in path.glob(pattern)
        if f.is_file() and f.suffix.lower() in DOCLING_EXTENSIONS
    ]
    
    if not file_paths:
        logger.warning(f"No supported documents found in {directory}")
        logger.info(f"Supported formats: {DOCLING_EXTENSIONS}")
        return {"processed": 0, "failed": 0}
    
    logger.info(f"Found {len(file_paths)} documents in {directory}")
    
    return ingest_with_docling(file_paths, batch_size)


def ingest_file(file_path: str, batch_size: int = 100) -> Dict[str, int]:
    """
    Ingest a single document file using Docling.
    
    Args:
        file_path: Path to document file
        batch_size: Batch size for processing
        
    Returns:
        Dict with 'processed' and 'failed' counts
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    return ingest_with_docling([file_path], batch_size)


def _upsert_chunks(
    client,
    embedder: Embedder,
    chunks: List[Dict[str, Any]],
    batch_size: int,
) -> Dict[str, int]:
    """
    Generate embeddings and upsert chunks to Qdrant.
    
    Args:
        client: Qdrant client
        embedder: Embedder instance
        chunks: List of chunk dicts
        batch_size: Batch size for processing
        
    Returns:
        Dict with 'processed' and 'failed' counts
    """
    processed = 0
    failed = 0
    
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        
        try:
            # Generate embeddings
            texts = [chunk["content"] for chunk in batch]
            embeddings = embedder.embed(texts)
            
            # Prepare points for Qdrant
            points = []
            for idx, chunk in enumerate(batch):
                # Create stable ID from chunk_id
                chunk_id = chunk["metadata"].get("chunk_id", f"chunk_{i + idx}")
                point_id = abs(hash(chunk_id)) % (2**63)  # Positive int64
                
                point = PointStruct(
                    id=point_id,
                    vector=embeddings[idx],
                    payload={
                        "content": chunk["content"],
                        **chunk["metadata"],
                    },
                )
                points.append(point)
            
            # Upsert to Qdrant
            client.upsert(
                collection_name=settings.qdrant.collection_name,
                points=points,
            )
            
            processed += len(batch)
            logger.debug(f"Processed batch {i // batch_size + 1}: {len(batch)} chunks")
            
        except Exception as e:
            logger.error(f"Error processing batch {i // batch_size + 1}: {e}")
            failed += len(batch)
    
    logger.info(f"Ingestion complete: {processed} processed, {failed} failed")
    return {"processed": processed, "failed": failed}
