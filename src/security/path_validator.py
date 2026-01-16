"""
Path Validator - Validate file paths for security

This module provides file path validation to prevent directory traversal
and other path-based security issues.
"""

import os
import re
from pathlib import Path
from typing import List, Optional, Set
from dataclasses import dataclass


@dataclass
class ValidationResult:
    """Result of path validation."""
    valid: bool
    normalized_path: Optional[str]
    error: Optional[str] = None


class PathValidator:
    """
    Validates file paths against security rules.
    
    Features:
    - Directory traversal prevention
    - Whitelist-based access control
    - Symlink resolution
    - Extension filtering
    """
    
    # Dangerous path patterns
    DANGEROUS_PATTERNS = [
        r'\.\./',           # Parent directory
        r'\.\.\\',          # Parent directory (Windows)
        r'^~',              # Home directory expansion
        r'\$\{',            # Environment variable expansion
        r'\$\(',            # Command substitution
        r'^/etc/',          # System config
        r'^/proc/',         # Process info
        r'^/sys/',          # System info
        r'^/dev/',          # Device files
        r'^C:\\Windows',    # Windows system
        r'^C:\\Program',    # Windows programs
    ]
    
    # Default allowed extensions for read operations
    DEFAULT_READ_EXTENSIONS = {
        '.gds', '.gds2', '.oas', '.oasis', '.lef', '.def',
        '.dxf', '.cif', '.mag', '.lyp', '.lyt', '.rb', '.py',
        '.txt', '.json', '.xml', '.yaml', '.yml', '.md'
    }
    
    # Default allowed extensions for write operations
    DEFAULT_WRITE_EXTENSIONS = {
        '.gds', '.gds2', '.oas', '.oasis', '.lef', '.def',
        '.dxf', '.cif', '.png', '.svg', '.lyp', '.lyt',
        '.txt', '.json', '.xml', '.yaml', '.yml'
    }
    
    def __init__(self, 
                 allowed_read_dirs: Optional[List[str]] = None,
                 allowed_write_dirs: Optional[List[str]] = None,
                 allowed_read_extensions: Optional[Set[str]] = None,
                 allowed_write_extensions: Optional[Set[str]] = None):
        """
        Initialize the PathValidator.
        
        Args:
            allowed_read_dirs: List of directories allowed for reading
            allowed_write_dirs: List of directories allowed for writing
            allowed_read_extensions: Set of allowed extensions for reading
            allowed_write_extensions: Set of allowed extensions for writing
        """
        self.allowed_read_dirs = [Path(d).resolve() for d in (allowed_read_dirs or ['/tmp'])]
        self.allowed_write_dirs = [Path(d).resolve() for d in (allowed_write_dirs or ['/tmp'])]
        self.allowed_read_extensions = allowed_read_extensions or self.DEFAULT_READ_EXTENSIONS
        self.allowed_write_extensions = allowed_write_extensions or self.DEFAULT_WRITE_EXTENSIONS
        
        # Compile dangerous patterns
        self._dangerous_regex = [re.compile(p, re.IGNORECASE) for p in self.DANGEROUS_PATTERNS]
    
    def validate_read_path(self, path: str) -> ValidationResult:
        """
        Validate a path for read operations.
        
        Args:
            path: Path to validate
            
        Returns:
            ValidationResult with validation status
        """
        # Check for dangerous patterns
        danger_check = self._check_dangerous_patterns(path)
        if danger_check:
            return ValidationResult(valid=False, normalized_path=None, error=danger_check)
        
        # Normalize and resolve the path
        try:
            normalized = Path(path).resolve()
        except Exception as e:
            return ValidationResult(valid=False, normalized_path=None, 
                                   error=f"Invalid path: {str(e)}")
        
        # Check extension
        ext = normalized.suffix.lower()
        if ext and ext not in self.allowed_read_extensions:
            return ValidationResult(valid=False, normalized_path=None,
                                   error=f"Extension not allowed for reading: {ext}")
        
        # Check if path is under allowed directories
        if not self._is_under_allowed_dirs(normalized, self.allowed_read_dirs):
            return ValidationResult(valid=False, normalized_path=None,
                                   error="Path is not under allowed read directories")
        
        return ValidationResult(valid=True, normalized_path=str(normalized))
    
    def validate_write_path(self, path: str) -> ValidationResult:
        """
        Validate a path for write operations.
        
        Args:
            path: Path to validate
            
        Returns:
            ValidationResult with validation status
        """
        # Check for dangerous patterns
        danger_check = self._check_dangerous_patterns(path)
        if danger_check:
            return ValidationResult(valid=False, normalized_path=None, error=danger_check)
        
        # Normalize and resolve the path
        try:
            normalized = Path(path).resolve()
        except Exception as e:
            return ValidationResult(valid=False, normalized_path=None,
                                   error=f"Invalid path: {str(e)}")
        
        # Check extension
        ext = normalized.suffix.lower()
        if ext and ext not in self.allowed_write_extensions:
            return ValidationResult(valid=False, normalized_path=None,
                                   error=f"Extension not allowed for writing: {ext}")
        
        # Check if path is under allowed directories
        if not self._is_under_allowed_dirs(normalized, self.allowed_write_dirs):
            return ValidationResult(valid=False, normalized_path=None,
                                   error="Path is not under allowed write directories")
        
        return ValidationResult(valid=True, normalized_path=str(normalized))
    
    def _check_dangerous_patterns(self, path: str) -> Optional[str]:
        """Check path against dangerous patterns."""
        for regex in self._dangerous_regex:
            if regex.search(path):
                return f"Path contains dangerous pattern: {regex.pattern}"
        return None
    
    def _is_under_allowed_dirs(self, path: Path, allowed_dirs: List[Path]) -> bool:
        """Check if path is under any of the allowed directories."""
        for allowed_dir in allowed_dirs:
            try:
                path.relative_to(allowed_dir)
                return True
            except ValueError:
                continue
        return False
    
    def is_safe_path(self, path: str) -> bool:
        """
        Quick check if a path is safe (no dangerous patterns).
        
        Args:
            path: Path to check
            
        Returns:
            True if path appears safe
        """
        return self._check_dangerous_patterns(path) is None
    
    def normalize_path(self, path: str) -> str:
        """
        Normalize a path (resolve relative paths, symlinks).
        
        Args:
            path: Path to normalize
            
        Returns:
            Normalized absolute path
        """
        return str(Path(path).resolve())
    
    def add_allowed_read_dir(self, directory: str) -> None:
        """Add a directory to the allowed read list."""
        self.allowed_read_dirs.append(Path(directory).resolve())
    
    def add_allowed_write_dir(self, directory: str) -> None:
        """Add a directory to the allowed write list."""
        self.allowed_write_dirs.append(Path(directory).resolve())
