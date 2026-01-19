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
