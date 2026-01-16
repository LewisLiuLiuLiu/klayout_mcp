"""
Search API Tool - Search KLayout APIs by keyword

This tool provides API search functionality for the MCP server.
"""

from typing import Optional, List, Dict, Any

from ..index.api_index import APIIndex, SearchResult


class SearchAPITool:
    """
    Tool for searching KLayout APIs.
    
    Searches classes and methods by keyword, with optional
    filtering by module and type.
    """
    
    def __init__(self, api_index: APIIndex):
        """
        Initialize the tool.
        
        Args:
            api_index: Loaded APIIndex instance
        """
        self.api_index = api_index
    
    def search(self, query: str, 
               module: Optional[str] = None,
               search_type: Optional[str] = None,
               limit: int = 10) -> Dict[str, Any]:
        """
        Search for KLayout APIs.
        
        Args:
            query: Search query string
            module: Filter by module (db, lay, tl, etc.)
            search_type: Filter by type ("class" or "method")
            limit: Maximum number of results
            
        Returns:
            Dictionary with search results
        """
        if not self.api_index.is_loaded():
            return {
                "success": False,
                "error": "API index not loaded"
            }
        
        # Perform search
        results = self.api_index.search(
            query=query,
            module=module,
            search_type=search_type,
            limit=limit
        )
        
        # Format results
        formatted_results = []
        for result in results:
            item = {
                "type": result.type,
                "name": result.name,
                "module": result.module,
                "description": result.description,
                "relevance_score": round(result.score, 2)
            }
            
            if result.type == "method" and result.class_name:
                item["class"] = result.class_name
                item["signature"] = result.signature
            
            formatted_results.append(item)
        
        return {
            "success": True,
            "query": query,
            "filters": {
                "module": module,
                "type": search_type
            },
            "results": formatted_results,
            "total": len(formatted_results)
        }
    
    def list_modules(self) -> Dict[str, Any]:
        """
        List all available modules.
        
        Returns:
            Dictionary with module list
        """
        if not self.api_index.is_loaded():
            return {
                "success": False,
                "error": "API index not loaded"
            }
        
        modules = self.api_index.list_modules()
        return {
            "success": True,
            "modules": modules,
            "total": len(modules)
        }
    
    def list_classes(self, module: Optional[str] = None) -> Dict[str, Any]:
        """
        List classes, optionally filtered by module.
        
        Args:
            module: Optional module filter
            
        Returns:
            Dictionary with class list
        """
        if not self.api_index.is_loaded():
            return {
                "success": False,
                "error": "API index not loaded"
            }
        
        classes = self.api_index.list_classes(module)
        return {
            "success": True,
            "module": module,
            "classes": classes,
            "total": len(classes)
        }
