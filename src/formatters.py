"""
Response Formatter for KLayout MCP Server

This module handles formatting responses in both JSON and Markdown formats,
and provides helpers for creating actionable error messages.
"""

from typing import Dict, Any, List, Optional
from .models import ResponseFormat, PaginationInfo


class ResponseFormatter:
    """
    Formats tool responses in JSON or Markdown format.
    
    JSON format: Machine-readable structured data
    Markdown format: Human-readable formatted text
    """
    
    @staticmethod
    def format_search_results(
        results: List[Dict[str, Any]],
        query: str,
        filters: Dict[str, Any],
        pagination: PaginationInfo,
        format: ResponseFormat = ResponseFormat.JSON
    ) -> Dict[str, Any]:
        """Format search results in the requested format."""
        
        if format == ResponseFormat.MARKDOWN:
            return ResponseFormatter._format_search_markdown(results, query, filters, pagination)
        
        return {
            "success": True,
            "query": query,
            "filters": {k: v for k, v in filters.items() if v is not None},
            "results": results,
            "pagination": pagination.model_dump(),
        }
    
    @staticmethod
    def _format_search_markdown(
        results: List[Dict[str, Any]],
        query: str,
        filters: Dict[str, Any],
        pagination: PaginationInfo
    ) -> Dict[str, Any]:
        """Format search results as Markdown."""
        
        lines = [f"## Search Results for '{query}'"]
        
        # Add filter info
        active_filters = {k: v for k, v in filters.items() if v is not None}
        if active_filters:
            lines.append(f"\n**Filters:** {', '.join(f'{k}={v}' for k, v in active_filters.items())}")
        
        lines.append(f"\n**Found:** {pagination.total} results (showing {pagination.count})")
        
        if not results:
            lines.append("\n*No results found.*")
        else:
            lines.append("")
            for i, r in enumerate(results, 1):
                if r["type"] == "class":
                    lines.append(f"### {i}. `{r['name']}` (class)")
                    lines.append(f"- **Module:** {r['module']}")
                    lines.append(f"- **Description:** {r['description'][:200]}...")
                else:
                    class_info = f" in `{r.get('class_name', 'unknown')}`" if r.get('class_name') else ""
                    lines.append(f"### {i}. `{r['name']}`{class_info} (method)")
                    lines.append(f"- **Module:** {r['module']}")
                    if r.get('signature'):
                        lines.append(f"- **Signature:** `{r['signature']}`")
                    lines.append(f"- **Description:** {r['description'][:200]}...")
                lines.append(f"- **Relevance:** {r['relevance_score']:.2f}")
                lines.append("")
        
        # Add pagination info
        if pagination.has_more:
            lines.append(f"\n*More results available. Use offset={pagination.next_offset} to see next page.*")
        
        return {
            "success": True,
            "content": "\n".join(lines),
            "pagination": pagination.model_dump()
        }
    
    @staticmethod
    def format_class_description(
        class_data: Dict[str, Any],
        format: ResponseFormat = ResponseFormat.JSON
    ) -> Dict[str, Any]:
        """Format class description in the requested format."""
        
        if format == ResponseFormat.MARKDOWN:
            return ResponseFormatter._format_class_markdown(class_data)
        
        return {
            "success": True,
            **class_data
        }
    
    @staticmethod
    def _format_class_markdown(class_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format class description as Markdown."""
        
        lines = [f"# Class `{class_data.get('name', 'Unknown')}`"]
        lines.append(f"\n**Module:** `{class_data.get('module', 'unknown')}`")
        
        if class_data.get('description'):
            lines.append(f"\n## Description\n{class_data['description']}")
        
        # Constructors
        constructors = class_data.get('constructors', [])
        if constructors:
            lines.append("\n## Constructors")
            for c in constructors[:5]:  # Limit to first 5
                sig = c.get('signature', c.get('name', ''))
                lines.append(f"\n### `{sig}`")
                if c.get('description'):
                    lines.append(f"{c['description'][:300]}")
        
        # Methods summary
        methods = class_data.get('methods', [])
        if methods:
            lines.append(f"\n## Methods ({len(methods)} total)")
            lines.append("\n| Method | Description |")
            lines.append("|--------|-------------|")
            for m in methods[:20]:  # Limit to first 20
                desc = m.get('description', '')[:80].replace('|', '\\|')
                lines.append(f"| `{m.get('name', '')}` | {desc} |")
            if len(methods) > 20:
                lines.append(f"\n*... and {len(methods) - 20} more methods*")
        
        # Static methods
        static_methods = class_data.get('static_methods', [])
        if static_methods:
            lines.append(f"\n## Static Methods ({len(static_methods)} total)")
            for m in static_methods[:10]:
                lines.append(f"- `{m.get('name', '')}`")
        
        # Examples
        examples = class_data.get('examples', [])
        if examples:
            lines.append("\n## Examples")
            for ex in examples[:3]:
                lines.append(f"\n```python\n{ex}\n```")
        
        return {
            "success": True,
            "content": "\n".join(lines)
        }
    
    @staticmethod
    def format_method_description(
        method_data: Dict[str, Any],
        class_name: str,
        format: ResponseFormat = ResponseFormat.JSON
    ) -> Dict[str, Any]:
        """Format method description in the requested format."""
        
        if format == ResponseFormat.MARKDOWN:
            return ResponseFormatter._format_method_markdown(method_data, class_name)
        
        return {
            "success": True,
            "class_name": class_name,
            **method_data
        }
    
    @staticmethod
    def _format_method_markdown(method_data: Dict[str, Any], class_name: str) -> Dict[str, Any]:
        """Format method description as Markdown."""
        
        method_name = method_data.get('name', 'unknown')
        lines = [f"# `{class_name}.{method_name}`"]
        
        if method_data.get('signature'):
            lines.append(f"\n**Signature:** `{method_data['signature']}`")
        
        if method_data.get('description'):
            lines.append(f"\n## Description\n{method_data['description']}")
        
        # Parameters
        params = method_data.get('parameters', [])
        if params:
            lines.append("\n## Parameters")
            lines.append("\n| Name | Type | Description |")
            lines.append("|------|------|-------------|")
            for p in params:
                lines.append(f"| `{p.get('name', '')}` | `{p.get('type', '')}` | {p.get('description', '')} |")
        
        # Return type
        if method_data.get('return_type'):
            lines.append(f"\n## Returns\n`{method_data['return_type']}`")
            if method_data.get('return_description'):
                lines.append(f"\n{method_data['return_description']}")
        
        return {
            "success": True,
            "content": "\n".join(lines)
        }
    
    @staticmethod
    def format_handles_list(
        handles: List[Dict[str, Any]],
        filter_type: Optional[str],
        format: ResponseFormat = ResponseFormat.JSON
    ) -> Dict[str, Any]:
        """Format handles list in the requested format."""
        
        if format == ResponseFormat.MARKDOWN:
            return ResponseFormatter._format_handles_markdown(handles, filter_type)
        
        return {
            "success": True,
            "filter_type": filter_type,
            "handles": handles,
            "total": len(handles)
        }
    
    @staticmethod
    def _format_handles_markdown(
        handles: List[Dict[str, Any]],
        filter_type: Optional[str]
    ) -> Dict[str, Any]:
        """Format handles list as Markdown."""
        
        lines = ["# Active Handles"]
        
        if filter_type:
            lines.append(f"\n**Filter:** type = `{filter_type}`")
        
        lines.append(f"\n**Total:** {len(handles)} handle(s)")
        
        if not handles:
            lines.append("\n*No handles currently registered.*")
        else:
            lines.append("\n| Handle ID | Type | Module | Alias |")
            lines.append("|-----------|------|--------|-------|")
            for h in handles:
                alias = h.get('alias', '-')
                lines.append(f"| `{h['id']}` | {h.get('type', 'unknown')} | {h.get('module', '-')} | {alias} |")
        
        return {
            "success": True,
            "content": "\n".join(lines),
            "total": len(handles)
        }
    
    @staticmethod
    def format_docs_results(
        results: List[Dict[str, Any]],
        query: str,
        topic: Optional[str],
        format: ResponseFormat = ResponseFormat.JSON
    ) -> Dict[str, Any]:
        """Format documentation search results."""
        
        if format == ResponseFormat.MARKDOWN:
            return ResponseFormatter._format_docs_markdown(results, query, topic)
        
        return {
            "success": True,
            "query": query,
            "topic": topic,
            "results": results,
            "total": len(results)
        }
    
    @staticmethod
    def _format_docs_markdown(
        results: List[Dict[str, Any]],
        query: str,
        topic: Optional[str]
    ) -> Dict[str, Any]:
        """Format documentation results as Markdown."""
        
        title = f"Documentation: '{query}'" if query else f"Topic: {topic}"
        lines = [f"## {title}"]
        lines.append(f"\n**Found:** {len(results)} result(s)")
        
        if not results:
            lines.append("\n*No documentation found.*")
        else:
            for i, r in enumerate(results, 1):
                lines.append(f"\n### {i}. {r.get('title', 'Untitled')}")
                if r.get('snippet'):
                    lines.append(f"\n{r['snippet'][:500]}...")
                if r.get('source'):
                    lines.append(f"\n*Source: {r['source']}*")
        
        return {
            "success": True,
            "content": "\n".join(lines),
            "total": len(results)
        }


class ErrorHelper:
    """
    Provides actionable error messages with suggestions.
    """
    
    # Available modules for suggestions
    AVAILABLE_MODULES = ["db", "lay", "tl", "rdb", "pex", "lib"]
    
    # Common class names for suggestions
    COMMON_CLASSES = [
        "Box", "DBox", "Point", "DPoint", "Vector", "DVector",
        "Edge", "DEdge", "Polygon", "DPolygon", "Region", "Edges",
        "Layout", "Cell", "Instance", "LayerInfo", "Trans", "CplxTrans",
        "Text", "Path", "SimplePolygon", "RecursiveShapeIterator"
    ]
    
    @staticmethod
    def class_not_found(class_name: str, module: Optional[str] = None) -> Dict[str, Any]:
        """Create error for class not found."""
        
        # Find similar class names
        similar = [c for c in ErrorHelper.COMMON_CLASSES 
                   if class_name.lower() in c.lower() or c.lower() in class_name.lower()]
        
        error = {
            "success": False,
            "error": f"Class '{class_name}' not found" + (f" in module '{module}'" if module else ""),
            "error_code": "CLASS_NOT_FOUND",
            "suggestion": f"Use search_klayout_api(query='{class_name}') to find similar classes",
            "available_modules": ErrorHelper.AVAILABLE_MODULES,
        }
        
        if similar:
            error["similar_classes"] = similar[:5]
        
        return error
    
    @staticmethod
    def method_not_found(class_name: str, method_name: str) -> Dict[str, Any]:
        """Create error for method not found."""
        return {
            "success": False,
            "error": f"Method '{method_name}' not found in class '{class_name}'",
            "error_code": "METHOD_NOT_FOUND",
            "suggestion": f"Use describe_klayout_api(class_name='{class_name}') to see all available methods",
        }
    
    @staticmethod
    def handle_not_found(handle: str) -> Dict[str, Any]:
        """Create error for handle not found."""
        return {
            "success": False,
            "error": f"Handle '{handle}' not found or has been released",
            "error_code": "HANDLE_NOT_FOUND",
            "suggestion": "Use klayout_manage_handles(action='list') to see all active handles",
        }
    
    @staticmethod
    def invalid_operation(operation: str, reason: str) -> Dict[str, Any]:
        """Create error for invalid operation."""
        return {
            "success": False,
            "error": f"Invalid operation '{operation}': {reason}",
            "error_code": "INVALID_OPERATION",
            "suggestion": "Valid operations are: 'constructor', 'method', 'static'",
            "available_options": ["constructor", "method", "static"],
        }
    
    @staticmethod
    def missing_parameter(param_name: str, operation: str) -> Dict[str, Any]:
        """Create error for missing required parameter."""
        suggestions = {
            "method_name": "Provide method_name for 'method' or 'static' operations",
            "handle": "Provide handle from a previous constructor call. Use klayout_manage_handles(action='list') to see available handles.",
            "class_name": "Provide the KLayout class name (e.g., 'Box', 'Layout', 'Cell')",
        }
        return {
            "success": False,
            "error": f"Missing required parameter '{param_name}' for operation '{operation}'",
            "error_code": "MISSING_PARAMETER",
            "suggestion": suggestions.get(param_name, f"Please provide the '{param_name}' parameter"),
        }
    
    @staticmethod
    def api_blocked(class_name: str, method_name: str) -> Dict[str, Any]:
        """Create error for blocked API call."""
        return {
            "success": False,
            "error": f"API call blocked by security sandbox: {class_name}.{method_name}",
            "error_code": "API_BLOCKED",
            "suggestion": "This API is restricted for security reasons. Try using a different approach.",
        }
    
    @staticmethod
    def klayout_not_available() -> Dict[str, Any]:
        """Create error for KLayout not available."""
        return {
            "success": False,
            "error": "KLayout modules not available",
            "error_code": "KLAYOUT_NOT_AVAILABLE",
            "suggestion": "Ensure KLayout is installed. For standalone mode: pip install klayout. For GUI mode: run from within KLayout.",
        }
    
    @staticmethod
    def documentation_not_available() -> Dict[str, Any]:
        """Create error for documentation not available."""
        return {
            "success": False,
            "error": "Documentation not available",
            "error_code": "DOCS_NOT_AVAILABLE",
            "suggestion": "Ensure the documentation files are present in klayout-doc/markdown_docs/",
        }
    
    @staticmethod
    def index_not_loaded() -> Dict[str, Any]:
        """Create error for index not loaded."""
        return {
            "success": False,
            "error": "API index not loaded",
            "error_code": "INDEX_NOT_LOADED",
            "suggestion": "Ensure the index file exists at data/api_index.json. Run the index builder if needed.",
        }
