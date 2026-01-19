"""
Invoker module for KLayout API invocation.

This module provides:
- HandleRegistry: Manage KLayout object references
- ParameterParser: Parse and validate API parameters
- APIInvoker: Execute KLayout API calls via reflection
- KLayoutCompat: Compatibility layer for pya/standalone modes
"""

from .handle_registry import HandleRegistry, HandleInfo
from .parameter_parser import ParameterParser, ParamDef, ParsedParams
from .api_invoker import APIInvoker, InvokeResult
from .klayout_compat import (
    KLayoutCompat,
    KLayoutModuleInfo,
    get_klayout_compat,
    get_pya,
    import_klayout_class,
)

__all__ = [
    "HandleRegistry",
    "HandleInfo",
    "ParameterParser",
    "ParamDef",
    "ParsedParams",
    "APIInvoker",
    "InvokeResult",
    "KLayoutCompat",
    "KLayoutModuleInfo",
    "get_klayout_compat",
    "get_pya",
    "import_klayout_class",
]
