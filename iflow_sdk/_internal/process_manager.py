"""iFlow process management.

This module handles automatic startup and management of iFlow CLI processes.
Each IFlowClient instance gets its own iFlow process.
"""

import asyncio
import logging
import platform
import shutil
import socket
import subprocess
import sys
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class IFlowNotInstalledError(Exception):
    """Raised when iFlow CLI is not installed."""
    pass


class IFlowProcessManager:
    """Manages the lifecycle of an iFlow CLI process.
    
    This class handles:
    - Detecting if iFlow is installed
    - Finding available ports
    - Starting iFlow with the ACP protocol
    - Cleanly shutting down the process
    """
    
    def __init__(self, start_port: int = 8090):
        """Initialize the process manager.
        
        Args:
            start_port: The port to start checking from (default: 8090)
        """
        self._process: Optional[asyncio.subprocess.Process] = None
        self._port: Optional[int] = None
        self._start_port = start_port
        self._iflow_path: Optional[str] = None
        
    @property
    def port(self) -> Optional[int]:
        """Get the port the iFlow process is running on."""
        return self._port
        
    @property
    def url(self) -> str:
        """Get the WebSocket URL for connecting to iFlow."""
        if not self._port:
            raise RuntimeError("iFlow process not started")
        return f"ws://localhost:{self._port}/acp"
        
    def _find_iflow(self) -> str:
        """Find the iFlow CLI executable.
        
        Returns:
            Path to the iFlow executable
            
        Raises:
            IFlowNotInstalledError: If iFlow is not found
        """
        # First check if it's in PATH
        if iflow_path := shutil.which("iflow"):
            logger.debug(f"Found iFlow at: {iflow_path}")
            return iflow_path
            
        # Check common installation locations
        locations = [
            Path.home() / ".npm-global/bin/iflow",
            Path("/usr/local/bin/iflow"),
            Path.home() / ".local/bin/iflow",
            Path.home() / "node_modules/.bin/iflow",
            Path.home() / ".yarn/bin/iflow",
            # Windows locations
            Path.home() / "AppData/Roaming/npm/iflow.cmd",
            Path("C:/Program Files/nodejs/iflow.cmd"),
        ]
        
        for path in locations:
            if path.exists() and path.is_file():
                logger.debug(f"Found iFlow at: {path}")
                return str(path)
                
        # Check if npm is installed
        npm_installed = shutil.which("npm") is not None
        node_installed = shutil.which("node") is not None
        
        system = platform.system().lower()
        
        # Build installation instructions based on platform
        if system == "windows":
            if not npm_installed and not node_installed:
                error_msg = "iFlow 需要 Node.js，但系统中未安装。\n\n"
                error_msg += "请先安装 Node.js: https://nodejs.org/\n"
                error_msg += "\n安装 Node.js 后，使用以下命令安装 iFlow:\n"
                error_msg += "  npm install -g @iflow-ai/iflow-cli@latest"
            else:
                error_msg = "未找到 iFlow CLI。请使用以下命令安装:\n"
                error_msg += "  npm install -g @iflow-ai/iflow-cli@latest"
        else:
            # Mac/Linux/Ubuntu
            error_msg = "未找到 iFlow CLI。请使用以下命令安装:\n\n"
            error_msg += "🍎 Mac/Linux/Ubuntu 用户:\n"
            error_msg += '  bash -c "$(curl -fsSL https://gitee.com/iflow-ai/iflow-cli/raw/main/install.sh)"\n\n'
            error_msg += "🪟 Windows 用户:\n"
            error_msg += "  npm install -g @iflow-ai/iflow-cli@latest"
            
        raise IFlowNotInstalledError(error_msg)
        
    def _is_port_available(self, port: int) -> bool:
        """Check if a port is available for use.
        
        Args:
            port: Port number to check
            
        Returns:
            True if the port is available, False otherwise
        """
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind(('localhost', port))
                return True
            except OSError:
                return False
                
    def _find_available_port(self, start_port: int = 8090, max_attempts: int = 100) -> int:
        """Find an available port starting from the given port.
        
        Args:
            start_port: Port to start searching from
            max_attempts: Maximum number of ports to try
            
        Returns:
            An available port number
            
        Raises:
            RuntimeError: If no available port is found
        """
        for i in range(max_attempts):
            port = start_port + i
            if self._is_port_available(port):
                logger.debug(f"Found available port: {port}")
                return port
                
        raise RuntimeError(f"No available port found in range {start_port}-{start_port + max_attempts}")
        
    async def start(self) -> str:
        """Start the iFlow process.
        
        Returns:
            The WebSocket URL to connect to
            
        Raises:
            IFlowNotInstalledError: If iFlow is not installed
            RuntimeError: If the process fails to start
        """
        if self._process and self._process.returncode is None:
            # Process already running
            return self.url
            
        # Find iFlow executable
        self._iflow_path = self._find_iflow()
        
        # Find an available port
        self._port = self._find_available_port(self._start_port)
        
        # Build command
        cmd = [
            self._iflow_path,
            "--experimental-acp",
            "--port", str(self._port)
        ]
        
        logger.info(f"Starting iFlow process: {' '.join(cmd)}")
        
        try:
            # Start the process
            self._process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                stdin=asyncio.subprocess.DEVNULL,  # No stdin needed
            )
            
            # Wait a bit to ensure the process starts successfully
            await asyncio.sleep(0.5)
            
            # Check if process is still running
            if self._process.returncode is not None:
                # Process exited, read stderr for error message
                if self._process.stderr:
                    stderr = await self._process.stderr.read()
                    error_msg = stderr.decode('utf-8', errors='ignore')
                    raise RuntimeError(f"iFlow process exited immediately: {error_msg}")
                else:
                    raise RuntimeError("iFlow process exited immediately")
                    
            logger.info(f"iFlow process started on port {self._port} (PID: {self._process.pid})")
            return self.url
            
        except Exception as e:
            self._process = None
            self._port = None
            raise RuntimeError(f"Failed to start iFlow process: {e}") from e
            
    async def stop(self) -> None:
        """Stop the iFlow process gracefully."""
        if not self._process:
            return
            
        if self._process.returncode is not None:
            # Process already stopped
            self._process = None
            self._port = None
            return
            
        logger.info(f"Stopping iFlow process (PID: {self._process.pid})")
        
        try:
            # Try graceful termination first
            self._process.terminate()
            
            # Wait up to 5 seconds for graceful shutdown
            try:
                await asyncio.wait_for(self._process.wait(), timeout=5.0)
                logger.info("iFlow process terminated gracefully")
            except asyncio.TimeoutError:
                # Force kill if graceful shutdown fails
                logger.warning("iFlow process did not terminate gracefully, forcing kill")
                self._process.kill()
                await self._process.wait()
                
        except ProcessLookupError:
            # Process already gone
            pass
        except Exception as e:
            logger.error(f"Error stopping iFlow process: {e}")
        finally:
            self._process = None
            self._port = None
            
    async def __aenter__(self) -> "IFlowProcessManager":
        """Async context manager entry."""
        await self.start()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.stop()