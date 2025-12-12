"""Document loader using Docling for comprehensive document processing.

Docling (IBM) provides advanced document understanding including:
- Complex PDF layouts with tables and multi-column text
- OCR for scanned documents
- Structure-aware parsing for Office documents
- Markdown/HTML with semantic structure preservation
"""

import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

# Supported extensions by Docling
DOCLING_EXTENSIONS = {
    ".pdf", ".docx", ".pptx", ".xlsx", 
    ".html", ".htm", ".md", ".txt",
    ".png", ".jpg", ".jpeg", ".tiff", ".bmp"  # Images with OCR
}


def get_document_converter():
    """
    Get Docling DocumentConverter instance.
    
    Returns:
        DocumentConverter instance
    """
    try:
        from docling.document_converter import DocumentConverter
        return DocumentConverter()
    except ImportError:
        raise ImportError(
            "Docling is required for document processing. "
            "Install with: pip install docling"
        )


def load_document(file_path: str) -> Optional[Dict[str, Any]]:
    """
    Load a single document using Docling.
    
    Docling handles: PDF, Word, PowerPoint, Excel, HTML, Markdown, Images (OCR)
    
    Args:
        file_path: Path to the document file
        
    Returns:
        Document dict with 'content' and 'metadata', or None if failed
    """
    path = Path(file_path)
    suffix = path.suffix.lower()
    
    if suffix not in DOCLING_EXTENSIONS:
        logger.warning(f"Unsupported file type: {suffix}. Supported: {DOCLING_EXTENSIONS}")
        return None
    
    try:
        converter = get_document_converter()
        
        logger.info(f"Processing document with Docling: {file_path}")
        result = converter.convert(file_path)
        
        # Extract text content as Markdown (preserves structure)
        content = result.document.export_to_markdown()
        
        if not content or not content.strip():
            logger.warning(f"No content extracted from {file_path}")
            return None
        
        # Build metadata
        metadata = {
            "source": str(file_path),
            "doc_id": path.stem,
            "type": suffix.lstrip("."),
            "created_at": datetime.now().isoformat(),
        }
        
        # Add Docling-specific metadata if available
        if hasattr(result.document, 'pages'):
            metadata["pages"] = len(result.document.pages)
        
        logger.info(f"Successfully processed {file_path}: {len(content)} chars")
        
        return {
            "content": content,
            "metadata": metadata,
        }
        
    except Exception as e:
        logger.error(f"Error processing document {file_path}: {e}")
        return None


def load_documents_from_directory(
    directory: str,
    recursive: bool = False,
    extensions: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """
    Load all supported documents from a directory using Docling.
    
    Args:
        directory: Directory path
        recursive: Whether to search recursively
        extensions: List of file extensions to include (None = all supported)
        
    Returns:
        List of document dicts
    """
    if extensions is None:
        extensions = list(DOCLING_EXTENSIONS)
    else:
        # Normalize extensions
        extensions = [ext if ext.startswith(".") else f".{ext}" for ext in extensions]
    
    path = Path(directory)
    if not path.exists():
        raise FileNotFoundError(f"Directory not found: {directory}")
    
    documents = []
    pattern = "**/*" if recursive else "*"
    
    # Collect all matching files
    files_to_process = [
        f for f in path.glob(pattern) 
        if f.is_file() and f.suffix.lower() in extensions
    ]
    
    logger.info(f"Found {len(files_to_process)} documents to process in {directory}")
    
    for file_path in files_to_process:
        doc = load_document(str(file_path))
        if doc:
            documents.append(doc)
    
    logger.info(f"Successfully loaded {len(documents)} documents from {directory}")
    return documents


def load_documents_batch(file_paths: List[str]) -> List[Dict[str, Any]]:
    """
    Load multiple documents by file paths.
    
    Args:
        file_paths: List of file paths to process
        
    Returns:
        List of document dicts
    """
    documents = []
    
    for file_path in file_paths:
        doc = load_document(file_path)
        if doc:
            documents.append(doc)
    
    return documents
