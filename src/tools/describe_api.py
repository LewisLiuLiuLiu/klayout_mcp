"""
Describe API Tool - Get detailed API documentation

This tool provides detailed API documentation for the MCP server.
"""

from typing import Optional, Dict, Any

from ..index.api_index import APIIndex
from ..docs.document_store import DocumentStore
from ..docs.doc_chunker import DocChunker


class DescribeAPITool:
    """
    Tool for getting detailed API documentation.
    
    Provides class descriptions, method signatures, and examples.
    """
    
    def __init__(self, api_index: APIIndex, doc_store: DocumentStore):
        """
        Initialize the tool.
        
        Args:
            api_index: Loaded APIIndex instance
            doc_store: DocumentStore instance
        """
        self.api_index = api_index
        self.doc_store = doc_store
        self.chunker = DocChunker()
    
    def describe_class(self, class_name: str,
                       include_methods: bool = True,
                       include_examples: bool = False) -> Dict[str, Any]:
        """
        Get detailed documentation for a class.
        
        Args:
            class_name: Name of the class
            include_methods: Include method list
            include_examples: Include code examples
            
        Returns:
            Dictionary with class documentation
        """
        # Get class info from index
        class_info = self.api_index.get_class(class_name)
        if not class_info:
            return {
                "success": False,
                "error": f"Class not found: {class_name}"
            }
        
        result = {
            "success": True,
            "class": {
                "name": class_name,
                "module": class_info.get("module", "unknown"),
                "description": class_info.get("description", ""),
                "hierarchy": class_info.get("hierarchy", []),
            }
        }
        
        if include_methods:
            result["class"]["constructors"] = [
                {"name": m["name"], "signature": m["signature"], "description": m["description"]}
                for m in class_info.get("constructors", [])
            ]
            result["class"]["methods"] = [
                {"name": m["name"], "signature": m["signature"], "description": m["description"]}
                for m in class_info.get("methods", [])[:50]  # Limit to 50 methods
            ]
            result["class"]["static_methods"] = [
                {"name": m["name"], "signature": m["signature"], "description": m["description"]}
                for m in class_info.get("static_methods", [])
            ]
            result["class"]["method_count"] = (
                len(class_info.get("methods", [])) +
                len(class_info.get("constructors", [])) +
                len(class_info.get("static_methods", []))
            )
        
        if include_examples:
            # Load full documentation and extract examples
            full_doc = self.doc_store.get_class_doc(class_name)
            if full_doc:
                examples = self.chunker.extract_examples(full_doc)
                result["examples"] = [
                    {"title": ex.title, "code": ex.code, "language": ex.language}
                    for ex in examples[:5]  # Limit to 5 examples
                ]
        
        return result
    
    def describe_method(self, class_name: str, method_name: str) -> Dict[str, Any]:
        """
        Get detailed documentation for a specific method.
        
        Args:
            class_name: Name of the class
            method_name: Name of the method
            
        Returns:
            Dictionary with method documentation
        """
        # Get method info from index
        method_info = self.api_index.get_method(class_name, method_name)
        if not method_info:
            return {
                "success": False,
                "error": f"Method not found: {class_name}.{method_name}"
            }
        
        result = {
            "success": True,
            "method": {
                "name": method_name,
                "class": class_name,
                "signature": method_info.get("signature", ""),
                "return_type": method_info.get("return_type", ""),
                "description": method_info.get("description", ""),
                "is_static": method_info.get("is_static", False),
                "is_const": method_info.get("is_const", False),
                "parameters": method_info.get("parameters", [])
            }
        }
        
        # Get detailed documentation from doc store
        detailed_doc = self.doc_store.get_method_doc(class_name, method_name)
        if detailed_doc:
            result["documentation"] = detailed_doc
        
        return result
    
    def get_class_doc(self, class_name: str) -> Dict[str, Any]:
        """
        Get the full markdown documentation for a class.
        
        Args:
            class_name: Name of the class
            
        Returns:
            Dictionary with full documentation
        """
        doc = self.doc_store.get_class_doc(class_name)
        if not doc:
            return {
                "success": False,
                "error": f"Documentation not found for: {class_name}"
            }
        
        return {
            "success": True,
            "class_name": class_name,
            "documentation": doc
        }
