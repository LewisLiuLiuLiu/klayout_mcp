#!/usr/bin/env python3
"""
KLayout MCP Server (klayout_mcp) - Async Version with Context Support
Model Context Protocol server for KLayout API

This server exposes 2000+ KLayout APIs through 7 meta-tools:
- search_klayout_api: Search APIs by keyword
- describe_klayout_api: Get detailed API documentation  
- call_klayout_api: Execute API calls
- klayout_manage_handles: Manage object handles
- search_klayout_docs: Search general documentation
- klayout_test_import: Test KLayout availability
- klayout_get_status: Get server status information

Features:
- Async/await support for non-blocking operations
- Context parameter for progress reporting and logging
- Structured output with automatic JSON Schema generation
"""

import asyncio
import sys
from pathlib import Path
from typing import Optional, Dict, Any, Union, Tuple
from contextlib import asynccontextmanager

from mcp.server import FastMCP
from mcp.server.fastmcp import Context

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models import (
    SearchAPIInput, DescribeAPIInput, CallAPIInput,
    ManageHandlesInput, SearchDocsInput,
    ResponseFormat, OperationType, HandleAction,
    PaginationInfo,
    # Response models for output schemas
    SearchAPIResponse, ClassDescriptionResponse, MethodDescriptionResponse,
    CallAPIResponse, ManageHandlesResponse, SearchDocsResponse,
    TestImportResponse, ServerStatusResponse
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
from src import resources as klayout_resources

# Configuration
def _find_data_path() -> Tuple[Path, Path]:
    """
    Find data paths - works both in development and after installation.
    
    Search order:
    1. Development: project_root/data/ and project_root/klayout-doc/
    2. Installed: package_dir/data/ and package_dir/klayout-doc/
    3. Installed (site-packages): site_packages/data/ and site_packages/klayout-doc/
    """
    # Start from current file location
    current_file = Path(__file__).resolve()
    
    # Try development layout first (src/server.py -> project_root)
    dev_root = current_file.parent.parent
    dev_index = dev_root / "data" / "api_index.json"
    dev_docs = dev_root / "klayout-doc" / "markdown_docs"
    
    if dev_index.exists() and dev_docs.exists():
        return dev_index, dev_docs
    
    # Try installed layout (site-packages/klayout_mcp/data/)
    # When installed, files are in the same directory as the package
    pkg_root = current_file.parent
    pkg_index = pkg_root / "data" / "api_index.json"
    pkg_docs = pkg_root / "klayout-doc" / "markdown_docs"
    
    if pkg_index.exists() or pkg_docs.exists():
        return pkg_index, pkg_docs
    
    # Try to find in site-packages root
    try:
        import site
        for site_path in site.getsitepackages():
            site_root = Path(site_path)
            site_index = site_root / "data" / "api_index.json"
            site_docs = site_root / "klayout-doc" / "markdown_docs"
            if site_index.exists() or site_docs.exists():
                return site_index, site_docs
    except Exception:
        pass
    
    # Fallback to development paths (will show warnings later if not found)
    return dev_index, dev_docs


INDEX_PATH, DOCS_PATH = _find_data_path()
PROJECT_ROOT = INDEX_PATH.parent.parent

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

# Lock for thread-safe initialization
_init_lock: Optional[asyncio.Lock] = None


async def _init_components_async() -> None:
    """Initialize all components on first use (async version)."""
    global _api_index, _doc_store, _registry, _invoker, _sandbox
    global _search_api, _describe_api, _call_api, _manage_handles, _search_docs
    global _init_lock
    
    # Create lock if not exists
    if _init_lock is None:
        _init_lock = asyncio.Lock()
    
    # Double-check with lock
    if _api_index is None:
        async with _init_lock:
            if _api_index is None:
                loop = asyncio.get_event_loop()
                
                # Initialize core components (potentially I/O bound)
                _api_index = await loop.run_in_executor(
                    None, 
                    lambda: APIIndex(str(INDEX_PATH)) if INDEX_PATH.exists() else APIIndex()
                )
                _doc_store = await loop.run_in_executor(
                    None,
                    lambda: DocumentStore(str(DOCS_PATH)) if DOCS_PATH.exists() else None
                )
                _registry = HandleRegistry()
                _sandbox = Sandbox()
                _invoker = APIInvoker(_registry, _sandbox)
                
                # Initialize tools
                _search_api = SearchAPITool(_api_index)
                _describe_api = DescribeAPITool(_api_index, _doc_store) if _doc_store else None
                _call_api = CallAPITool(_invoker, _registry, _sandbox)
                _manage_handles = ManageHandlesTool(_registry)
                _search_docs = SearchDocsTool(_doc_store) if _doc_store else None
                
                # Set resources references
                klayout_resources.set_resources(_api_index, _doc_store, _registry)


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
    },
    structured_output=True
)
async def search_klayout_api(params: SearchAPIInput, ctx: Context) -> SearchAPIResponse:
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
    await ctx.report_progress(0.1, "Initializing components...")
    await _init_components_async()
    
    if not _api_index or not _api_index.is_loaded():
        await ctx.report_progress(1.0, "Failed - index not loaded")
        return ErrorHelper.index_not_loaded()
    
    await ctx.report_progress(0.3, f"Searching for '{params.query}'...")
    
    # Convert enum values to strings for the underlying tool
    module_str = params.module.value if params.module else None
    type_str = params.search_type.value if params.search_type else None
    
    # Perform search with extended limit to calculate total
    loop = asyncio.get_event_loop()
    all_results = await loop.run_in_executor(
        None,
        lambda: _search_api.search(
            query=params.query,
            module=module_str,
            search_type=type_str,
            limit=1000  # Get all results for pagination info
        )
    )
    
    if not all_results.get("success", False):
        await ctx.report_progress(1.0, "Search failed")
        return all_results
    
    await ctx.report_progress(0.7, "Processing results...")
    
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
        await ctx.log_warning(f"No results found for query: {params.query}")
    
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
    
    await ctx.report_progress(1.0, f"Found {total} results")
    await ctx.log_info(f"Search completed", {"query": params.query, "total": total})
    
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
    },
    structured_output=True
)
async def describe_klayout_api(params: DescribeAPIInput, ctx: Context) -> Union[ClassDescriptionResponse, MethodDescriptionResponse]:
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
    await ctx.report_progress(0.1, "Initializing...")
    await _init_components_async()
    
    if _describe_api is None:
        await ctx.report_progress(1.0, "Failed - documentation not available")
        return ErrorHelper.documentation_not_available()
    
    await ctx.report_progress(0.4, f"Looking up {params.class_name}...")
    
    loop = asyncio.get_event_loop()
    
    if params.method_name:
        # Describe specific method
        await ctx.report_progress(0.6, f"Fetching method {params.method_name}...")
        result = await loop.run_in_executor(
            None,
            lambda: _describe_api.describe_method(params.class_name, params.method_name)
        )
        
        if not result.get("success", False):
            # Check if class exists
            class_data = _api_index.get_class(params.class_name) if _api_index else None
            if not class_data:
                await ctx.log_error(f"Class not found: {params.class_name}")
                return ErrorHelper.class_not_found(params.class_name)
            await ctx.log_warning(f"Method not found: {params.class_name}.{params.method_name}")
            return ErrorHelper.method_not_found(params.class_name, params.method_name)
        
        await ctx.report_progress(1.0, "Complete")
        return ResponseFormatter.format_method_description(
            result, params.class_name, params.response_format
        )
    else:
        # Describe entire class
        await ctx.report_progress(0.6, "Fetching class documentation...")
        result = await loop.run_in_executor(
            None,
            lambda: _describe_api.describe_class(
                params.class_name, 
                include_examples=params.include_examples
            )
        )
        
        if not result.get("success", False):
            await ctx.log_error(f"Class not found: {params.class_name}")
            return ErrorHelper.class_not_found(params.class_name)
        
        await ctx.report_progress(1.0, "Complete")
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
    },
    structured_output=True
)
async def call_klayout_api(params: CallAPIInput, ctx: Context) -> CallAPIResponse:
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
    await ctx.report_progress(0.1, "Initializing...")
    await _init_components_async()
    
    # Check KLayout availability
    compat = get_klayout_compat()
    if not compat.is_available:
        await ctx.report_progress(1.0, "Failed - KLayout not available")
        return ErrorHelper.klayout_not_available()
    
    await ctx.report_progress(0.3, "Validating parameters...")
    
    # Validate operation-specific requirements
    operation = params.operation.value
    
    if operation in ("method", "static") and not params.method_name:
        return ErrorHelper.missing_parameter("method_name", operation)
    
    if operation == "method" and not params.handle:
        return ErrorHelper.missing_parameter("handle", operation)
    
    await ctx.report_progress(0.5, f"Executing {params.class_name}.{params.method_name or '__init__'}...")
    await ctx.log_info("API call started", {
        "operation": operation,
        "class": params.class_name,
        "method": params.method_name
    })
    
    # Execute the call in thread pool (since KLayout API calls may be CPU-bound)
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None,
        lambda: _call_api.call(
            operation=operation,
            class_name=params.class_name,
            method_name=params.method_name,
            handle=params.handle,
            params=params.params
        )
    )
    
    await ctx.report_progress(0.8, "Processing result...")
    
    # Enhance error messages
    if not result.get("success", False):
        error_msg = result.get("error", "")
        
        if "not found" in error_msg.lower():
            if "class" in error_msg.lower():
                await ctx.log_error(f"Class not found: {params.class_name}")
                return ErrorHelper.class_not_found(params.class_name)
            elif "method" in error_msg.lower():
                await ctx.log_error(f"Method not found: {params.method_name}")
                return ErrorHelper.method_not_found(params.class_name, params.method_name or "")
            elif "handle" in error_msg.lower():
                await ctx.log_error(f"Handle not found: {params.handle}")
                return ErrorHelper.handle_not_found(params.handle or "")
        
        if "blocked" in error_msg.lower():
            await ctx.log_warning(f"Blocked API call: {params.class_name}.{params.method_name or '__init__'}")
            return ErrorHelper.api_blocked(params.class_name, params.method_name or "__init__")
        
        # Return original error with suggestions
        result["suggestion"] = "Check parameter types and values. Use describe_klayout_api to see method signatures."
        await ctx.log_error("API call failed", {"error": error_msg})
    else:
        await ctx.log_info("API call successful", {
            "return_type": result.get("return_type"),
            "has_handle": result.get("handle") is not None
        })
    
    await ctx.report_progress(1.0, "Complete")
    return result


# ============================================================================
# MCP Tool 4: klayout_manage_handles
# ============================================================================
@mcp.tool(
    name="klayout_manage_handles",
    annotations={
        "title": "Manage KLayout Handles",
        "readOnlyHint": False,
        "destructiveHint": True,
        "idempotentHint": False,
        "openWorldHint": False
    },
    structured_output=True
)
async def klayout_manage_handles(params: ManageHandlesInput, ctx: Context) -> ManageHandlesResponse:
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
    await ctx.report_progress(0.2, "Initializing...")
    await _init_components_async()
    
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
    
    await ctx.report_progress(0.5, f"Performing '{action}' action...")
    
    # Execute action
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None,
        lambda: _manage_handles.manage(
            action=action,
            handle=params.handle,
            alias=params.alias,
            filter_type=params.filter_type
        )
    )
    
    # Format list results
    if action == "list" and result.get("success"):
        await ctx.report_progress(1.0, f"Found {result.get('total', 0)} handles")
        return ResponseFormatter.format_handles_list(
            handles=result.get("handles", []),
            filter_type=params.filter_type,
            format=params.response_format
        )
    
    # Enhance error for handle not found
    if not result.get("success") and "not found" in result.get("error", "").lower():
        await ctx.log_warning(f"Handle not found: {params.handle}")
        return ErrorHelper.handle_not_found(params.handle or "")
    
    await ctx.report_progress(1.0, "Complete")
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
    },
    structured_output=True
)
async def search_klayout_docs(params: SearchDocsInput, ctx: Context) -> SearchDocsResponse:
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
    await ctx.report_progress(0.2, "Initializing...")
    await _init_components_async()
    
    if _search_docs is None:
        await ctx.report_progress(1.0, "Failed - documentation not available")
        return ErrorHelper.documentation_not_available()
    
    await ctx.report_progress(0.4, "Searching documentation...")
    
    loop = asyncio.get_event_loop()
    
    # Handle different search modes
    if params.topic and not params.query:
        result = await loop.run_in_executor(None, lambda: _search_docs.get_topic(params.topic))
    elif params.topic:
        result = await loop.run_in_executor(
            None, 
            lambda: _search_docs.search_topic(params.topic, params.query)
        )
    else:
        if not params.query:
            return {
                "success": False,
                "error": "Either query or topic must be provided",
                "error_code": "MISSING_QUERY",
                "suggestion": "Provide a search query or specify a topic"
            }
        result = await loop.run_in_executor(
            None,
            lambda: _search_docs.search(params.query, limit=params.limit)
        )
    
    if not result.get("success", False):
        await ctx.report_progress(1.0, "Search failed")
        return result
    
    total = len(result.get("results", []))
    await ctx.report_progress(1.0, f"Found {total} results")
    await ctx.log_info("Documentation search complete", {"query": params.query, "topic": params.topic, "total": total})
    
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
    },
    structured_output=True
)
async def klayout_test_import(ctx: Context) -> TestImportResponse:
    """
    Test if KLayout module is properly imported and available.
    
    Verifies KLayout availability and reports which mode is active:
    - 'pya': Running inside KLayout GUI
    - 'standalone': Using klayout Python package
    - 'unavailable': KLayout not found
    
    Use this tool to diagnose KLayout installation issues.
    """
    await ctx.report_progress(0.3, "Checking KLayout availability...")
    
    compat = get_klayout_compat()
    
    if not compat.is_available:
        await ctx.report_progress(1.0, "KLayout not available")
        await ctx.log_error("KLayout import failed")
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
        await ctx.report_progress(0.6, "Testing KLayout functionality...")
        
        # Test by creating a simple object
        Box = compat.get_class('Box', 'db')
        if Box is None:
            await ctx.report_progress(1.0, "Test failed")
            return {
                "success": False,
                "mode": compat.mode,
                "error": "Box class not found",
                "suggestion": "KLayout installation may be incomplete"
            }
        
        box = Box(0, 0, 10, 10)
        
        await ctx.report_progress(1.0, "KLayout working correctly")
        await ctx.log_info(f"KLayout test passed", {"mode": compat.mode})
        
        return {
            "success": True,
            "mode": compat.mode,
            "message": f"KLayout imported successfully in {compat.mode} mode",
            "test_result": f"Created test Box: {box}",
            "available_modules": compat.get_status().get("modules_loaded", [])
        }
    except Exception as e:
        await ctx.report_progress(1.0, "Test failed")
        await ctx.log_error(f"KLayout test error: {e}")
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
    },
    structured_output=True
)
async def klayout_get_status(ctx: Context) -> ServerStatusResponse:
    """
    Get comprehensive KLayout MCP server status information.
    
    Returns:
    - KLayout availability and mode
    - API index statistics (total classes, methods)
    - Documentation availability
    - Active handle count
    - Server health information
    """
    await ctx.report_progress(0.3, "Initializing...")
    await _init_components_async()
    
    await ctx.report_progress(0.6, "Gathering status information...")
    
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
    
    await ctx.report_progress(1.0, "Complete")
    await ctx.log_info("Status check completed", {"health": result["health"]["status"]})
    
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
    },
    structured_output=True
)
async def manage_handles_deprecated(params: ManageHandlesInput, ctx: Context) -> ManageHandlesResponse:
    """
    [DEPRECATED] Use klayout_manage_handles instead.
    
    This tool is deprecated and will be removed in a future version.
    Please use klayout_manage_handles for handle management.
    """
    await ctx.log_warning("Deprecated tool 'manage_handles' called, use 'klayout_manage_handles'")
    result = await klayout_manage_handles(params, ctx)
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
    },
    structured_output=True
)
async def test_klayout_import_deprecated(ctx: Context) -> TestImportResponse:
    """
    [DEPRECATED] Use klayout_test_import instead.
    """
    await ctx.log_warning("Deprecated tool 'test_klayout_import' called, use 'klayout_test_import'")
    result = await klayout_test_import(ctx)
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
    },
    structured_output=True
)
async def get_klayout_version_deprecated(ctx: Context) -> ServerStatusResponse:
    """
    [DEPRECATED] Use klayout_get_status instead.
    """
    await ctx.log_warning("Deprecated tool 'get_klayout_version' called, use 'klayout_get_status'")
    result = await klayout_get_status(ctx)
    result["_deprecation_warning"] = "This tool is deprecated. Use 'klayout_get_status' instead."
    return result


# ============================================================================
# MCP Resources (async version with Context)
# ============================================================================

@mcp.resource("klayout://docs/{class_name}")
async def get_class_doc_resource(class_name: str, ctx: Context) -> str:
    """
    Get full documentation for a KLayout class.
    
    Use this resource to quickly access class documentation without searching.
    """
    await ctx.log_info(f"Accessing class documentation: {class_name}")
    await _init_components_async()
    return klayout_resources.get_class_documentation(class_name)


@mcp.resource("klayout://docs/{class_name}/{method_name}")
async def get_method_doc_resource(class_name: str, method_name: str, ctx: Context) -> str:
    """
    Get documentation for a specific method.
    
    Access detailed method documentation including parameters and return types.
    """
    await ctx.log_info(f"Accessing method documentation: {class_name}.{method_name}")
    await _init_components_async()
    return klayout_resources.get_method_documentation(class_name, method_name)


@mcp.resource("klayout://api/classes")
async def list_classes_resource(ctx: Context) -> str:
    """
    List all available KLayout API classes.
    
    Returns a JSON list of all 1,348+ available classes.
    """
    await ctx.log_debug("Listing all API classes")
    await _init_components_async()
    return klayout_resources.list_all_classes()


@mcp.resource("klayout://api/modules")
async def list_modules_resource(ctx: Context) -> str:
    """
    List all available KLayout modules.
    
    Modules include: db (database), lay (layout view), tl (tools), 
    rdb (report database), pex (parasitic extraction).
    """
    await ctx.log_debug("Listing all API modules")
    await _init_components_async()
    return klayout_resources.list_modules()


@mcp.resource("klayout://status")
async def get_status_resource(ctx: Context) -> str:
    """
    Get KLayout MCP server status.
    
    Check server health, KLayout availability, and loaded components.
    """
    await ctx.log_debug("Accessing server status resource")
    await _init_components_async()
    return klayout_resources.get_server_status()


# ============================================================================
# Main entry point
# ============================================================================
def main() -> None:
    """Main entry point for the MCP server."""
    # Run MCP server with stdio transport
    mcp.run(transport='stdio')


if __name__ == "__main__":
    main()
