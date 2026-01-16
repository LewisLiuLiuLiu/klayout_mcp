#!/usr/bin/env python3
"""
KLayout MCP Server
Model Context Protocol server for KLayout API

This server exposes 2000+ KLayout APIs through 5 meta-tools:
- search_klayout_api: Search APIs by keyword
- describe_klayout_api: Get detailed API documentation
- call_klayout_api: Execute API calls
- manage_handles: Manage object handles
- search_klayout_docs: Search general documentation
"""

import sys
import os
from pathlib import Path
from typing import Optional, Dict, Any, List

from mcp.server import FastMCP

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.index.api_index import APIIndex
from src.docs.document_store import DocumentStore
from src.invoker.handle_registry import HandleRegistry
from src.invoker.api_invoker import APIInvoker
from src.security.sandbox import Sandbox
from src.tools.search_api import SearchAPITool
from src.tools.describe_api import DescribeAPITool
from src.tools.call_api import CallAPITool
from src.tools.manage_handles import ManageHandlesTool
from src.tools.search_docs import SearchDocsTool

# Configuration
PROJECT_ROOT = Path(__file__).parent.parent
INDEX_PATH = PROJECT_ROOT / "data" / "api_index.json"
DOCS_PATH = PROJECT_ROOT / "klayout-doc" / "markdown_docs"

# Create MCP server instance
mcp = FastMCP(name="klayout-mcp-server")

# Initialize components (lazy loading)
_api_index: Optional[APIIndex] = None
_doc_store: Optional[DocumentStore] = None
_registry: Optional[HandleRegistry] = None
_invoker: Optional[APIInvoker] = None
_sandbox: Optional[Sandbox] = None

# Tool instances
_search_api: Optional[SearchAPITool] = None
_describe_api: Optional[DescribeAPITool] = None
_call_api: Optional[CallAPITool] = None
_manage_handles: Optional[ManageHandlesTool] = None
_search_docs: Optional[SearchDocsTool] = None


def _init_components():
    """Initialize all components on first use."""
    global _api_index, _doc_store, _registry, _invoker, _sandbox
    global _search_api, _describe_api, _call_api, _manage_handles, _search_docs
    
    if _api_index is None:
        # Initialize core components
        _api_index = APIIndex(str(INDEX_PATH)) if INDEX_PATH.exists() else APIIndex()
        _doc_store = DocumentStore(str(DOCS_PATH)) if DOCS_PATH.exists() else None
        _registry = HandleRegistry()
        _sandbox = Sandbox()
        _invoker = APIInvoker(_registry, _sandbox)
        
        # Initialize tools
        _search_api = SearchAPITool(_api_index)
        _describe_api = DescribeAPITool(_api_index, _doc_store) if _doc_store else None
        _call_api = CallAPITool(_invoker, _registry, _sandbox)
        _manage_handles = ManageHandlesTool(_registry)
        _search_docs = SearchDocsTool(_doc_store) if _doc_store else None


# ============================================================================
# MCP Tool 1: search_klayout_api
# ============================================================================
@mcp.tool()
def search_klayout_api(
    query: str,
    module: Optional[str] = None,
    search_type: Optional[str] = None,
    limit: int = 10
) -> Dict[str, Any]:
    """
    Search KLayout APIs by keyword.
    
    Args:
        query: Search query string (e.g., "Box", "area", "Layout")
        module: Filter by module (db, lay, tl, rdb). Optional.
        search_type: Filter by type ("class" or "method"). Optional.
        limit: Maximum number of results (default 10)
    
    Returns:
        Dictionary with search results including class/method names,
        descriptions, and relevance scores.
    
    Example:
        search_klayout_api(query="Box", module="db", limit=5)
    """
    _init_components()
    return _search_api.search(query, module, search_type, limit)


# ============================================================================
# MCP Tool 2: describe_klayout_api
# ============================================================================
@mcp.tool()
def describe_klayout_api(
    class_name: str,
    method_name: Optional[str] = None,
    include_examples: bool = False
) -> Dict[str, Any]:
    """
    Get detailed documentation for a KLayout API class or method.
    
    Args:
        class_name: Name of the class (e.g., "Box", "Layout", "Cell")
        method_name: Name of a specific method. Optional.
        include_examples: Include code examples in the response.
    
    Returns:
        Dictionary with detailed API documentation including:
        - Class description and module
        - Method signatures and descriptions
        - Parameter information
        - Code examples (if requested)
    
    Example:
        describe_klayout_api(class_name="Box", include_examples=True)
        describe_klayout_api(class_name="Box", method_name="area")
    """
    _init_components()
    if _describe_api is None:
        return {"success": False, "error": "Documentation not available"}
    
    if method_name:
        return _describe_api.describe_method(class_name, method_name)
    else:
        return _describe_api.describe_class(class_name, include_examples=include_examples)


# ============================================================================
# MCP Tool 3: call_klayout_api
# ============================================================================
@mcp.tool()
def call_klayout_api(
    operation: str,
    class_name: str,
    method_name: Optional[str] = None,
    handle: Optional[str] = None,
    params: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Execute a KLayout API call.
    
    Args:
        operation: Type of operation:
            - "constructor": Create a new object
            - "method": Call an instance method
            - "static": Call a static method
        class_name: Name of the class (e.g., "Box", "Layout")
        method_name: Method name (required for "method" and "static" operations)
        handle: Object handle ID (required for "method" operation)
        params: Parameters as key-value pairs. Optional.
    
    Returns:
        Dictionary with:
        - success: Boolean indicating success
        - handle: Handle ID for created objects
        - value: Return value for methods
        - execution_time_ms: Execution time in milliseconds
    
    Examples:
        # Create a Box
        call_klayout_api(
            operation="constructor",
            class_name="Box",
            params={"left": 0, "bottom": 0, "right": 100, "top": 100}
        )
        
        # Call area() method on the Box
        call_klayout_api(
            operation="method",
            class_name="Box",
            method_name="area",
            handle="box_abc123_1234567890"
        )
    """
    _init_components()
    return _call_api.call(operation, class_name, method_name, handle, params)


# ============================================================================
# MCP Tool 4: manage_handles
# ============================================================================
@mcp.tool()
def manage_handles(
    action: str,
    handle: Optional[str] = None,
    alias: Optional[str] = None,
    filter_type: Optional[str] = None
) -> Dict[str, Any]:
    """
    Manage KLayout object handles.
    
    Args:
        action: Action to perform:
            - "list": List all handles
            - "get": Get handle details
            - "release": Release a handle
            - "release_all": Release all handles
            - "alias": Set an alias for a handle
        handle: Handle ID (required for get/release/alias)
        alias: Alias name (required for "alias" action)
        filter_type: Filter by object type (for "list" action)
    
    Returns:
        Dictionary with action results.
    
    Examples:
        # List all handles
        manage_handles(action="list")
        
        # List only Box handles
        manage_handles(action="list", filter_type="Box")
        
        # Set an alias
        manage_handles(action="alias", handle="box_abc123", alias="my_box")
        
        # Release a handle
        manage_handles(action="release", handle="box_abc123")
    """
    _init_components()
    return _manage_handles.manage(action, handle, alias, filter_type)


# ============================================================================
# MCP Tool 5: search_klayout_docs
# ============================================================================
@mcp.tool()
def search_klayout_docs(
    query: str,
    topic: Optional[str] = None,
    limit: int = 5
) -> Dict[str, Any]:
    """
    Search KLayout general documentation and tutorials.
    
    Args:
        query: Search query string
        topic: Search within a specific topic. Optional.
               Available topics: transformations, expressions, drc_ref,
               lvs_ref, layer_mapping, packages, etc.
        limit: Maximum number of results (default 5)
    
    Returns:
        Dictionary with search results including snippets
        and relevance scores.
    
    Examples:
        # Search all documentation
        search_klayout_docs(query="coordinate transformation")
        
        # Get a specific topic
        search_klayout_docs(query="", topic="transformations")
        
        # Search within a topic
        search_klayout_docs(query="rotation", topic="transformations")
    """
    _init_components()
    if _search_docs is None:
        return {"success": False, "error": "Documentation not available"}
    
    if topic and not query:
        return _search_docs.get_topic(topic)
    elif topic:
        return _search_docs.search_topic(topic, query)
    else:
        return _search_docs.search(query, limit=limit)


# ============================================================================
# Utility tools (kept from original)
# ============================================================================
@mcp.tool()
def test_klayout_import() -> str:
    """Test if KLayout module is properly imported."""
    try:
        import klayout.db as db
        box = db.Box(0, 0, 10, 10)
        return f"KLayout imported successfully! Box: {box}"
    except Exception as e:
        return f"Error importing KLayout: {str(e)}"


@mcp.tool()
def get_klayout_version() -> Dict[str, Any]:
    """Get KLayout version and server status information."""
    _init_components()
    
    result = {
        "klayout_available": False,
        "index_loaded": _api_index.is_loaded() if _api_index else False,
        "docs_available": _doc_store is not None,
    }
    
    try:
        import klayout.db as db
        result["klayout_available"] = True
        result["klayout_module"] = "klayout.db loaded"
    except Exception as e:
        result["error"] = str(e)
    
    if _api_index and _api_index.is_loaded():
        stats = _api_index.get_stats()
        result["api_stats"] = {
            "total_classes": stats.get("total_classes", 0),
            "total_methods": stats.get("total_methods", 0),
            "total_modules": stats.get("total_modules", 0)
        }
    
    if _registry:
        result["handle_stats"] = _registry.get_stats()
    
    return result


# ============================================================================
# Main entry point
# ============================================================================
if __name__ == "__main__":
    # Run MCP server with stdio transport
    mcp.run(transport='stdio')
