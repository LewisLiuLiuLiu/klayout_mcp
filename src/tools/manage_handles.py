"""
Manage Handles Tool - Manage object handles

This tool provides handle management functionality for the MCP server.
"""

from typing import Optional, Dict, Any, List

from ..invoker.handle_registry import HandleRegistry


class ManageHandlesTool:
    """
    Tool for managing object handles.
    
    Provides listing, getting, releasing, and aliasing handles.
    """
    
    def __init__(self, registry: HandleRegistry):
        """
        Initialize the tool.
        
        Args:
            registry: HandleRegistry instance
        """
        self.registry = registry
    
    def manage(self, action: str,
               handle: Optional[str] = None,
               alias: Optional[str] = None,
               filter_type: Optional[str] = None,
               filter_module: Optional[str] = None) -> Dict[str, Any]:
        """
        Perform a handle management action.
        
        Args:
            action: Action to perform ("list", "get", "release", "release_all", "alias")
            handle: Handle ID (for get/release/alias actions)
            alias: Alias name (for alias action)
            filter_type: Type filter for list action
            filter_module: Module filter for list action
            
        Returns:
            Dictionary with action result
        """
        if action == "list":
            return self.list_handles(filter_type, filter_module)
        elif action == "get":
            if not handle:
                return {"success": False, "error": "Handle is required for 'get' action"}
            return self.get_handle(handle)
        elif action == "release":
            if not handle:
                return {"success": False, "error": "Handle is required for 'release' action"}
            return self.release_handle(handle)
        elif action == "release_all":
            return self.release_all(filter_type)
        elif action == "alias":
            if not handle or not alias:
                return {"success": False, "error": "Handle and alias are required for 'alias' action"}
            return self.set_alias(handle, alias)
        else:
            return {"success": False, "error": f"Unknown action: {action}"}
    
    def list_handles(self, filter_type: Optional[str] = None,
                     filter_module: Optional[str] = None) -> Dict[str, Any]:
        """
        List all registered handles.
        
        Args:
            filter_type: Filter by object type
            filter_module: Filter by module
            
        Returns:
            Dictionary with handle list
        """
        handles = self.registry.list_handles(filter_type, filter_module)
        
        return {
            "success": True,
            "handles": [h.to_dict() for h in handles],
            "total": len(handles),
            "filters": {
                "type": filter_type,
                "module": filter_module
            }
        }
    
    def get_handle(self, handle: str) -> Dict[str, Any]:
        """
        Get information about a specific handle.
        
        Args:
            handle: Handle ID or alias
            
        Returns:
            Dictionary with handle info
        """
        info = self.registry.get_info(handle)
        if not info:
            return {"success": False, "error": f"Handle not found: {handle}"}
        
        obj = self.registry.get(handle)
        obj_repr = str(obj) if obj else "N/A"
        
        return {
            "success": True,
            "handle": info.to_dict(),
            "object_repr": obj_repr[:200]  # Limit length
        }
    
    def release_handle(self, handle: str) -> Dict[str, Any]:
        """
        Release a specific handle.
        
        Args:
            handle: Handle ID or alias
            
        Returns:
            Dictionary with release result
        """
        released = self.registry.release(handle)
        return {
            "success": True,
            "released": released,
            "handle": handle
        }
    
    def release_all(self, filter_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Release all handles.
        
        Args:
            filter_type: Only release handles of this type
            
        Returns:
            Dictionary with release result
        """
        count = self.registry.release_all(filter_type)
        return {
            "success": True,
            "released_count": count,
            "filter_type": filter_type
        }
    
    def set_alias(self, handle: str, alias: str) -> Dict[str, Any]:
        """
        Set an alias for a handle.
        
        Args:
            handle: Handle ID
            alias: Alias to set
            
        Returns:
            Dictionary with alias result
        """
        success = self.registry.set_alias(handle, alias)
        if not success:
            return {"success": False, "error": f"Handle not found: {handle}"}
        
        return {
            "success": True,
            "handle": handle,
            "alias": alias
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get registry statistics.
        
        Returns:
            Dictionary with statistics
        """
        stats = self.registry.get_stats()
        return {
            "success": True,
            "stats": stats
        }
    
    def cleanup_expired(self) -> Dict[str, Any]:
        """
        Clean up expired handles.
        
        Returns:
            Dictionary with cleanup result
        """
        count = self.registry.cleanup_expired()
        return {
            "success": True,
            "cleaned_up": count
        }
