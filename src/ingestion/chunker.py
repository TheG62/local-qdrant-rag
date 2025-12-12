"""Document chunking using Docling's HybridChunker.

Docling's HybridChunker provides structure-aware chunking that:
- Respects document structure (headings, paragraphs, tables)
- Preserves semantic boundaries
- Handles tables and lists as atomic units
- Provides better context than naive text splitting
"""

import logging
from typing import List, Dict, Any, Optional

from ..settings import settings

logger = logging.getLogger(__name__)


class Chunker:
    """
    Document chunker with Docling HybridChunker support.
    
    Falls back to simple text chunking if Docling is not available.
    """
    
    def __init__(
        self,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
        use_docling: bool = True,
    ):
        """
        Initialize chunker.
        
        Args:
            chunk_size: Maximum tokens per chunk (for Docling) or chars (for fallback)
            chunk_overlap: Overlap between chunks (only used in fallback mode)
            use_docling: Whether to try using Docling's HybridChunker
        """
        self.chunk_size = chunk_size or settings.chunking.chunk_size
        self.chunk_overlap = chunk_overlap or settings.chunking.chunk_overlap
        self.use_docling = use_docling
        self._docling_chunker = None
        
        if use_docling:
            self._init_docling_chunker()
    
    def _init_docling_chunker(self):
        """Initialize Docling's HybridChunker if available."""
        try:
            from docling.chunking import HybridChunker
            
            self._docling_chunker = HybridChunker(
                tokenizer="BAAI/bge-m3",  # Match our embedding model
                max_tokens=self.chunk_size,
                merge_peers=True,  # Merge small adjacent chunks
            )
            logger.info(f"Using Docling HybridChunker (max_tokens={self.chunk_size})")
            
        except ImportError:
            logger.warning("Docling not available, falling back to simple chunking")
            self._docling_chunker = None
        except Exception as e:
            logger.warning(f"Could not initialize Docling chunker: {e}")
            self._docling_chunker = None
    
    def chunk_document(self, document: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Chunk a document into smaller pieces.
        
        Args:
            document: Document dict with 'content' and 'metadata'
            
        Returns:
            List of chunk dicts with 'content' and 'metadata'
        """
        content = document.get("content", "")
        metadata = document.get("metadata", {}).copy()
        
        if not content.strip():
            logger.warning("Document has no content to chunk")
            return []
        
        # Use simple text chunking (Docling chunking happens at convert time)
        chunks = self._simple_chunk(content)
        
        # Add metadata to each chunk
        chunked_docs = []
        for idx, chunk_text in enumerate(chunks):
            chunk_metadata = metadata.copy()
            chunk_metadata["chunk_id"] = f"{metadata.get('doc_id', 'doc')}_{idx}"
            chunk_metadata["chunk_index"] = idx
            chunk_metadata["total_chunks"] = len(chunks)
            
            chunked_docs.append({
                "content": chunk_text,
                "metadata": chunk_metadata,
            })
        
        logger.debug(f"Chunked document into {len(chunked_docs)} chunks")
        return chunked_docs
    
    def chunk_docling_document(self, docling_result) -> List[Dict[str, Any]]:
        """
        Chunk a Docling document result using HybridChunker.
        
        This method should be used directly after Docling conversion
        for best results (structure-aware chunking).
        
        Args:
            docling_result: Result from DocumentConverter.convert()
            
        Returns:
            List of chunk dicts with 'content' and 'metadata'
        """
        if self._docling_chunker is None:
            # Fallback to simple chunking via export
            content = docling_result.document.export_to_markdown()
            return self.chunk_document({
                "content": content,
                "metadata": {"source": str(docling_result.input.file)},
            })
        
        try:
            chunks = list(self._docling_chunker.chunk(docling_result.document))
            
            chunked_docs = []
            source = str(docling_result.input.file) if hasattr(docling_result, 'input') else "unknown"
            doc_id = source.split("/")[-1].rsplit(".", 1)[0] if source else "doc"
            
            for idx, chunk in enumerate(chunks):
                chunk_metadata = {
                    "source": source,
                    "doc_id": doc_id,
                    "chunk_id": f"{doc_id}_{idx}",
                    "chunk_index": idx,
                    "total_chunks": len(chunks),
                }
                
                # Add heading context if available
                if hasattr(chunk, 'meta') and chunk.meta:
                    if hasattr(chunk.meta, 'headings') and chunk.meta.headings:
                        chunk_metadata["headings"] = chunk.meta.headings
                    if hasattr(chunk.meta, 'doc_items'):
                        chunk_metadata["doc_items"] = len(chunk.meta.doc_items)
                
                chunked_docs.append({
                    "content": chunk.text,
                    "metadata": chunk_metadata,
                })
            
            logger.info(f"Docling HybridChunker produced {len(chunked_docs)} chunks")
            return chunked_docs
            
        except Exception as e:
            logger.warning(f"Docling chunking failed, falling back to simple: {e}")
            content = docling_result.document.export_to_markdown()
            return self.chunk_document({
                "content": content,
                "metadata": {"source": str(docling_result.input.file)},
            })
    
    def _simple_chunk(self, text: str) -> List[str]:
        """
        Simple text chunking with overlap.
        
        Used as fallback when Docling chunking is not available.
        """
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + self.chunk_size
            chunk = text[start:end]
            
            # Try to break at paragraph or sentence boundary
            if end < len(text):
                # Look for paragraph break first
                para_break = chunk.rfind("\n\n")
                if para_break > self.chunk_size // 2:
                    chunk = chunk[:para_break]
                    end = start + para_break
                else:
                    # Look for sentence boundary
                    for sep in [". ", "! ", "? ", "\n"]:
                        last_sep = chunk.rfind(sep)
                        if last_sep > self.chunk_size // 2:
                            chunk = chunk[:last_sep + len(sep)]
                            end = start + last_sep + len(sep)
                            break
            
            chunk = chunk.strip()
            if chunk:
                chunks.append(chunk)
            
            # Move start with overlap
            if end >= len(text):
                break
            start = max(start + 1, end - self.chunk_overlap)
        
        return chunks
