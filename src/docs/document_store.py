"""
Document Store - On-demand loading of API documentation with LRU cache

This module provides lazy loading and caching of KLayout documentation
to avoid loading all docs into memory at once.
"""

import re
from pathlib import Path
from typing import Dict, List, Optional, Any
from functools import lru_cache
from dataclasses import dataclass
import threading


@dataclass
class SearchMatch:
    """Represents a search match in documentation."""
    file_path: str
    class_name: str
    section: str
    snippet: str
    line_number: int
    score: float


class DocumentStore:
    """
    Provides on-demand loading and caching of API documentation.
    
    Uses LRU cache to keep frequently accessed docs in memory
    while avoiding loading all documentation at once.
    """
    
    def __init__(self, docs_root: str, cache_size: int = 50):
        """
        Initialize the DocumentStore.
        
        Args:
            docs_root: Root directory containing markdown documentation
            cache_size: Maximum number of documents to keep in cache
        """
        self.docs_root = Path(docs_root)
        self.code_path = self.docs_root / "code"
        self.about_path = self.docs_root / "about"
        self.cache_size = cache_size
        self._cache: Dict[str, str] = {}
        self._cache_order: List[str] = []
        self._lock = threading.Lock()
        
        # Build file index for fast lookup
        self._file_index: Dict[str, Path] = {}
        self._build_file_index()
    
    def _build_file_index(self) -> None:
        """Build an index of class names to file paths."""
        if self.code_path.exists():
            for md_file in self.code_path.glob("*.md"):
                # Extract class name from filename
                class_name = md_file.stem
                if class_name.startswith("class_"):
                    class_name = class_name[6:]
                class_name = class_name.replace("++", "::")
                self._file_index[class_name] = md_file
        
        # Also index about docs
        if self.about_path.exists():
            for md_file in self.about_path.glob("*.md"):
                topic_name = md_file.stem
                self._file_index[f"about:{topic_name}"] = md_file
    
    def get_class_doc(self, class_name: str) -> Optional[str]:
        """
        Get the full documentation for a class.
        
        Args:
            class_name: Name of the class
            
        Returns:
            Full markdown documentation or None if not found
        """
        cache_key = f"class:{class_name}"
        
        # Check cache first
        with self._lock:
            if cache_key in self._cache:
                # Move to end of cache order (most recently used)
                self._cache_order.remove(cache_key)
                self._cache_order.append(cache_key)
                return self._cache[cache_key]
        
        # Find the file
        file_path = self._file_index.get(class_name)
        if not file_path:
            # Try with class_ prefix
            for name, path in self._file_index.items():
                if name.lower() == class_name.lower():
                    file_path = path
                    break
        
        if not file_path or not file_path.exists():
            return None
        
        # Load and cache
        try:
            content = file_path.read_text(encoding='utf-8')
            self._add_to_cache(cache_key, content)
            return content
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            return None
    
    def get_topic_doc(self, topic_name: str) -> Optional[str]:
        """
        Get documentation for a special topic (from about/ directory).
        
        Args:
            topic_name: Name of the topic (e.g., "transformations", "expressions")
            
        Returns:
            Full markdown documentation or None if not found
        """
        cache_key = f"about:{topic_name}"
        
        # Check cache first
        with self._lock:
            if cache_key in self._cache:
                self._cache_order.remove(cache_key)
                self._cache_order.append(cache_key)
                return self._cache[cache_key]
        
        # Find the file
        file_path = self._file_index.get(cache_key)
        if not file_path:
            # Try direct path
            file_path = self.about_path / f"{topic_name}.md"
        
        if not file_path or not file_path.exists():
            return None
        
        try:
            content = file_path.read_text(encoding='utf-8')
            self._add_to_cache(cache_key, content)
            return content
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            return None
    
    def get_method_doc(self, class_name: str, method_name: str) -> Optional[str]:
        """
        Get documentation for a specific method.
        
        Args:
            class_name: Name of the class
            method_name: Name of the method
            
        Returns:
            Method documentation or None if not found
        """
        class_doc = self.get_class_doc(class_name)
        if not class_doc:
            return None
        
        # Find the method section in Detailed description
        # Method headers are like: ### method_name
        pattern = rf'###\s+{re.escape(method_name)}\s*(.*?)(?=###\s+\w|$)'
        match = re.search(pattern, class_doc, re.DOTALL)
        
        if match:
            return f"### {method_name}\n{match.group(1).strip()}"
        
        return None
    
    def _add_to_cache(self, key: str, content: str) -> None:
        """Add content to cache with LRU eviction."""
        with self._lock:
            # Remove oldest if cache is full
            while len(self._cache) >= self.cache_size:
                oldest_key = self._cache_order.pop(0)
                del self._cache[oldest_key]
            
            self._cache[key] = content
            self._cache_order.append(key)
    
    def search_content(self, query: str, doc_type: str = "all", 
                       limit: int = 10) -> List[SearchMatch]:
        """
        Search for content within documentation.
        
        Args:
            query: Search query string
            doc_type: Type of docs to search ("class", "topic", "all")
            limit: Maximum number of results
            
        Returns:
            List of SearchMatch objects
        """
        results: List[SearchMatch] = []
        query_lower = query.lower()
        
        # Determine which files to search
        files_to_search: List[tuple] = []
        
        if doc_type in ("class", "all"):
            for class_name, file_path in self._file_index.items():
                if not class_name.startswith("about:"):
                    files_to_search.append((class_name, file_path, "class"))
        
        if doc_type in ("topic", "all"):
            for class_name, file_path in self._file_index.items():
                if class_name.startswith("about:"):
                    topic = class_name[6:]
                    files_to_search.append((topic, file_path, "topic"))
        
        # Search through files (limit scanning for performance)
        for name, file_path, dtype in files_to_search[:500]:  # Limit files scanned
            if len(results) >= limit * 3:  # Get more than needed for scoring
                break
            
            try:
                content = file_path.read_text(encoding='utf-8')
                content_lower = content.lower()
                
                if query_lower in content_lower:
                    # Find the match position and extract snippet
                    pos = content_lower.find(query_lower)
                    start = max(0, pos - 50)
                    end = min(len(content), pos + len(query) + 100)
                    snippet = content[start:end].strip()
                    
                    # Count matches for scoring
                    match_count = content_lower.count(query_lower)
                    
                    results.append(SearchMatch(
                        file_path=str(file_path),
                        class_name=name,
                        section=dtype,
                        snippet=f"...{snippet}...",
                        line_number=content[:pos].count('\n') + 1,
                        score=match_count
                    ))
            except Exception:
                continue
        
        # Sort by score and limit
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:limit]
    
    def list_topics(self) -> List[str]:
        """
        List all available topics from the about/ directory.
        
        Returns:
            List of topic names
        """
        topics = []
        for key in self._file_index:
            if key.startswith("about:"):
                topics.append(key[6:])
        return sorted(topics)
    
    def list_classes(self) -> List[str]:
        """
        List all available class names.
        
        Returns:
            List of class names
        """
        classes = []
        for key in self._file_index:
            if not key.startswith("about:"):
                classes.append(key)
        return sorted(classes)
    
    def clear_cache(self) -> None:
        """Clear the document cache."""
        with self._lock:
            self._cache.clear()
            self._cache_order.clear()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        with self._lock:
            return {
                "cache_size": len(self._cache),
                "max_size": self.cache_size,
                "cached_docs": list(self._cache.keys())
            }
