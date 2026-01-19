#!/usr/bin/env python3
"""
KLayout MCP Server (klayout_mcp)
Model Context Protocol server for KLayout API

This server exposes 2000+ KLayout APIs through 7 meta-tools:
- search_klayout_api: Search APIs by keyword
- describe_klayout_api: Get detailed API documentation  
- call_klayout_api: Execute API calls
- klayout_manage_handles: Manage object handles
- search_klayout_docs: Search general documentation
- klayout_test_import: Test KLayout availability
- klayout_get_status: Get server status information
"""

import sys
from pathlib import Path
from typing import Optional, Dict, Any

from mcp.server import FastMCP

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models import (
    SearchAPIInput, DescribeAPIInput, CallAPIInput,
    ManageHandlesInput, SearchDocsInput,
    ResponseFormat, OperationType, HandleAction,
    PaginationInfo
)
from src.formatters import ResponseFormatter, ErrorHelper
from src.index.api_index import APIIndex
from src.docs.document_store import DocumentStore
from src.invoker.handle_registry import HandleRegistry
from src.invoker.api_invoker import APIInvoker
from src.invoker.klayout_compat import get_klayout_compat
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

# Create MCP server instance with Python naming convention
mcp = FastMCP(name="klayout_mcp")

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
@mcp.tool(
    name="search_klayout_api",
    annotations={
        "title": "Search KLayout APIs",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
def search_klayout_api(params: SearchAPIInput) -> Dict[str, Any]:
    """
    Search KLayout APIs by keyword. Find classes and methods matching your query.
    
    Use this tool to discover available KLayout APIs. Supports filtering by module
    (db, lay, tl, rdb) and type (class, method). Returns paginated results with
    relevance scores.
    
    Examples:
        - Search for box-related APIs: query="Box"
        - Find geometry methods: query="area", search_type="method"  
        - Search in database module: query="polygon", module="db"
    """
    _init_components()
    
    if not _api_index or not _api_index.is_loaded():
        return ErrorHelper.index_not_loaded()
    
    # Convert enum values to strings for the underlying tool
    module_str = params.module.value if params.module else None
    type_str = params.search_type.value if params.search_type else None
    
    # Perform search with extended limit to calculate total
    # Get more results than needed to determine total
    all_results = _search_api.search(
        query=params.query,
        module=module_str,
        search_type=type_str,
        limit=1000  # Get all results for pagination info
    )
    
    if not all_results.get("success", False):
        return all_results
    
    all_items = all_results.get("results", [])
    total = len(all_items)
    
    # Apply pagination
    paginated_items = all_items[params.offset:params.offset + params.limit]
    
    # Create pagination info
    pagination = PaginationInfo(
        total=total,
        count=len(paginated_items),
        offset=params.offset,
        limit=params.limit,
        has_more=(params.offset + params.limit) < total,
        next_offset=params.offset + params.limit if (params.offset + params.limit) < total else None
    )
    
    # Add suggestions if no results
    suggestions = None
    if not paginated_items:
        suggestions = [
            f"Try a broader search term",
            f"Remove filters (module/search_type)",
            f"Check spelling of '{params.query}'"
        ]
    
    # Format response based on requested format
    result = ResponseFormatter.format_search_results(
        results=paginated_items,
        query=params.query,
        filters={"module": module_str, "type": type_str},
        pagination=pagination,
        format=params.response_format
    )
    
    if suggestions:
        result["suggestions"] = suggestions
    
    return result


# ============================================================================
# MCP Tool 2: describe_klayout_api
# ============================================================================
@mcp.tool(
    name="describe_klayout_api",
    annotations={
        "title": "Describe KLayout API",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
def describe_klayout_api(params: DescribeAPIInput) -> Dict[str, Any]:
    """
    Get detailed documentation for a KLayout API class or method.
    
    Retrieves comprehensive documentation including description, constructors,
    methods, parameters, return types, and code examples. Use after searching
    to get full details about a specific API.
    
    Examples:
        - Describe Box class: class_name="Box"
        - Describe specific method: class_name="Box", method_name="area"
        - Get examples: class_name="Layout", include_examples=True
    """
    _init_components()
    
    if _describe_api is None:
        return ErrorHelper.documentation_not_available()
    
    if params.method_name:
        # Describe specific method
        result = _describe_api.describe_method(params.class_name, params.method_name)
        
        if not result.get("success", False):
            # Check if class exists
            class_data = _api_index.get_class(params.class_name) if _api_index else None
            if not class_data:
                return ErrorHelper.class_not_found(params.class_name)
            return ErrorHelper.method_not_found(params.class_name, params.method_name)
        
        return ResponseFormatter.format_method_description(
            result, params.class_name, params.response_format
        )
    else:
        # Describe entire class
        result = _describe_api.describe_class(
            params.class_name, 
            include_examples=params.include_examples
        )
        
        if not result.get("success", False):
            return ErrorHelper.class_not_found(params.class_name)
        
        return ResponseFormatter.format_class_description(result, params.response_format)


# ============================================================================
# MCP Tool 3: call_klayout_api
# ============================================================================
@mcp.tool(
    name="call_klayout_api",
    annotations={
        "title": "Call KLayout API",
        "readOnlyHint": False,
        "destructiveHint": True,
        "idempotentHint": False,
        "openWorldHint": False
    }
)
def call_klayout_api(params: CallAPIInput) -> Dict[str, Any]:
    """
    Execute a KLayout API call dynamically.
    
    Supports three operation types:
    - constructor: Create a new object (returns a handle)
    - method: Call an instance method on an existing object (requires handle)
    - static: Call a static class method
    
    Handles are automatically managed and can be used in subsequent calls.
    Use klayout_manage_handles to list, alias, or release handles.
    
    Examples:
        # Create a Box
        operation="constructor", class_name="Box", 
        params={"left": 0, "bottom": 0, "right": 100, "top": 100}
        
        # Call method on Box (using handle from above)
        operation="method", class_name="Box", method_name="area",
        handle="box_abc123"
    """
    _init_components()
    
    # Check KLayout availability
    compat = get_klayout_compat()
    if not compat.is_available:
        return ErrorHelper.klayout_not_available()
    
    # Validate operation-specific requirements
    operation = params.operation.value
    
    if operation in ("method", "static") and not params.method_name:
        return ErrorHelper.missing_parameter("method_name", operation)
    
    if operation == "method" and not params.handle:
        return ErrorHelper.missing_parameter("handle", operation)
    
    # Execute the call
    result = _call_api.call(
        operation=operation,
        class_name=params.class_name,
        method_name=params.method_name,
        handle=params.handle,
        params=params.params
    )
    
    # Enhance error messages
    if not result.get("success", False):
        error_msg = result.get("error", "")
        
        if "not found" in error_msg.lower():
            if "class" in error_msg.lower():
                return ErrorHelper.class_not_found(params.class_name)
            elif "method" in error_msg.lower():
                return ErrorHelper.method_not_found(params.class_name, params.method_name or "")
            elif "handle" in error_msg.lower():
                return ErrorHelper.handle_not_found(params.handle or "")
        
        if "blocked" in error_msg.lower():
            return ErrorHelper.api_blocked(params.class_name, params.method_name or "__init__")
        
        # Return original error with suggestions
        result["suggestion"] = "Check parameter types and values. Use describe_klayout_api to see method signatures."
    
    return result


# ============================================================================
# MCP Tool 4: klayout_manage_handles (renamed from manage_handles)
# ============================================================================
@mcp.tool(
    name="klayout_manage_handles",
    annotations={
        "title": "Manage KLayout Handles",
        "readOnlyHint": False,  # Can modify (release handles)
        "destructiveHint": True,  # release_all is destructive
        "idempotentHint": False,
        "openWorldHint": False
    }
)
def klayout_manage_handles(params: ManageHandlesInput) -> Dict[str, Any]:
    """
    Manage KLayout object handles created by call_klayout_api.
    
    Handles are references to KLayout objects that persist between API calls.
    Use this tool to:
    - list: See all active handles
    - get: Get details about a specific handle
    - release: Free a handle (object may be garbage collected)
    - release_all: Free all handles
    - alias: Assign a friendly name to a handle
    
    Examples:
        - List all handles: action="list"
        - List Box handles only: action="list", filter_type="Box"
        - Release a handle: action="release", handle="box_abc123"
        - Set alias: action="alias", handle="box_abc123", alias="my_box"
    """
    _init_components()
    
    action = params.action.value
    
    # Validate action-specific requirements
    if action in ("get", "release", "alias") and not params.handle:
        return {
            "success": False,
            "error": f"Handle ID required for '{action}' action",
            "error_code": "MISSING_HANDLE",
            "suggestion": "Use action='list' to see available handles"
        }
    
    if action == "alias" and not params.alias:
        return {
            "success": False,
            "error": "Alias name required for 'alias' action",
            "error_code": "MISSING_ALIAS",
            "suggestion": "Provide an alias name (e.g., alias='my_box')"
        }
    
    # Execute action
    result = _manage_handles.manage(
        action=action,
        handle=params.handle,
        alias=params.alias,
        filter_type=params.filter_type
    )
    
    # Format list results
    if action == "list" and result.get("success"):
        return ResponseFormatter.format_handles_list(
            handles=result.get("handles", []),
            filter_type=params.filter_type,
            format=params.response_format
        )
    
    # Enhance error for handle not found
    if not result.get("success") and "not found" in result.get("error", "").lower():
        return ErrorHelper.handle_not_found(params.handle or "")
    
    return result


# ============================================================================
# MCP Tool 5: search_klayout_docs
# ============================================================================
@mcp.tool(
    name="search_klayout_docs",
    annotations={
        "title": "Search KLayout Documentation",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
def search_klayout_docs(params: SearchDocsInput) -> Dict[str, Any]:
    """
    Search KLayout general documentation and tutorials.
    
    Search through KLayout's documentation including guides, tutorials,
    and reference materials. Supports searching by topic or keyword.
    
    Available topics: transformations, expressions, drc_ref, lvs_ref,
    layer_mapping, packages, programming, ruby, python
    
    Examples:
        - Search all docs: query="coordinate transformation"
        - Get topic overview: query="", topic="transformations"
        - Search within topic: query="rotation", topic="transformations"
    """
    _init_components()
    
    if _search_docs is None:
        return ErrorHelper.documentation_not_available()
    
    # Handle different search modes
    if params.topic and not params.query:
        result = _search_docs.get_topic(params.topic)
    elif params.topic:
        result = _search_docs.search_topic(params.topic, params.query)
    else:
        if not params.query:
            return {
                "success": False,
                "error": "Either query or topic must be provided",
                "error_code": "MISSING_QUERY",
                "suggestion": "Provide a search query or specify a topic"
            }
        result = _search_docs.search(params.query, limit=params.limit)
    
    if not result.get("success", False):
        return result
    
    return ResponseFormatter.format_docs_results(
        results=result.get("results", []),
        query=params.query,
        topic=params.topic,
        format=params.response_format
    )


# ============================================================================
# MCP Tool 6: klayout_test_import
# ============================================================================
@mcp.tool(
    name="klayout_test_import",
    annotations={
        "title": "Test KLayout Import",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
def klayout_test_import() -> Dict[str, Any]:
    """
    Test if KLayout module is properly imported and available.
    
    Verifies KLayout availability and reports which mode is active:
    - 'pya': Running inside KLayout GUI
    - 'standalone': Using klayout Python package
    - 'unavailable': KLayout not found
    
    Use this tool to diagnose KLayout installation issues.
    """
    compat = get_klayout_compat()
    
    if not compat.is_available:
        return {
            "success": False,
            "mode": "unavailable",
            "error": "KLayout modules not available",
            "suggestion": "Install KLayout: pip install klayout (standalone) or run from KLayout GUI",
            "troubleshooting": [
                "For standalone: pip install klayout",
                "For GUI mode: Run this script from KLayout's macro editor",
                "Check Python version compatibility (Python 3.8+)"
            ]
        }
    
    try:
        # Test by creating a simple object
        Box = compat.get_class('Box', 'db')
        if Box is None:
            return {
                "success": False,
                "mode": compat.mode,
                "error": "Box class not found",
                "suggestion": "KLayout installation may be incomplete"
            }
        
        box = Box(0, 0, 10, 10)
        
        return {
            "success": True,
            "mode": compat.mode,
            "message": f"KLayout imported successfully in {compat.mode} mode",
            "test_result": f"Created test Box: {box}",
            "available_modules": compat.get_status().get("modules_loaded", [])
        }
    except Exception as e:
        return {
            "success": False,
            "mode": compat.mode,
            "error": f"Error using KLayout: {str(e)}",
            "suggestion": "Check KLayout installation and Python environment"
        }


# ============================================================================
# MCP Tool 7: klayout_get_status
# ============================================================================
@mcp.tool(
    name="klayout_get_status",
    annotations={
        "title": "Get KLayout Server Status",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
def klayout_get_status() -> Dict[str, Any]:
    """
    Get comprehensive KLayout MCP server status information.
    
    Returns:
    - KLayout availability and mode
    - API index statistics (total classes, methods)
    - Documentation availability
    - Active handle count
    - Server health information
    """
    _init_components()
    
    compat = get_klayout_compat()
    
    result = {
        "success": True,
        "server_name": "klayout_mcp",
        "klayout": {
            "available": compat.is_available,
            "mode": compat.mode,
            "modules_loaded": compat.get_status().get("modules_loaded", [])
        },
        "index": {
            "loaded": _api_index.is_loaded() if _api_index else False,
        },
        "documentation": {
            "available": _doc_store is not None
        },
        "handles": _registry.get_stats() if _registry else {"total": 0}
    }
    
    # Add API statistics if index is loaded
    if _api_index and _api_index.is_loaded():
        stats = _api_index.get_stats()
        result["index"]["stats"] = {
            "total_classes": stats.get("total_classes", 0),
            "total_methods": stats.get("total_methods", 0),
            "total_modules": stats.get("total_modules", 0),
            "version": stats.get("version", "unknown")
        }
    
    # Health check
    result["health"] = {
        "status": "healthy" if (compat.is_available and 
                                _api_index and _api_index.is_loaded()) else "degraded",
        "issues": []
    }
    
    if not compat.is_available:
        result["health"]["issues"].append("KLayout modules not available")
    if not _api_index or not _api_index.is_loaded():
        result["health"]["issues"].append("API index not loaded")
    if not _doc_store:
        result["health"]["issues"].append("Documentation not available")
    
    return result


# ============================================================================
# Backward compatibility aliases (deprecated)
# ============================================================================
@mcp.tool(
    name="manage_handles",
    annotations={
        "title": "Manage Handles (Deprecated)",
        "readOnlyHint": False,
        "destructiveHint": True,
        "idempotentHint": False,
        "openWorldHint": False
    }
)
def manage_handles_deprecated(params: ManageHandlesInput) -> Dict[str, Any]:
    """
    [DEPRECATED] Use klayout_manage_handles instead.
    
    This tool is deprecated and will be removed in a future version.
    Please use klayout_manage_handles for handle management.
    """
    result = klayout_manage_handles(params)
    result["_deprecation_warning"] = "This tool is deprecated. Use 'klayout_manage_handles' instead."
    return result


@mcp.tool(
    name="test_klayout_import",
    annotations={
        "title": "Test Import (Deprecated)",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
def test_klayout_import_deprecated() -> Dict[str, Any]:
    """
    [DEPRECATED] Use klayout_test_import instead.
    """
    result = klayout_test_import()
    result["_deprecation_warning"] = "This tool is deprecated. Use 'klayout_test_import' instead."
    return result


@mcp.tool(
    name="get_klayout_version",
    annotations={
        "title": "Get Version (Deprecated)",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
def get_klayout_version_deprecated() -> Dict[str, Any]:
    """
    [DEPRECATED] Use klayout_get_status instead.
    """
    result = klayout_get_status()
    result["_deprecation_warning"] = "This tool is deprecated. Use 'klayout_get_status' instead."
    return result


# ============================================================================
# Main entry point
# ============================================================================
if __name__ == "__main__":
    # Run MCP server with stdio transport
    mcp.run(transport='stdio')
