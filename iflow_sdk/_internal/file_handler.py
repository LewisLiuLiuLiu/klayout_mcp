"""File system handler for ACP protocol.

This module handles file system requests from iFlow, including
reading and writing text files with proper permission control.
"""

import asyncio
import logging
import os
from pathlib import Path
from typing import List, Optional, Set

logger = logging.getLogger(__name__)


class FileSystemHandler:
    """Handles file system operations for the ACP protocol.
    
    This class implements the fs/read_text_file and fs/write_text_file
    methods that iFlow can call to access the local file system.
    
    Security features:
    - Allowed directories whitelist
    - Path traversal prevention
    - File size limits
    - Read-only mode option
    """
    
    def __init__(
        self,
        allowed_dirs: Optional[List[str]] = None,
        read_only: bool = False,
        max_file_size: int = 10 * 1024 * 1024,  # 10MB default
    ):
        """Initialize file system handler.
        
        Args:
            allowed_dirs: List of directories that can be accessed.
                         If None, defaults to current working directory.
            read_only: If True, only allow read operations
            max_file_size: Maximum file size in bytes for read operations
        """
        self.read_only = read_only
        self.max_file_size = max_file_size
        
        # Set up allowed directories
        if allowed_dirs is None:
            # Default to current working directory
            self.allowed_dirs = {Path.cwd().resolve()}
        else:
            # Resolve all paths to absolute
            self.allowed_dirs = {Path(d).resolve() for d in allowed_dirs}
        
        logger.info("FileSystemHandler initialized with %d allowed directories", 
                   len(self.allowed_dirs))
        for d in self.allowed_dirs:
            logger.debug("  Allowed: %s", d)
    
    def _is_path_allowed(self, file_path: str) -> bool:
        """Check if a file path is within allowed directories.
        
        Args:
            file_path: Path to check
            
        Returns:
            True if path is allowed, False otherwise
        """
        try:
            # Resolve to absolute path
            abs_path = Path(file_path).resolve()
            
            # Check if it's under any allowed directory
            for allowed_dir in self.allowed_dirs:
                try:
                    # Check if abs_path is relative to allowed_dir
                    abs_path.relative_to(allowed_dir)
                    return True
                except ValueError:
                    # Not under this directory
                    continue
            
            logger.warning("Path not in allowed directories: %s", abs_path)
            return False
            
        except Exception as e:
            logger.error("Error checking path: %s", e)
            return False
    
    async def read_file(
        self,
        file_path: str,
        line: Optional[int] = None,
        limit: Optional[int] = None
    ) -> str:
        """Read a text file.
        
        Args:
            file_path: Path to the file to read
            line: Optional starting line number (1-based)
            limit: Optional maximum number of lines to read
            
        Returns:
            File content as string
            
        Raises:
            PermissionError: If path is not allowed
            FileNotFoundError: If file doesn't exist
            ValueError: If file is too large
        """
        # Check if path is allowed
        if not self._is_path_allowed(file_path):
            raise PermissionError(f"Access denied: {file_path}")
        
        abs_path = Path(file_path).resolve()
        
        # Check if file exists
        if not abs_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        if not abs_path.is_file():
            raise ValueError(f"Not a file: {file_path}")
        
        # Check file size
        file_size = abs_path.stat().st_size
        if file_size > self.max_file_size:
            raise ValueError(
                f"File too large: {file_size} bytes (max: {self.max_file_size})"
            )
        
        # Read the file
        try:
            with open(abs_path, 'r', encoding='utf-8') as f:
                if line is not None or limit is not None:
                    # Read specific lines
                    lines = f.readlines()
                    
                    # Adjust to 0-based indexing
                    start_line = (line - 1) if line else 0
                    end_line = start_line + limit if limit else len(lines)
                    
                    # Ensure bounds
                    start_line = max(0, start_line)
                    end_line = min(len(lines), end_line)
                    
                    return ''.join(lines[start_line:end_line])
                else:
                    # Read entire file
                    return f.read()
                    
        except UnicodeDecodeError:
            # Try with different encoding
            try:
                with open(abs_path, 'r', encoding='latin-1') as f:
                    return f.read()
            except Exception as e:
                raise ValueError(f"Failed to decode file: {e}")
        except Exception as e:
            raise IOError(f"Failed to read file: {e}")
    
    async def write_file(self, file_path: str, content: str) -> None:
        """Write content to a text file.
        
        Args:
            file_path: Path to the file to write
            content: Content to write
            
        Raises:
            PermissionError: If path is not allowed or in read-only mode
            IOError: If write fails
        """
        # Check if read-only mode
        if self.read_only:
            raise PermissionError("File system is in read-only mode")
        
        # Check if path is allowed
        if not self._is_path_allowed(file_path):
            raise PermissionError(f"Access denied: {file_path}")
        
        abs_path = Path(file_path).resolve()
        
        # Create parent directories if needed
        abs_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write the file
        try:
            with open(abs_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.info("Wrote %d bytes to %s", len(content), file_path)
            
        except Exception as e:
            raise IOError(f"Failed to write file: {e}")
    
    def add_allowed_directory(self, directory: str) -> None:
        """Add a directory to the allowed list.
        
        Args:
            directory: Directory path to add
        """
        abs_dir = Path(directory).resolve()
        if not abs_dir.exists():
            raise ValueError(f"Directory does not exist: {directory}")
        if not abs_dir.is_dir():
            raise ValueError(f"Not a directory: {directory}")
        
        self.allowed_dirs.add(abs_dir)
        logger.info("Added allowed directory: %s", abs_dir)
    
    def remove_allowed_directory(self, directory: str) -> None:
        """Remove a directory from the allowed list.
        
        Args:
            directory: Directory path to remove
        """
        abs_dir = Path(directory).resolve()
        self.allowed_dirs.discard(abs_dir)
        logger.info("Removed allowed directory: %s", abs_dir)