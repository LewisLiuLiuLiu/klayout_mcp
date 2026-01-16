"""
Documentation module for KLayout API documentation handling.

This module provides:
- DocumentStore: On-demand loading of documentation with LRU cache
- DocChunker: Split documentation into semantic chunks
"""

from .document_store import DocumentStore, SearchMatch
from .doc_chunker import DocChunker, DocChunk, CodeExample

__all__ = [
    "DocumentStore",
    "SearchMatch",
    "DocChunker",
    "DocChunk",
    "CodeExample",
]
