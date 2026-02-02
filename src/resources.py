"""
MCP Resources for KLayout MCP Server

This module provides MCP Resources for efficient access to KLayout
documentation and API information via URI templates.
"""

import json
from typing import Optional
from pathlib import Path

# Global references to be set by server
_api_index = None
_doc_store = None
_registry = None


def set_resources(api_index, doc_store, registry):
    """Set global resource references from server."""
    global _api_index, _doc_store, _registry
    _api_index = api_index
    _doc_store = doc_store
    _registry = registry


def get_class_documentation(class_name: str) -> str:
    """
    Get full documentation for a KLayout class.
    
    URI: klayout://docs/{class_name}
    
    Args:
        class_name: Name of the KLayout class
        
    Returns:
        Markdown formatted documentation
    """
    if _doc_store is None:
        return f"# Error\n\nDocumentation not available for '{class_name}'."
    
    doc = _doc_store.get_class_doc(class_name)
    if not doc:
        return f"# Class Not Found\n\nNo documentation found for class '{class_name}'."
    
    return doc


def get_method_documentation(class_name: str, method_name: str) -> str:
    """
    Get documentation for a specific method.
    
    URI: klayout://docs/{class_name}/{method_name}
    
    Args:
        class_name: Name of the KLayout class
        method_name: Name of the method
        
    Returns:
        Markdown formatted documentation
    """
    if _doc_store is None:
        return f"# Error\n\nDocumentation not available."
    
    doc = _doc_store.get_method_doc(class_name, method_name)
    if not doc:
        return f"# Method Not Found\n\nNo documentation found for '{class_name}.{method_name}'."
    
    return doc


def list_all_classes() -> str:
    """
    List all available KLayout API classes.
    
    URI: klayout://api/classes
    
    Returns:
        JSON list of class names
    """
    if _api_index is None or not _api_index.is_loaded():
        return json.dumps({"error": "API index not loaded"}, indent=2)
    
    classes = _api_index.list_classes()
    return json.dumps({
        "total": len(classes),
        "classes": sorted(classes)
    }, indent=2)


def list_modules() -> str:
    """
    List all available KLayout modules.
    
    URI: klayout://api/modules
    
    Returns:
        JSON list of module names
    """
    if _api_index is None or not _api_index.is_loaded():
        return json.dumps({"error": "API index not loaded"}, indent=2)
    
    modules = _api_index.list_modules()
    return json.dumps({
        "total": len(modules),
        "modules": sorted(modules)
    }, indent=2)


def list_module_classes(module_name: str) -> str:
    """
    List classes in a specific module.
    
    URI: klayout://api/modules/{module_name}/classes
    
    Args:
        module_name: Module name (db, lay, tl, rdb, pex)
        
    Returns:
        JSON list of class names
    """
    if _api_index is None or not _api_index.is_loaded():
        return json.dumps({"error": "API index not loaded"}, indent=2)
    
    classes = _api_index.list_classes(module=module_name)
    return json.dumps({
        "module": module_name,
        "total": len(classes),
        "classes": sorted(classes)
    }, indent=2)


def get_server_status() -> str:
    """
    Get KLayout MCP server status.
    
    URI: klayout://status
    
    Returns:
        JSON status information
    """
    from .invoker.klayout_compat import get_klayout_compat
    
    compat = get_klayout_compat()
    
    status = {
        "server_name": "klayout_mcp",
        "klayout": {
            "available": compat.is_available,
            "mode": compat.mode,
            "modules_loaded": compat.get_status().get("modules_loaded", [])
        },
        "index": {
            "loaded": _api_index.is_loaded() if _api_index else False,
            "stats": _api_index.get_stats() if _api_index and _api_index.is_loaded() else None
        },
        "documentation": {
            "available": _doc_store is not None
        },
        "handles": _registry.get_stats() if _registry else {"total": 0}
    }
    
    return json.dumps(status, indent=2)
