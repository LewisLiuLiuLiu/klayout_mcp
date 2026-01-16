"""
API Invoker - Reflection-based KLayout API execution

This module provides the ability to dynamically call KLayout APIs
using Python reflection mechanisms.
"""

import importlib
import traceback
import time
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass

from .handle_registry import HandleRegistry
from .parameter_parser import ParameterParser


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
    - Dynamic module/class loading
    - Constructor invocation
    - Instance method invocation
    - Static method invocation
    - Automatic result registration in HandleRegistry
    """
    
    # KLayout module mappings
    KLAYOUT_MODULES = {
        'db': 'klayout.db',
        'lay': 'klayout.lay', 
        'rdb': 'klayout.rdb',
        'tl': 'klayout.tl',
        'lib': 'klayout.lib',
    }
    
    # Types that should be registered as handles
    HANDLE_TYPES = {
        'Layout', 'Cell', 'Instance', 'Box', 'DBox', 'Point', 'DPoint',
        'Edge', 'DEdge', 'Path', 'DPath', 'Polygon', 'DPolygon',
        'Region', 'Edges', 'EdgePairs', 'Texts',
        'Trans', 'DTrans', 'CplxTrans', 'DCplxTrans', 'ICplxTrans',
        'LayerInfo', 'RecursiveShapeIterator', 'Shapes',
        'LayoutView', 'CellView', 'LayerProperties',
        'Technology', 'Library',
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
        """Get a class from a KLayout module."""
        # Map module name to full module path
        module_path = self.KLAYOUT_MODULES.get(module, f'klayout.{module}')
        
        # Try to import and cache the module
        if module_path not in self._module_cache:
            try:
                self._module_cache[module_path] = importlib.import_module(module_path)
            except ImportError:
                return None
        
        mod = self._module_cache[module_path]
        return getattr(mod, class_name, None)
    
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
            # Determine module from result type
            module = 'db'  # Default
            result_module = type(result).__module__
            for mod_name, mod_path in self.KLAYOUT_MODULES.items():
                if mod_path in result_module:
                    module = mod_name
                    break
            
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
        """Check if KLayout modules are available."""
        try:
            import klayout.db
            return True
        except ImportError:
            return False
