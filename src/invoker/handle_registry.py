"""
Handle Registry - Manage KLayout object references

This module provides lifecycle management for KLayout objects,
allowing them to be referenced by unique handles across API calls.

Supports objects from both 'pya' (KLayout GUI) and 'klayout.db' (standalone) modes.
"""

import uuid
import time
import weakref
import threading
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class HandleInfo:
    """Information about a registered handle."""
    handle_id: str
    obj_type: str
    module: str
    created_at: float
    last_accessed: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    alias: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "handle_id": self.handle_id,
            "obj_type": self.obj_type,
            "module": self.module,
            "created_at": datetime.fromtimestamp(self.created_at).isoformat(),
            "last_accessed": datetime.fromtimestamp(self.last_accessed).isoformat(),
            "age_seconds": time.time() - self.created_at,
            "alias": self.alias,
            "metadata": self.metadata
        }


class HandleRegistry:
    """
    Manages KLayout object references with handle-based access.
    
    Features:
    - Unique handle IDs for object references
    - Alias support for user-friendly names
    - Automatic expiration of unused handles
    - Thread-safe operations
    - Weak reference option for memory efficiency
    - Supports both pya and standalone klayout.db objects
    """
    
    def __init__(self, 
                 default_ttl: float = 3600.0,  # 1 hour default TTL
                 use_weakref: bool = False,
                 cleanup_interval: float = 300.0):  # 5 minutes
        """
        Initialize the HandleRegistry.
        
        Args:
            default_ttl: Default time-to-live for handles in seconds
            use_weakref: Whether to use weak references (objects may be GC'd)
            cleanup_interval: Interval for automatic cleanup in seconds
        """
        self._handles: Dict[str, Any] = {}
        self._handle_info: Dict[str, HandleInfo] = {}
        self._aliases: Dict[str, str] = {}  # alias -> handle_id
        self._default_ttl = default_ttl
        self._use_weakref = use_weakref
        self._cleanup_interval = cleanup_interval
        self._lock = threading.RLock()
        self._last_cleanup = time.time()
    
    def register(self, obj: Any, obj_type: str, 
                 module: str = "unknown",
                 metadata: Optional[Dict[str, Any]] = None,
                 alias: Optional[str] = None,
                 ttl: Optional[float] = None) -> str:
        """
        Register an object and return its handle ID.
        
        Args:
            obj: The object to register
            obj_type: Type name of the object (e.g., "Box", "Layout")
            module: Module the object belongs to (e.g., "db", "lay")
            metadata: Optional metadata to store with the handle
            alias: Optional alias for easier reference
            ttl: Time-to-live in seconds (None for default)
            
        Returns:
            Unique handle ID
        """
        with self._lock:
            # Generate unique handle ID
            short_uuid = uuid.uuid4().hex[:8]
            timestamp = int(time.time())
            handle_id = f"{obj_type.lower()}_{short_uuid}_{timestamp}"
            
            # Store object (optionally as weak reference)
            if self._use_weakref:
                try:
                    self._handles[handle_id] = weakref.ref(obj)
                except TypeError:
                    # Object doesn't support weak references
                    self._handles[handle_id] = obj
            else:
                self._handles[handle_id] = obj
            
            # Store handle info
            now = time.time()
            self._handle_info[handle_id] = HandleInfo(
                handle_id=handle_id,
                obj_type=obj_type,
                module=module,
                created_at=now,
                last_accessed=now,
                metadata=metadata or {},
                alias=alias
            )
            
            # Register alias if provided
            if alias:
                self._aliases[alias] = handle_id
            
            # Periodic cleanup
            self._maybe_cleanup()
            
            return handle_id
    
    def get(self, handle_or_alias: str) -> Optional[Any]:
        """
        Get an object by its handle ID or alias.
        
        Args:
            handle_or_alias: Handle ID or alias
            
        Returns:
            The registered object or None if not found/expired
        """
        with self._lock:
            # Resolve alias
            handle_id = self._aliases.get(handle_or_alias, handle_or_alias)
            
            if handle_id not in self._handles:
                return None
            
            obj = self._handles[handle_id]
            
            # Handle weak reference
            if self._use_weakref and isinstance(obj, weakref.ref):
                obj = obj()
                if obj is None:
                    # Object was garbage collected
                    self._remove_handle(handle_id)
                    return None
            
            # Update last accessed time
            if handle_id in self._handle_info:
                self._handle_info[handle_id].last_accessed = time.time()
            
            return obj
    
    def release(self, handle_or_alias: str) -> bool:
        """
        Release a handle and its associated object.
        
        Args:
            handle_or_alias: Handle ID or alias
            
        Returns:
            True if handle was released, False if not found
        """
        with self._lock:
            # Resolve alias
            handle_id = self._aliases.get(handle_or_alias, handle_or_alias)
            
            if handle_id not in self._handles:
                return False
            
            self._remove_handle(handle_id)
            return True
    
    def _remove_handle(self, handle_id: str) -> None:
        """Remove a handle and its associated data."""
        # Remove from handles
        self._handles.pop(handle_id, None)
        
        # Remove handle info and alias
        info = self._handle_info.pop(handle_id, None)
        if info and info.alias:
            self._aliases.pop(info.alias, None)
    
    def release_all(self, filter_type: Optional[str] = None) -> int:
        """
        Release all handles, optionally filtered by type.
        
        Args:
            filter_type: Only release handles of this type
            
        Returns:
            Number of handles released
        """
        with self._lock:
            if filter_type:
                handles_to_release = [
                    h for h, info in self._handle_info.items()
                    if info.obj_type == filter_type
                ]
            else:
                handles_to_release = list(self._handles.keys())
            
            for handle_id in handles_to_release:
                self._remove_handle(handle_id)
            
            return len(handles_to_release)
    
    def set_alias(self, handle_id: str, alias: str) -> bool:
        """
        Set or update an alias for a handle.
        
        Args:
            handle_id: The handle ID
            alias: The alias to set
            
        Returns:
            True if successful, False if handle not found
        """
        with self._lock:
            if handle_id not in self._handles:
                return False
            
            # Remove old alias if exists
            info = self._handle_info.get(handle_id)
            if info and info.alias:
                self._aliases.pop(info.alias, None)
            
            # Set new alias
            self._aliases[alias] = handle_id
            if info:
                info.alias = alias
            
            return True
    
    def get_info(self, handle_or_alias: str) -> Optional[HandleInfo]:
        """
        Get information about a handle.
        
        Args:
            handle_or_alias: Handle ID or alias
            
        Returns:
            HandleInfo or None if not found
        """
        with self._lock:
            handle_id = self._aliases.get(handle_or_alias, handle_or_alias)
            return self._handle_info.get(handle_id)
    
    def list_handles(self, filter_type: Optional[str] = None,
                     filter_module: Optional[str] = None) -> List[HandleInfo]:
        """
        List all registered handles.
        
        Args:
            filter_type: Filter by object type
            filter_module: Filter by module
            
        Returns:
            List of HandleInfo objects
        """
        with self._lock:
            results = []
            for info in self._handle_info.values():
                if filter_type and info.obj_type != filter_type:
                    continue
                if filter_module and info.module != filter_module:
                    continue
                results.append(info)
            return results
    
    def cleanup_expired(self, ttl: Optional[float] = None) -> int:
        """
        Remove handles that haven't been accessed within the TTL.
        
        Args:
            ttl: Time-to-live in seconds (None for default)
            
        Returns:
            Number of handles removed
        """
        with self._lock:
            ttl = ttl or self._default_ttl
            now = time.time()
            expired = []
            
            for handle_id, info in self._handle_info.items():
                if now - info.last_accessed > ttl:
                    expired.append(handle_id)
            
            for handle_id in expired:
                self._remove_handle(handle_id)
            
            return len(expired)
    
    def _maybe_cleanup(self) -> None:
        """Run cleanup if enough time has passed since last cleanup."""
        now = time.time()
        if now - self._last_cleanup > self._cleanup_interval:
            self.cleanup_expired()
            self._last_cleanup = now
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get registry statistics.
        
        Returns:
            Dictionary with statistics
        """
        with self._lock:
            type_counts: Dict[str, int] = {}
            module_counts: Dict[str, int] = {}
            
            for info in self._handle_info.values():
                type_counts[info.obj_type] = type_counts.get(info.obj_type, 0) + 1
                module_counts[info.module] = module_counts.get(info.module, 0) + 1
            
            return {
                "total_handles": len(self._handles),
                "total_aliases": len(self._aliases),
                "by_type": type_counts,
                "by_module": module_counts,
                "use_weakref": self._use_weakref,
                "default_ttl": self._default_ttl
            }
    
    def __len__(self) -> int:
        """Return number of registered handles."""
        return len(self._handles)
    
    def __contains__(self, handle_or_alias: str) -> bool:
        """Check if handle or alias exists."""
        with self._lock:
            handle_id = self._aliases.get(handle_or_alias, handle_or_alias)
            return handle_id in self._handles
    
    @staticmethod
    def is_klayout_object(obj: Any) -> bool:
        """
        Check if an object is a KLayout object.
        
        Supports both pya (KLayout GUI) and standalone klayout.db modes.
        
        Args:
            obj: Object to check
            
        Returns:
            True if the object is from KLayout modules
        """
        if obj is None:
            return False
        
        obj_module = type(obj).__module__
        
        # Check pya mode (inside KLayout GUI)
        if obj_module == 'pya':
            return True
        
        # Check standalone mode (klayout.db, klayout.lay, etc.)
        if obj_module.startswith('klayout.'):
            return True
        
        return False
    
    @staticmethod
    def get_object_type_name(obj: Any) -> str:
        """
        Get the type name for a KLayout object.
        
        Args:
            obj: KLayout object
            
        Returns:
            Type name (e.g., 'Box', 'Layout')
        """
        return type(obj).__name__
