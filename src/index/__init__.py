"""
Index module for KLayout API indexing and search.

This module provides:
- IndexBuilder: Parse markdown docs and build API index
- APIIndex: Search and lookup APIs from the index
"""

from .index_builder import IndexBuilder, APIClass, APIMethod
from .api_index import APIIndex, SearchResult

__all__ = [
    "IndexBuilder",
    "APIClass", 
    "APIMethod",
    "APIIndex",
    "SearchResult",
]
