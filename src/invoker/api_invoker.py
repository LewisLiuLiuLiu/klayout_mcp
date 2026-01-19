"""
API Invoker - Reflection-based KLayout API execution

This module provides the ability to dynamically call KLayout APIs
using Python reflection mechanisms.

Supports both 'pya' (inside KLayout GUI) and 'klayout.db' (standalone) modes
through the KLayoutCompat compatibility layer.
"""

import importlib
import traceback
import time
from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass

from .handle_registry import HandleRegistry
from .parameter_parser import ParameterParser
from .klayout_compat import get_klayout_compat, KLayoutCompat


@dataclass
class InvokeResult:
    """Result of an API invocation."""
    success: bool
    return_value: Any
    return_handle: Optional[str]
    return_type: str
    execution_time: float
    error: Optional[str] = None
    traceback: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        result = {
            "success": self.success,
            "return_type": self.return_type,
            "execution_time_ms": round(self.execution_time * 1000, 2)
        }
        
        if self.success:
            if self.return_handle:
                result["handle"] = self.return_handle
                result["value"] = f"<{self.return_type} object>"
            else:
                result["value"] = self._serialize_value(self.return_value)
        else:
            result["error"] = self.error
            if self.traceback:
                result["traceback"] = self.traceback
        
        return result
    
    def _serialize_value(self, value: Any) -> Any:
        """Serialize a value for JSON output."""
        if value is None:
            return None
        if isinstance(value, (int, float, str, bool)):
            return value
        if isinstance(value, (list, tuple)):
            return [self._serialize_value(v) for v in value]
        if isinstance(value, dict):
            return {k: self._serialize_value(v) for k, v in value.items()}
        # For complex objects, return string representation
        return str(value)


class APIInvoker:
    """
    Executes KLayout API calls using reflection.
    
    Features:
    - Dynamic module/class loading via KLayoutCompat
    - Constructor invocation with positional and keyword arguments
    - Instance method invocation
    - Static method invocation
    - Automatic result registration in HandleRegistry
    - Supports both 'pya' and standalone 'klayout.db' modes
    """
    
    # Types that should be registered as handles
    HANDLE_TYPES = {
        'Layout', 'Cell', 'Instance', 'Box', 'DBox', 'Point', 'DPoint',
        'Vector', 'DVector', 'Edge', 'DEdge', 'EdgePair', 'DEdgePair',
        'Path', 'DPath', 'Polygon', 'DPolygon', 'SimplePolygon', 'DSimplePolygon',
        'Text', 'DText', 'Region', 'Edges', 'EdgePairs', 'Texts',
        'Trans', 'DTrans', 'CplxTrans', 'DCplxTrans', 'ICplxTrans', 'VCplxTrans',
        'LayerInfo', 'RecursiveShapeIterator', 'RecursiveInstanceIterator', 'Shapes',
        'LayoutView', 'CellView', 'LayerProperties',
        'Technology', 'Library', 'PCellDeclaration',
        'CellInstArray', 'LayerMapping', 'ShapeProcessor',
        'ReportDatabase', 'RdbCategory', 'RdbItem', 'RdbCell',
    }
    
    def __init__(self, registry: HandleRegistry, 
                 sandbox: Optional[Any] = None):
        """
        Initialize the APIInvoker.
        
        Args:
            registry: HandleRegistry for managing object references
            sandbox: Optional sandbox for security checks
        """
        self.registry = registry
        self.sandbox = sandbox
        self.parser = ParameterParser(registry)
        self._compat: KLayoutCompat = get_klayout_compat()
        self._module_cache: Dict[str, Any] = {}
    
    def invoke_constructor(self, class_name: str, module: str,
                          params: Optional[Dict[str, Any]] = None) -> InvokeResult:
        """
        Invoke a class constructor.
        
        Args:
            class_name: Name of the class
            module: Module name (db, lay, etc.)
            params: Constructor parameters
            
        Returns:
            InvokeResult with the new object handle
        """
        start_time = time.time()
        
        try:
            # Security check
            if self.sandbox and not self.sandbox.check_api_call(class_name, '__init__'):
                return InvokeResult(
                    success=False,
                    return_value=None,
                    return_handle=None,
                    return_type='error',
                    execution_time=time.time() - start_time,
                    error=f"API call blocked by sandbox: {class_name}.__init__"
                )
            
            # Get the class
            cls = self._get_class(class_name, module)
            if cls is None:
                return InvokeResult(
                    success=False,
                    return_value=None,
                    return_handle=None,
                    return_type='error',
                    execution_time=time.time() - start_time,
                    error=f"Class not found: {class_name} in module {module}"
                )
            
            # Parse and resolve parameters
            params = params or {}
            resolved_params = self.parser.resolve_handles(params)
            
            # Create instance
            obj = cls(**resolved_params) if resolved_params else cls()
            
            # Register handle if it's a complex type
            handle = None
            if self._should_register(class_name, obj):
                handle = self.registry.register(obj, class_name, module=module)
            
            return InvokeResult(
                success=True,
                return_value=obj,
                return_handle=handle,
                return_type=class_name,
                execution_time=time.time() - start_time
            )
            
        except Exception as e:
            return InvokeResult(
                success=False,
                return_value=None,
                return_handle=None,
                return_type='error',
                execution_time=time.time() - start_time,
                error=str(e),
                traceback=traceback.format_exc()
            )
    
    def invoke_method(self, handle: str, method_name: str,
                     params: Optional[Dict[str, Any]] = None) -> InvokeResult:
        """
        Invoke an instance method on a registered object.
        
        Args:
            handle: Handle ID of the object
            method_name: Name of the method to call
            params: Method parameters
            
        Returns:
            InvokeResult with the method return value
        """
        start_time = time.time()
        
        try:
            # Get the object
            obj = self.registry.get(handle)
            if obj is None:
                return InvokeResult(
                    success=False,
                    return_value=None,
                    return_handle=None,
                    return_type='error',
                    execution_time=time.time() - start_time,
                    error=f"Handle not found: {handle}"
                )
            
            obj_type = type(obj).__name__
            
            # Security check
            if self.sandbox and not self.sandbox.check_api_call(obj_type, method_name):
                return InvokeResult(
                    success=False,
                    return_value=None,
                    return_handle=None,
                    return_type='error',
                    execution_time=time.time() - start_time,
                    error=f"API call blocked by sandbox: {obj_type}.{method_name}"
                )
            
            # Get the method
            method = getattr(obj, method_name, None)
            if method is None or not callable(method):
                return InvokeResult(
                    success=False,
                    return_value=None,
                    return_handle=None,
                    return_type='error',
                    execution_time=time.time() - start_time,
                    error=f"Method not found: {method_name} on {obj_type}"
                )
            
            # Parse and resolve parameters
            params = params or {}
            resolved_params = self.parser.resolve_handles(params)
            
            # Call the method
            result = method(**resolved_params) if resolved_params else method()
            
            # Process return value
            return self._process_result(result, start_time)
            
        except Exception as e:
            return InvokeResult(
                success=False,
                return_value=None,
                return_handle=None,
                return_type='error',
                execution_time=time.time() - start_time,
                error=str(e),
                traceback=traceback.format_exc()
            )
    
    def invoke_static(self, class_name: str, method_name: str,
                     module: str,
                     params: Optional[Dict[str, Any]] = None) -> InvokeResult:
        """
        Invoke a static method on a class.
        
        Args:
            class_name: Name of the class
            method_name: Name of the static method
            module: Module name
            params: Method parameters
            
        Returns:
            InvokeResult with the method return value
        """
        start_time = time.time()
        
        try:
            # Security check
            if self.sandbox and not self.sandbox.check_api_call(class_name, method_name):
                return InvokeResult(
                    success=False,
                    return_value=None,
                    return_handle=None,
                    return_type='error',
                    execution_time=time.time() - start_time,
                    error=f"API call blocked by sandbox: {class_name}.{method_name}"
                )
            
            # Get the class
            cls = self._get_class(class_name, module)
            if cls is None:
                return InvokeResult(
                    success=False,
                    return_value=None,
                    return_handle=None,
                    return_type='error',
                    execution_time=time.time() - start_time,
                    error=f"Class not found: {class_name} in module {module}"
                )
            
            # Get the static method
            method = getattr(cls, method_name, None)
            if method is None or not callable(method):
                return InvokeResult(
                    success=False,
                    return_value=None,
                    return_handle=None,
                    return_type='error',
                    execution_time=time.time() - start_time,
                    error=f"Static method not found: {method_name} on {class_name}"
                )
            
            # Parse and resolve parameters
            params = params or {}
            resolved_params = self.parser.resolve_handles(params)
            
            # Call the method
            result = method(**resolved_params) if resolved_params else method()
            
            # Process return value
            return self._process_result(result, start_time)
            
        except Exception as e:
            return InvokeResult(
                success=False,
                return_value=None,
                return_handle=None,
                return_type='error',
                execution_time=time.time() - start_time,
                error=str(e),
                traceback=traceback.format_exc()
            )
    
    def _get_class(self, class_name: str, module: str) -> Optional[type]:
        """
        Get a class from a KLayout module using the compatibility layer.
        
        Args:
            class_name: Name of the class
            module: Module name (db, lay, tl, rdb, lib)
            
        Returns:
            The class or None if not found
        """
        # Use KLayoutCompat for unified access
        return self._compat.get_class(class_name, module)
    
    def _should_register(self, type_name: str, obj: Any) -> bool:
        """Determine if an object should be registered as a handle."""
        # Register known complex types
        if type_name in self.HANDLE_TYPES:
            return True
        
        # Register if it's not a primitive type
        if not isinstance(obj, (int, float, str, bool, type(None))):
            return True
        
        return False
    
    def _process_result(self, result: Any, start_time: float) -> InvokeResult:
        """Process a method return value."""
        result_type = type(result).__name__
        
        # Register handle if appropriate
        handle = None
        if result is not None and self._should_register(result_type, result):
            # Determine module from result type using compatibility layer
            module = self._compat.get_object_module(result) or 'db'
            handle = self.registry.register(result, result_type, module=module)
        
        return InvokeResult(
            success=True,
            return_value=result,
            return_handle=handle,
            return_type=result_type,
            execution_time=time.time() - start_time
        )
    
    def get_available_methods(self, class_name: str, module: str) -> List[str]:
        """
        Get list of available methods for a class.
        
        Args:
            class_name: Name of the class
            module: Module name
            
        Returns:
            List of method names
        """
        cls = self._get_class(class_name, module)
        if cls is None:
            return []
        
        methods = []
        for name in dir(cls):
            if not name.startswith('_'):
                attr = getattr(cls, name, None)
                if callable(attr):
                    methods.append(name)
        
        return sorted(methods)
    
    def check_klayout_available(self) -> bool:
        """
        Check if KLayout modules are available.
        
        Returns:
            True if KLayout (pya or standalone) is available
        """
        return self._compat.is_available
    
    def get_klayout_status(self) -> Dict[str, Any]:
        """
        Get detailed status of KLayout module availability.
        
        Returns:
            Dictionary with status information including mode and loaded modules
        """
        return self._compat.get_status()
    
    def get_module_for_class(self, class_name: str) -> str:
        """
        Get the module name for a given class.
        
        Args:
            class_name: Name of the class
            
        Returns:
            Module name (db, lay, tl, rdb, lib)
        """
        return self._compat.get_module_for_class(class_name)

