"""
Pydantic Models for KLayout MCP Server

This module defines all input/output models for the MCP tools,
providing automatic validation, documentation, and type safety.
"""

from enum import Enum
from typing import Optional, Dict, Any, List, Literal
from pydantic import BaseModel, Field, field_validator, ConfigDict


# ============================================================================
# Enums for constrained choices
# ============================================================================

class ResponseFormat(str, Enum):
    """Output format for tool responses."""
    JSON = "json"
    MARKDOWN = "markdown"


class SearchType(str, Enum):
    """Type filter for API search."""
    CLASS = "class"
    METHOD = "method"


class ModuleType(str, Enum):
    """KLayout module types."""
    DB = "db"
    LAY = "lay"
    TL = "tl"
    RDB = "rdb"
    PEX = "pex"
    LIB = "lib"


class OperationType(str, Enum):
    """Operation types for API calls."""
    CONSTRUCTOR = "constructor"
    METHOD = "method"
    STATIC = "static"


class HandleAction(str, Enum):
    """Actions for handle management."""
    LIST = "list"
    GET = "get"
    RELEASE = "release"
    RELEASE_ALL = "release_all"
    ALIAS = "alias"


# ============================================================================
# Input Models for MCP Tools
# ============================================================================

class SearchAPIInput(BaseModel):
    """Input model for search_klayout_api tool."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )
    
    query: str = Field(
        ...,
        description="Search query string (e.g., 'Box', 'area', 'Layout', 'polygon')",
        min_length=1,
        max_length=200,
        examples=["Box", "area", "Layout"]
    )
    module: Optional[ModuleType] = Field(
        default=None,
        description="Filter by module: 'db' (database/geometry), 'lay' (layout view), 'tl' (utilities), 'rdb' (report database), 'pex' (parasitic extraction)"
    )
    search_type: Optional[SearchType] = Field(
        default=None,
        description="Filter by type: 'class' for classes only, 'method' for methods only"
    )
    limit: int = Field(
        default=20,
        description="Maximum number of results to return",
        ge=1,
        le=100
    )
    offset: int = Field(
        default=0,
        description="Number of results to skip for pagination",
        ge=0
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.JSON,
        description="Output format: 'json' for programmatic use, 'markdown' for human readability"
    )


class DescribeAPIInput(BaseModel):
    """Input model for describe_klayout_api tool."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )
    
    class_name: str = Field(
        ...,
        description="Name of the KLayout class (e.g., 'Box', 'Layout', 'Cell', 'Region')",
        min_length=1,
        max_length=100,
        examples=["Box", "Layout", "Cell", "Region", "Polygon"]
    )
    method_name: Optional[str] = Field(
        default=None,
        description="Name of a specific method to describe. If omitted, describes the entire class.",
        max_length=100,
        examples=["area", "width", "height", "move"]
    )
    include_examples: bool = Field(
        default=True,
        description="Include code examples in the response"
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.JSON,
        description="Output format: 'json' for programmatic use, 'markdown' for human readability"
    )


class CallAPIInput(BaseModel):
    """Input model for call_klayout_api tool."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )
    
    operation: OperationType = Field(
        ...,
        description="Type of operation: 'constructor' to create object, 'method' to call instance method, 'static' for static method"
    )
    class_name: str = Field(
        ...,
        description="Name of the KLayout class (e.g., 'Box', 'Layout', 'Cell')",
        min_length=1,
        max_length=100
    )
    method_name: Optional[str] = Field(
        default=None,
        description="Method name (required for 'method' and 'static' operations)"
    )
    handle: Optional[str] = Field(
        default=None,
        description="Object handle ID (required for 'method' operation). Get handles from previous constructor calls or klayout_manage_handles."
    )
    params: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Parameters as key-value pairs. Values can be primitives, lists, or handle references (strings starting with 'handle:')"
    )
    
    @field_validator('method_name')
    @classmethod
    def validate_method_for_operation(cls, v, info):
        """Validate that method_name is provided for method/static operations."""
        # Note: Full validation happens at runtime since we need 'operation' value
        return v


class ManageHandlesInput(BaseModel):
    """Input model for klayout_manage_handles tool."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )
    
    action: HandleAction = Field(
        ...,
        description="Action: 'list' all handles, 'get' handle details, 'release' a handle, 'release_all' handles, 'alias' set handle alias"
    )
    handle: Optional[str] = Field(
        default=None,
        description="Handle ID (required for 'get', 'release', 'alias' actions)"
    )
    alias: Optional[str] = Field(
        default=None,
        description="Alias name to assign (required for 'alias' action)",
        max_length=50
    )
    filter_type: Optional[str] = Field(
        default=None,
        description="Filter handles by object type (e.g., 'Box', 'Layout') for 'list' action"
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.JSON,
        description="Output format: 'json' for programmatic use, 'markdown' for human readability"
    )


class SearchDocsInput(BaseModel):
    """Input model for search_klayout_docs tool."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )
    
    query: str = Field(
        default="",
        description="Search query string. Can be empty if topic is specified.",
        max_length=200
    )
    topic: Optional[str] = Field(
        default=None,
        description="Search within a specific topic: 'transformations', 'expressions', 'drc_ref', 'lvs_ref', 'layer_mapping', 'packages', etc."
    )
    limit: int = Field(
        default=10,
        description="Maximum number of results to return",
        ge=1,
        le=50
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.JSON,
        description="Output format: 'json' for programmatic use, 'markdown' for human readability"
    )


# ============================================================================
# Response Models (for documentation and structured output)
# ============================================================================

class PaginationInfo(BaseModel):
    """Pagination metadata for list responses."""
    total: int = Field(..., description="Total number of items available")
    count: int = Field(..., description="Number of items in this response")
    offset: int = Field(..., description="Current offset")
    limit: int = Field(..., description="Requested limit")
    has_more: bool = Field(..., description="Whether more results are available")
    next_offset: Optional[int] = Field(None, description="Offset for next page, if has_more is True")


class SearchResultItem(BaseModel):
    """A single search result item."""
    type: str = Field(..., description="Result type: 'class' or 'method'")
    name: str = Field(..., description="Name of the class or method")
    module: str = Field(..., description="Module containing this item")
    description: str = Field(..., description="Brief description")
    relevance_score: float = Field(..., description="Relevance score (higher is better)")
    class_name: Optional[str] = Field(None, description="Parent class name (for methods)")
    signature: Optional[str] = Field(None, description="Method signature (for methods)")


class SearchAPIResponse(BaseModel):
    """Response model for search_klayout_api."""
    success: bool
    query: str
    filters: Dict[str, Any]
    results: List[SearchResultItem]
    pagination: PaginationInfo
    suggestions: Optional[List[str]] = Field(None, description="Search suggestions if no results found")


class ErrorResponse(BaseModel):
    """Standard error response with actionable suggestions."""
    success: bool = False
    error: str = Field(..., description="Error message")
    error_code: Optional[str] = Field(None, description="Error code for programmatic handling")
    suggestion: Optional[str] = Field(None, description="Suggested action to resolve the error")
    available_options: Optional[List[str]] = Field(None, description="Available options if applicable")
    documentation_link: Optional[str] = Field(None, description="Link to relevant documentation")


# ============================================================================
# Additional Response Models for Output Schemas
# ============================================================================

class MethodParameter(BaseModel):
    """Parameter information for a method."""
    name: str = Field(..., description="Parameter name")
    type: str = Field(..., description="Parameter type")
    description: Optional[str] = Field(None, description="Parameter description")
    default: Optional[Any] = Field(None, description="Default value if optional")


class MethodInfo(BaseModel):
    """Information about a class method."""
    name: str = Field(..., description="Method name")
    signature: Optional[str] = Field(None, description="Method signature")
    description: Optional[str] = Field(None, description="Method description")
    return_type: Optional[str] = Field(None, description="Return type")
    return_description: Optional[str] = Field(None, description="Return value description")
    parameters: List[MethodParameter] = Field(default_factory=list, description="Method parameters")


class ClassDescriptionResponse(BaseModel):
    """Response model for describe_klayout_api when describing a class."""
    success: bool
    name: str = Field(..., description="Class name")
    module: str = Field(..., description="Module name")
    description: Optional[str] = Field(None, description="Class description")
    constructors: List[MethodInfo] = Field(default_factory=list, description="Constructor methods")
    methods: List[MethodInfo] = Field(default_factory=list, description="Instance methods")
    static_methods: List[MethodInfo] = Field(default_factory=list, description="Static methods")
    deprecated_methods: List[MethodInfo] = Field(default_factory=list, description="Deprecated methods")
    examples: List[str] = Field(default_factory=list, description="Code examples")
    base_classes: List[str] = Field(default_factory=list, description="Base/inherited classes")


class MethodDescriptionResponse(BaseModel):
    """Response model for describe_klayout_api when describing a method."""
    success: bool
    class_name: str = Field(..., description="Parent class name")
    method_info: MethodInfo = Field(..., description="Method details")


class CallAPIResponse(BaseModel):
    """Response model for call_klayout_api."""
    success: bool
    return_type: str = Field(..., description="Type of the returned value")
    execution_time_ms: float = Field(..., description="Execution time in milliseconds")
    handle: Optional[str] = Field(None, description="Object handle if return value is a complex object")
    value: Any = Field(None, description="Return value (primitive) or string representation")
    alias: Optional[str] = Field(None, description="Alias assigned to the handle")
    error: Optional[str] = Field(None, description="Error message if failed")
    traceback: Optional[str] = Field(None, description="Stack trace if failed")
    suggestion: Optional[str] = Field(None, description="Suggestion for fixing the error")


class HandleInfo(BaseModel):
    """Information about a registered handle."""
    id: str = Field(..., description="Handle ID")
    type: str = Field(..., description="Object type/class name")
    module: Optional[str] = Field(None, description="Module name")
    alias: Optional[str] = Field(None, description="Alias name if set")
    created_at: Optional[str] = Field(None, description="Creation timestamp")


class ManageHandlesResponse(BaseModel):
    """Response model for klayout_manage_handles."""
    success: bool
    action: Optional[str] = Field(None, description="Action that was performed")
    handles: List[HandleInfo] = Field(default_factory=list, description="List of handles (for list action)")
    total: Optional[int] = Field(None, description="Total number of handles")
    filter_type: Optional[str] = Field(None, description="Filter applied")
    handle: Optional[HandleInfo] = Field(None, description="Single handle info (for get action)")
    released: Optional[bool] = Field(None, description="Whether handle was released")
    aliased: Optional[bool] = Field(None, description="Whether alias was set")
    error: Optional[str] = Field(None, description="Error message if failed")
    error_code: Optional[str] = Field(None, description="Error code")
    suggestion: Optional[str] = Field(None, description="Suggestion for fixing the error")
    content: Optional[str] = Field(None, description="Markdown formatted content")


class DocSearchResult(BaseModel):
    """A single documentation search result."""
    title: str = Field(..., description="Document title")
    snippet: str = Field(..., description="Text snippet")
    source: Optional[str] = Field(None, description="Source file/topic")
    score: Optional[float] = Field(None, description="Relevance score")


class SearchDocsResponse(BaseModel):
    """Response model for search_klayout_docs."""
    success: bool
    query: str = Field(default="", description="Search query")
    topic: Optional[str] = Field(None, description="Topic filter")
    results: List[DocSearchResult] = Field(default_factory=list, description="Search results")
    total: int = Field(default=0, description="Total number of results")
    documentation: Optional[str] = Field(None, description="Full documentation (for topic lookup)")
    topics: Optional[List[str]] = Field(None, description="List of available topics")
    error: Optional[str] = Field(None, description="Error message if failed")
    error_code: Optional[str] = Field(None, description="Error code")
    suggestion: Optional[str] = Field(None, description="Suggestion for fixing the error")
    content: Optional[str] = Field(None, description="Markdown formatted content")


class TestImportResponse(BaseModel):
    """Response model for klayout_test_import."""
    success: bool
    mode: str = Field(..., description="KLayout mode: 'pya', 'standalone', or 'unavailable'")
    message: Optional[str] = Field(None, description="Success message")
    test_result: Optional[str] = Field(None, description="Test execution result")
    available_modules: List[str] = Field(default_factory=list, description="List of available modules")
    error: Optional[str] = Field(None, description="Error message if failed")
    suggestion: Optional[str] = Field(None, description="Suggestion for fixing")
    troubleshooting: Optional[List[str]] = Field(None, description="List of troubleshooting steps")


class KLayoutStatus(BaseModel):
    """KLayout availability status."""
    available: bool = Field(..., description="Whether KLayout is available")
    mode: str = Field(..., description="Mode: 'pya', 'standalone', or 'unavailable'")
    modules_loaded: List[str] = Field(default_factory=list, description="List of loaded modules")


class IndexStatus(BaseModel):
    """API index status."""
    loaded: bool = Field(..., description="Whether index is loaded")
    stats: Optional[Dict[str, Any]] = Field(None, description="Index statistics")


class DocumentationStatus(BaseModel):
    """Documentation availability status."""
    available: bool = Field(..., description="Whether documentation is available")


class HandleStats(BaseModel):
    """Handle registry statistics."""
    total: int = Field(default=0, description="Total number of active handles")
    by_type: Optional[Dict[str, int]] = Field(None, description="Handle count by type")


class HealthStatus(BaseModel):
    """Server health status."""
    status: str = Field(..., description="Health status: 'healthy' or 'degraded'")
    issues: List[str] = Field(default_factory=list, description="List of issues if degraded")


class ServerStatusResponse(BaseModel):
    """Response model for klayout_get_status."""
    success: bool
    server_name: str = Field(..., description="Server name")
    klayout: KLayoutStatus = Field(..., description="KLayout status")
    index: IndexStatus = Field(..., description="API index status")
    documentation: DocumentationStatus = Field(..., description="Documentation status")
    handles: HandleStats = Field(..., description="Handle statistics")
    health: HealthStatus = Field(..., description="Health status")
