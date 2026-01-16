"""
API Index - Search and lookup APIs by name/keyword

This module provides fast API lookup and search functionality
using the pre-built index from IndexBuilder.
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass


@dataclass
class SearchResult:
    """Represents a search result."""
    name: str
    type: str  # "class" or "method"
    module: str
    description: str
    score: float
    class_name: Optional[str] = None  # For method results
    signature: Optional[str] = None   # For method results


class APIIndex:
    """
    Provides fast API lookup and search functionality.
    
    Uses the pre-built JSON index for efficient searching without
    loading all documentation into memory.
    """
    
    def __init__(self, index_path: Optional[str] = None):
        """
        Initialize the APIIndex.
        
        Args:
            index_path: Path to the JSON index file. If None, index must be loaded later.
        """
        self._index: Dict[str, Any] = {}
        self._classes: Dict[str, Any] = {}
        self._modules: Dict[str, List[str]] = {}
        self._keyword_index: Dict[str, List[str]] = {}
        self._loaded = False
        
        if index_path:
            self.load_index(index_path)
    
    def load_index(self, index_path: str) -> None:
        """
        Load the API index from a JSON file.
        
        Args:
            index_path: Path to the JSON index file
        """
        path = Path(index_path)
        if not path.exists():
            raise FileNotFoundError(f"Index file not found: {index_path}")
        
        with open(path, 'r', encoding='utf-8') as f:
            self._index = json.load(f)
        
        self._classes = self._index.get("classes", {})
        self._modules = self._index.get("modules", {})
        self._keyword_index = self._index.get("keyword_index", {})
        self._loaded = True
    
    def is_loaded(self) -> bool:
        """Check if the index is loaded."""
        return self._loaded
    
    def search(self, query: str, module: Optional[str] = None, 
               search_type: Optional[str] = None, limit: int = 10) -> List[SearchResult]:
        """
        Search for APIs matching the query.
        
        Args:
            query: Search query string
            module: Filter by module (db, lay, tl, etc.)
            search_type: Filter by type ("class" or "method")
            limit: Maximum number of results to return
            
        Returns:
            List of SearchResult objects sorted by relevance
        """
        if not self._loaded:
            raise RuntimeError("Index not loaded. Call load_index() first.")
        
        results: List[SearchResult] = []
        query_lower = query.lower()
        query_parts = set(re.findall(r'\w+', query_lower))
        
        # Search classes
        if search_type is None or search_type == "class":
            results.extend(self._search_classes(query_lower, query_parts, module))
        
        # Search methods
        if search_type is None or search_type == "method":
            results.extend(self._search_methods(query_lower, query_parts, module))
        
        # Sort by score (descending) and limit
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:limit]
    
    def _search_classes(self, query_lower: str, query_parts: set, 
                        module: Optional[str]) -> List[SearchResult]:
        """Search for matching classes."""
        results = []
        
        for class_name, class_data in self._classes.items():
            # Filter by module if specified
            if module and class_data.get("module") != module:
                continue
            
            score = self._calculate_class_score(class_name, class_data, 
                                                query_lower, query_parts)
            if score > 0:
                results.append(SearchResult(
                    name=class_name,
                    type="class",
                    module=class_data.get("module", "unknown"),
                    description=class_data.get("description", "")[:200],
                    score=score
                ))
        
        return results
    
    def _search_methods(self, query_lower: str, query_parts: set,
                        module: Optional[str]) -> List[SearchResult]:
        """Search for matching methods."""
        results = []
        
        for class_name, class_data in self._classes.items():
            # Filter by module if specified
            if module and class_data.get("module") != module:
                continue
            
            # Search in all method categories
            all_methods = (
                class_data.get("methods", []) +
                class_data.get("constructors", []) +
                class_data.get("static_methods", [])
            )
            
            for method in all_methods:
                method_name = method.get("name", "")
                score = self._calculate_method_score(method_name, method,
                                                    query_lower, query_parts)
                if score > 0:
                    results.append(SearchResult(
                        name=method_name,
                        type="method",
                        module=class_data.get("module", "unknown"),
                        description=method.get("description", "")[:200],
                        score=score,
                        class_name=class_name,
                        signature=method.get("signature", "")
                    ))
        
        return results
    
    def _calculate_class_score(self, class_name: str, class_data: Dict,
                               query_lower: str, query_parts: set) -> float:
        """Calculate relevance score for a class."""
        score = 0.0
        class_name_lower = class_name.lower()
        
        # Exact match - highest score
        if class_name_lower == query_lower:
            score += 10.0
        # Starts with query
        elif class_name_lower.startswith(query_lower):
            score += 5.0
        # Contains query
        elif query_lower in class_name_lower:
            score += 3.0
        
        # Check keywords
        keywords = class_data.get("keywords", [])
        for keyword in keywords:
            if keyword.lower() in query_parts:
                score += 1.0
        
        # Check description
        description = class_data.get("description", "").lower()
        for part in query_parts:
            if part in description:
                score += 0.5
        
        return score
    
    def _calculate_method_score(self, method_name: str, method_data: Dict,
                                query_lower: str, query_parts: set) -> float:
        """Calculate relevance score for a method."""
        score = 0.0
        method_name_lower = method_name.lower()
        
        # Exact match
        if method_name_lower == query_lower:
            score += 8.0
        # Starts with query
        elif method_name_lower.startswith(query_lower):
            score += 4.0
        # Contains query
        elif query_lower in method_name_lower:
            score += 2.0
        
        # Check description
        description = method_data.get("description", "").lower()
        for part in query_parts:
            if part in description:
                score += 0.3
        
        return score
    
    def get_class(self, class_name: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a class.
        
        Args:
            class_name: Name of the class
            
        Returns:
            Dictionary containing class information or None if not found
        """
        if not self._loaded:
            raise RuntimeError("Index not loaded. Call load_index() first.")
        
        return self._classes.get(class_name)
    
    def get_method(self, class_name: str, method_name: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific method.
        
        Args:
            class_name: Name of the class
            method_name: Name of the method
            
        Returns:
            Dictionary containing method information or None if not found
        """
        if not self._loaded:
            raise RuntimeError("Index not loaded. Call load_index() first.")
        
        class_data = self._classes.get(class_name)
        if not class_data:
            return None
        
        # Search in all method categories
        all_methods = (
            class_data.get("methods", []) +
            class_data.get("constructors", []) +
            class_data.get("static_methods", []) +
            class_data.get("deprecated_methods", [])
        )
        
        for method in all_methods:
            if method.get("name") == method_name:
                return method
        
        return None
    
    def list_modules(self) -> List[str]:
        """
        Get list of all available modules.
        
        Returns:
            List of module names
        """
        if not self._loaded:
            raise RuntimeError("Index not loaded. Call load_index() first.")
        
        return list(self._modules.keys())
    
    def list_classes(self, module: Optional[str] = None) -> List[str]:
        """
        List all classes, optionally filtered by module.
        
        Args:
            module: Optional module name to filter by
            
        Returns:
            List of class names
        """
        if not self._loaded:
            raise RuntimeError("Index not loaded. Call load_index() first.")
        
        if module:
            return self._modules.get(module, [])
        
        return list(self._classes.keys())
    
    def get_class_methods(self, class_name: str) -> Dict[str, List[Dict]]:
        """
        Get all methods of a class organized by category.
        
        Args:
            class_name: Name of the class
            
        Returns:
            Dictionary with keys: constructors, methods, static_methods, deprecated_methods
        """
        if not self._loaded:
            raise RuntimeError("Index not loaded. Call load_index() first.")
        
        class_data = self._classes.get(class_name)
        if not class_data:
            return {}
        
        return {
            "constructors": class_data.get("constructors", []),
            "methods": class_data.get("methods", []),
            "static_methods": class_data.get("static_methods", []),
            "deprecated_methods": class_data.get("deprecated_methods", [])
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the loaded index.
        
        Returns:
            Dictionary containing index statistics
        """
        if not self._loaded:
            return {"loaded": False}
        
        total_methods = 0
        for class_data in self._classes.values():
            total_methods += len(class_data.get("methods", []))
            total_methods += len(class_data.get("constructors", []))
            total_methods += len(class_data.get("static_methods", []))
        
        return {
            "loaded": True,
            "version": self._index.get("version", "unknown"),
            "total_classes": len(self._classes),
            "total_modules": len(self._modules),
            "total_methods": total_methods,
            "total_keywords": len(self._keyword_index)
        }
