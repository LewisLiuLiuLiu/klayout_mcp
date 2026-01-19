"""
Call API Tool - Execute KLayout API calls

This tool provides the ability to execute KLayout API calls.
Supports both 'pya' and standalone 'klayout.db' modes.
"""

from typing import Optional, Dict, Any, List

from ..invoker.api_invoker import APIInvoker
from ..invoker.handle_registry import HandleRegistry
from ..invoker.klayout_compat import get_klayout_compat
from ..security.sandbox import Sandbox


class CallAPITool:
    """
    Tool for executing KLayout API calls.
    
    Supports constructor calls, instance methods, and static methods.
    """
    
    def __init__(self, invoker: APIInvoker, registry: HandleRegistry,
                 sandbox: Optional[Sandbox] = None):
        """
        Initialize the tool.
        
        Args:
            invoker: APIInvoker instance
            registry: HandleRegistry instance
            sandbox: Optional Sandbox instance
        """
        self.invoker = invoker
        self.registry = registry
        self.sandbox = sandbox
        self._compat = get_klayout_compat()
    
    def call(self, operation: str, class_name: str,
             method_name: Optional[str] = None,
             handle: Optional[str] = None,
             params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute a KLayout API call.
        
        Args:
            operation: Type of operation ("constructor", "method", "static")
            class_name: Name of the class
            method_name: Name of the method (for method/static operations)
            handle: Handle ID of the object (for method operations)
            params: Parameters for the call
            
        Returns:
            Dictionary with call result
        """
        # Validate operation
        if operation not in ("constructor", "method", "static"):
            return {
                "success": False,
                "error": f"Invalid operation: {operation}. Must be 'constructor', 'method', or 'static'"
            }
        
        # Validate required parameters
        if operation == "method" and not handle:
            return {
                "success": False,
                "error": "Handle is required for method operations"
            }
        
        if operation in ("method", "static") and not method_name:
            return {
                "success": False,
                "error": "Method name is required for method/static operations"
            }
        
        # Determine module from class name (default to db)
        module = self._guess_module(class_name)
        
        # Execute the call
        if operation == "constructor":
            result = self.invoker.invoke_constructor(class_name, module, params)
        elif operation == "method":
            result = self.invoker.invoke_method(handle, method_name, params)
        else:  # static
            result = self.invoker.invoke_static(class_name, method_name, module, params)
        
        return result.to_dict()
    
    def _guess_module(self, class_name: str) -> str:
        """
        Guess the module for a class based on the compatibility layer's class map.
        
        Args:
            class_name: Name of the class
            
        Returns:
            Module name (db, lay, tl, rdb, lib)
        """
        # Use the compatibility layer's comprehensive class-to-module mapping
        return self._compat.get_module_for_class(class_name)
    
    def create_object(self, class_name: str,
                      params: Optional[Dict[str, Any]] = None,
                      alias: Optional[str] = None) -> Dict[str, Any]:
        """
        Convenience method to create a new object.
        
        Args:
            class_name: Name of the class
            params: Constructor parameters
            alias: Optional alias for the handle
            
        Returns:
            Dictionary with creation result
        """
        result = self.call("constructor", class_name, params=params)
        
        # Set alias if provided and successful
        if result.get("success") and alias and "handle" in result:
            self.registry.set_alias(result["handle"], alias)
            result["alias"] = alias
        
        return result
    
    def invoke_on(self, handle: str, method_name: str,
                  params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Convenience method to invoke a method on an object.
        
        Args:
            handle: Handle ID or alias
            method_name: Name of the method
            params: Method parameters
            
        Returns:
            Dictionary with invocation result
        """
        # Get the object to determine class name
        obj = self.registry.get(handle)
        if obj is None:
            return {
                "success": False,
                "error": f"Handle not found: {handle}"
            }
        
        class_name = type(obj).__name__
        return self.call("method", class_name, method_name, handle, params)
    
    def check_available(self) -> Dict[str, Any]:
        """
        Check if KLayout API is available.
        
        Returns:
            Dictionary with availability status
        """
        available = self.invoker.check_klayout_available()
        return {
            "success": True,
            "klayout_available": available
        }
