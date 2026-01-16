"""
Sandbox - Security sandbox for API calls

This module provides a security sandbox that restricts dangerous API calls
and enforces resource limits.
"""

import time
import threading
from typing import Dict, Set, Optional, Any, Callable, List
from dataclasses import dataclass
from functools import wraps


@dataclass
class SandboxConfig:
    """Configuration for the sandbox."""
    # API restrictions
    blocked_classes: Set[str]
    blocked_methods: Set[str]
    blocked_patterns: List[str]
    
    # Resource limits
    max_memory_mb: int = 1024
    max_execution_time: float = 60.0  # seconds
    max_objects: int = 1000
    
    @classmethod
    def default(cls) -> 'SandboxConfig':
        """Create default sandbox configuration."""
        return cls(
            blocked_classes={
                'QProcess', 'QTcpSocket', 'QUdpSocket',
                'QNetworkAccessManager', 'QFile',
            },
            blocked_methods={
                'system', 'exec', 'eval', 'compile',
                '__import__', 'open', 'input',
            },
            blocked_patterns=[
                '*socket*', '*network*', '*process*',
                '*file*write*', '*file*delete*',
            ],
            max_memory_mb=1024,
            max_execution_time=60.0,
            max_objects=1000
        )


class SandboxViolation(Exception):
    """Raised when a sandbox rule is violated."""
    pass


class Sandbox:
    """
    Security sandbox for KLayout API calls.
    
    Features:
    - API call filtering (blocked classes/methods)
    - Execution time limits
    - Object count limits
    - Pattern-based blocking
    """
    
    def __init__(self, config: Optional[SandboxConfig] = None):
        """
        Initialize the Sandbox.
        
        Args:
            config: Sandbox configuration (uses defaults if None)
        """
        self.config = config or SandboxConfig.default()
        self._object_count = 0
        self._lock = threading.Lock()
        self._start_time: Optional[float] = None
    
    def check_api_call(self, class_name: str, method_name: str) -> bool:
        """
        Check if an API call is allowed.
        
        Args:
            class_name: Name of the class
            method_name: Name of the method
            
        Returns:
            True if the call is allowed
        """
        # Check blocked classes
        if class_name in self.config.blocked_classes:
            return False
        
        # Check blocked methods
        if method_name in self.config.blocked_methods:
            return False
        
        # Check patterns
        full_name = f"{class_name}.{method_name}".lower()
        for pattern in self.config.blocked_patterns:
            if self._match_pattern(pattern, full_name):
                return False
        
        return True
    
    def _match_pattern(self, pattern: str, text: str) -> bool:
        """Simple pattern matching with * wildcards."""
        pattern = pattern.lower()
        text = text.lower()
        
        if '*' not in pattern:
            return pattern in text
        
        parts = pattern.split('*')
        pos = 0
        for part in parts:
            if not part:
                continue
            idx = text.find(part, pos)
            if idx < 0:
                return False
            pos = idx + len(part)
        
        return True
    
    def check_object_limit(self) -> bool:
        """Check if object count limit is reached."""
        with self._lock:
            return self._object_count < self.config.max_objects
    
    def increment_object_count(self) -> None:
        """Increment the object counter."""
        with self._lock:
            self._object_count += 1
    
    def decrement_object_count(self) -> None:
        """Decrement the object counter."""
        with self._lock:
            if self._object_count > 0:
                self._object_count -= 1
    
    def reset_object_count(self) -> None:
        """Reset the object counter."""
        with self._lock:
            self._object_count = 0
    
    def start_execution(self) -> None:
        """Mark the start of a timed execution."""
        self._start_time = time.time()
    
    def check_execution_time(self) -> bool:
        """Check if execution time limit is exceeded."""
        if self._start_time is None:
            return True
        elapsed = time.time() - self._start_time
        return elapsed < self.config.max_execution_time
    
    def get_remaining_time(self) -> float:
        """Get remaining execution time in seconds."""
        if self._start_time is None:
            return self.config.max_execution_time
        elapsed = time.time() - self._start_time
        return max(0, self.config.max_execution_time - elapsed)
    
    def execute_safe(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute a function within the sandbox constraints.
        
        Args:
            func: Function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Function result
            
        Raises:
            SandboxViolation: If any sandbox rule is violated
        """
        # Check object limit
        if not self.check_object_limit():
            raise SandboxViolation(
                f"Object limit exceeded: {self._object_count} >= {self.config.max_objects}"
            )
        
        # Start timing
        self.start_execution()
        
        try:
            result = func(*args, **kwargs)
            
            # Check time after execution
            if not self.check_execution_time():
                raise SandboxViolation(
                    f"Execution time exceeded: {self.config.max_execution_time}s"
                )
            
            return result
            
        except SandboxViolation:
            raise
        except Exception as e:
            # Re-raise other exceptions
            raise
    
    def sandboxed(self, func: Callable) -> Callable:
        """
        Decorator to run a function in the sandbox.
        
        Args:
            func: Function to wrap
            
        Returns:
            Wrapped function
        """
        @wraps(func)
        def wrapper(*args, **kwargs):
            return self.execute_safe(func, *args, **kwargs)
        return wrapper
    
    def validate_call(self, class_name: str, method_name: str) -> None:
        """
        Validate an API call, raising if blocked.
        
        Args:
            class_name: Class name
            method_name: Method name
            
        Raises:
            SandboxViolation: If the call is blocked
        """
        if not self.check_api_call(class_name, method_name):
            raise SandboxViolation(
                f"API call blocked: {class_name}.{method_name}"
            )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get sandbox statistics."""
        return {
            "object_count": self._object_count,
            "max_objects": self.config.max_objects,
            "max_execution_time": self.config.max_execution_time,
            "blocked_classes": len(self.config.blocked_classes),
            "blocked_methods": len(self.config.blocked_methods),
            "blocked_patterns": len(self.config.blocked_patterns),
        }
    
    def add_blocked_class(self, class_name: str) -> None:
        """Add a class to the blocked list."""
        self.config.blocked_classes.add(class_name)
    
    def add_blocked_method(self, method_name: str) -> None:
        """Add a method to the blocked list."""
        self.config.blocked_methods.add(method_name)
    
    def add_blocked_pattern(self, pattern: str) -> None:
        """Add a pattern to the blocked list."""
        self.config.blocked_patterns.append(pattern)
