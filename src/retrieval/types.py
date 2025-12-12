"""Retrieval result types."""

from dataclasses import dataclass
from typing import Dict, Any, Optional


@dataclass
class RetrievalResult:
    """Result from a retrieval query."""
    
    content: str
    source: Optional[str] = None
    doc_id: Optional[str] = None
    chunk_id: Optional[str] = None
    page: Optional[int] = None
    score: float = 0.0
    metadata: Optional[Dict[str, Any]] = None

