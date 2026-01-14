"""ACP (Agent Communication Protocol) implementation.

This module implements the ACP protocol v0.0.9 for communication
between the SDK and iFlow. It handles the JSON-RPC based messaging
and protocol flow.
"""

import asyncio
import json
import logging
from typing import Any, AsyncIterator, Callable, Dict, List, Optional, Union

from .._errors import AuthenticationError, JSONDecodeError, ProtocolError, TimeoutError
from .transport import WebSocketTransport
from .file_handler import FileSystemHandler
from ..types import ApprovalMode

logger = logging.getLogger(__name__)


class ACPProtocol:
    """ACP protocol handler for iFlow communication.

    Implements the Agent Communication Protocol (ACP) which
    defines the interaction between GUI applications and AI agents.

    The protocol uses JSON-RPC 2.0 for message formatting and supports:
    - Initialization and authentication
    - User message sending (session/prompt)
    - Assistant response streaming (session/update)
    - Tool call confirmations
    - Task notifications
    """

    PROTOCOL_VERSION = 1  # Now uses numeric version

    def __init__(self, transport: WebSocketTransport, file_handler: Optional[FileSystemHandler] = None, approval_mode: Optional[ApprovalMode] = None):
        """Initialize ACP protocol handler.

        Args:
            transport: WebSocket transport for communication
            file_handler: Optional file system handler for fs/* methods
            approval_mode: Approval mode (passed to iFlow via session_settings, not used by SDK)
        """
        self.transport = transport
        self._initialized = False
        self._authenticated = False
        self._request_id = 0
        self._pending_requests: Dict[int, asyncio.Future] = {}
        self._client_handlers: Dict[str, Callable] = {}
        self._file_handler = file_handler
        self._approval_mode = approval_mode  # Stored but not used for logic - iFlow controls this
        self._pending_permission_requests: Dict[int, asyncio.Future] = {}  # Track permission requests awaiting user response

    def _next_request_id(self) -> int:
        """Generate next request ID.

        Returns:
            Unique request ID
        """
        self._request_id += 1
        return self._request_id

    async def initialize(
        self,
        mcp_servers: List[Dict[str, Any]] = None,
        hooks: Dict[str, List[Dict[str, Any]]] = None,
        commands: List[Dict[str, str]] = None,
        agents: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Initialize the protocol connection.

        Performs the ACP initialization handshake:
        1. Wait for //ready signal
        2. Send initialize request with optional configs
        3. Process initialize response

        Args:
            mcp_servers: Optional list of MCP servers to configure
            hooks: Optional hook configurations for various events
            commands: Optional command configurations
            agents: Optional agent configurations

        Returns:
            Initialize response containing:
            - protocolVersion: Server's protocol version
            - authMethods: Available authentication methods
            - agentCapabilities: Agent capabilities

        Raises:
            ProtocolError: If initialization fails
            TimeoutError: If initialization times out
        """
        if self._initialized:
            logger.warning("Protocol already initialized")
            return {
                "protocolVersion": self.PROTOCOL_VERSION,
                "isAuthenticated": self._authenticated,
            }

        try:
            # Wait for //ready signal
            logger.info("Waiting for //ready signal...")
            async for message in self.transport.receive():
                if isinstance(message, str) and message.strip() == "//ready":
                    logger.info("Received //ready signal")
                    break
                elif isinstance(message, str) and message.startswith("//"):
                    # Log other control messages
                    logger.debug("Control message: %s", message)
                    continue

            # Send initialize request
            request_id = self._next_request_id()
            params = {
                "protocolVersion": self.PROTOCOL_VERSION,
                "clientCapabilities": {"fs": {"readTextFile": True, "writeTextFile": True}},
            }
            
            # Add optional configurations
            if mcp_servers:
                params["mcpServers"] = mcp_servers
            if hooks:
                params["hooks"] = hooks
            if commands:
                params["commands"] = commands
            if agents:
                params["agents"] = agents
            
            request = {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": "initialize",
                "params": params,
            }

            await self.transport.send(request)
            logger.info("Sent initialize request")

            # Wait for initialize response
            async for message in self.transport.receive():
                if isinstance(message, str) and message.startswith("//"):
                    # Skip control messages
                    logger.debug("Control message: %s", message)
                    continue

                try:
                    data = json.loads(message) if isinstance(message, str) else message

                    if data.get("id") == request_id:
                        if "error" in data:
                            raise ProtocolError(f"Initialize failed: {data['error']}")

                        result = data.get("result", {})
                        self._initialized = True
                        self._authenticated = result.get("isAuthenticated", False)

                        logger.info(
                            "Initialized with protocol version: %s, authenticated: %s",
                            result.get("protocolVersion"),
                            self._authenticated,
                        )

                        return result

                except json.JSONDecodeError as e:
                    logger.error("Failed to parse response: %s", e)
                    continue

            raise ProtocolError("Failed to receive initialize response")

        except Exception as e:
            logger.error("Initialization failed: %s", e)
            raise ProtocolError(f"Failed to initialize protocol: {e}") from e

    async def authenticate(
        self, 
        method_id: str = "iflow",
        method_info: Dict[str, str] = None
    ) -> None:
        """Perform authentication if required.

        This method should be called if initialize() indicates
        that authentication is needed (isAuthenticated = False).

        Args:
            method_id: Authentication method ID (e.g., "use_iflow_ak", "login_with_iflow")
            method_info: Optional authentication info dictionary with keys like apiKey, baseUrl, modelName

        Raises:
            AuthenticationError: If authentication fails
            TimeoutError: If authentication times out
        """
        if self._authenticated:
            logger.info("Already authenticated")
            return

        params = {"methodId": method_id}
        if method_info:
            params["methodInfo"] = method_info
            
        request_id = self._next_request_id()
        request = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": "authenticate",
            "params": params,
        }

        await self.transport.send(request)
        logger.info("Sent authenticate request with method: %s", method_id)

        # Wait for authentication response with timeout
        timeout = 10.0
        start_time = asyncio.get_event_loop().time()
        
        async for message in self.transport.receive():
            # Skip control messages
            if isinstance(message, str) and message.startswith("//"):
                logger.debug("Control message during auth: %s", message)
                continue
                
            try:
                data = json.loads(message) if isinstance(message, str) else message
                
                # Check if this is our authentication response
                if data.get("id") == request_id:
                    if "error" in data:
                        error_msg = data["error"].get("message", "Authentication failed")
                        raise AuthenticationError(f"Authentication failed: {error_msg}")
                    
                    # Verify the response contains the expected methodId
                    result = data.get("result", {})
                    response_method = result.get("methodId")
                    
                    if response_method == method_id:
                        self._authenticated = True
                        logger.info("Authentication successful with method: %s", response_method)
                        return
                    else:
                        logger.warning("Unexpected methodId in response: %s (expected %s)", 
                                     response_method, method_id)
                        # Still mark as authenticated if we got a response
                        self._authenticated = True
                        return
                        
            except json.JSONDecodeError as e:
                logger.error("Failed to parse authentication response: %s", e)
                continue
            
            # Check timeout
            if asyncio.get_event_loop().time() - start_time > timeout:
                raise TimeoutError(f"Authentication timeout after {timeout} seconds")
        
        raise AuthenticationError("Connection closed during authentication")

    async def create_session(
        self,
        cwd: str,
        mcp_servers: List[Dict[str, Any]] = None,
        hooks: Dict[str, List[Dict[str, Any]]] = None,
        commands: List[Dict[str, str]] = None,
        agents: List[Dict[str, Any]] = None,
        settings: Dict[str, Any] = None
    ) -> str:
        """Create a new session.

        Args:
            cwd: Working directory for the session
            mcp_servers: Optional list of MCP servers to configure
            hooks: Optional hook configurations for various events
            commands: Optional command configurations
            agents: Optional agent configurations
            settings: Optional session settings (allowed_tools, system_prompt, etc.)

        Returns:
            Session ID for use in subsequent requests

        Raises:
            ProtocolError: If not initialized or authenticated
        """
        if not self._initialized:
            raise ProtocolError("Protocol not initialized. Call initialize() first.")

        if not self._authenticated:
            raise ProtocolError("Not authenticated. Call authenticate() first.")

        params = {"cwd": cwd, "mcpServers": mcp_servers or []}
        
        # Add optional configurations
        if hooks:
            params["hooks"] = hooks
        if commands:
            params["commands"] = commands
        if agents:
            params["agents"] = agents
        if settings:
            params["settings"] = settings
            
        request_id = self._next_request_id()
        request = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": "session/new",
            "params": params,
        }

        await self.transport.send(request)
        logger.info("Sent session/new request with cwd: %s", cwd)

        # Wait for response directly from transport
        timeout = 10.0
        start_time = asyncio.get_event_loop().time()

        async for message in self.transport.receive():
            # Skip control messages
            if isinstance(message, str) and message.startswith("//"):
                logger.debug("Control message: %s", message)
                continue

            try:
                data = json.loads(message) if isinstance(message, str) else message

                if data.get("id") == request_id:
                    if "error" in data:
                        raise ProtocolError(f"session/new failed: {data['error']}")

                    result = data.get("result", {})
                    if "sessionId" in result:
                        logger.info("Created session: %s", result["sessionId"])
                        return result["sessionId"]
                    else:
                        logger.error("Invalid session/new response: %s", result)
                        return f"session_{request_id}"

            except json.JSONDecodeError as e:
                logger.error("Failed to parse response: %s", e)
                continue

            # Check timeout
            if asyncio.get_event_loop().time() - start_time > timeout:
                logger.warning("Session creation timed out, using fallback ID")
                return f"session_{request_id}"

        raise ProtocolError("Connection closed while waiting for session/new response")

    async def load_session(
        self,
        session_id: str,
        cwd: str,
        mcp_servers: List[Dict[str, Any]] = None,
        hooks: Dict[str, List[Dict[str, Any]]] = None,
        commands: List[Dict[str, str]] = None,
        agents: List[Dict[str, Any]] = None,
        settings: Dict[str, Any] = None
    ) -> None:
        """Load an existing session.

        Args:
            session_id: The session ID to load
            cwd: Working directory for the session
            mcp_servers: Optional list of MCP servers to configure
            hooks: Optional hook configurations for various events
            commands: Optional command configurations
            agents: Optional agent configurations
            settings: Optional session settings (allowed_tools, system_prompt, etc.)

        Returns:
            None (iFlow returns null for this operation)

        Raises:
            ProtocolError: If not initialized or authenticated

        Note:
            This method is part of the ACP protocol but is not yet supported
            by iFlow (loadSession capability is false). It's included for
            future compatibility.
        """
        if not self._initialized:
            raise ProtocolError("Protocol not initialized. Call initialize() first.")

        if not self._authenticated:
            raise ProtocolError("Not authenticated. Call authenticate() first.")

        params = {
            "sessionId": session_id,
            "cwd": cwd,
            "mcpServers": mcp_servers or []
        }

        # Add optional configurations
        if hooks:
            params["hooks"] = hooks
        if commands:
            params["commands"] = commands
        if agents:
            params["agents"] = agents
        if settings:
            params["settings"] = settings

        request_id = self._next_request_id()
        request = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": "session/load",
            "params": params,
        }

        await self.transport.send(request)
        logger.info("Sent session/load request for session: %s", session_id)

        # Wait for response
        timeout = 10.0
        start_time = asyncio.get_event_loop().time()

        async for message in self.transport.receive():
            # Skip control messages
            if isinstance(message, str) and message.startswith("//"):
                logger.debug("Control message: %s", message)
                continue

            try:
                data = json.loads(message) if isinstance(message, str) else message

                if data.get("id") == request_id:
                    if "error" in data:
                        raise ProtocolError(f"session/new failed: {data['error']}")

                    result = data.get("result", {})
                    if "sessionId" in result:
                        logger.info("Created session: %s", result["sessionId"])
                        return result["sessionId"]
                    else:
                        logger.error("Invalid session/new response: %s", result)
                        return f"session_{request_id}"

            except json.JSONDecodeError as e:
                logger.error("Failed to parse response: %s", e)
                continue

            # Check timeout
            if asyncio.get_event_loop().time() - start_time > timeout:
                raise TimeoutError("session/load request timed out")

        raise ProtocolError("Connection closed while waiting for session/load response")

    async def send_prompt(self, session_id: str, prompt: List[Dict[str, str]]) -> int:
        """Send a prompt to the session.

        Args:
            session_id: The session ID from create_session()
            prompt: List of content blocks (text or file references)

        Returns:
            Request ID for tracking the message

        Raises:
            ProtocolError: If not initialized or authenticated
        """
        if not self._initialized:
            raise ProtocolError("Protocol not initialized. Call initialize() first.")

        if not self._authenticated:
            raise ProtocolError("Not authenticated. Call authenticate() first.")

        request_id = self._next_request_id()
        request = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": "session/prompt",
            "params": {"sessionId": session_id, "prompt": prompt},
        }

        await self.transport.send(request)
        logger.info("Sent session/prompt with %d content blocks", len(prompt))

        return request_id

    async def cancel_session(self, session_id: str) -> None:
        """Cancel the current session.

        Args:
            session_id: The session to cancel

        Raises:
            ProtocolError: If session doesn't exist
        """
        request_id = self._next_request_id()
        request = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": "session/cancel",
            "params": {"sessionId": session_id},
        }

        await self.transport.send(request)
        logger.info("Sent session/cancel request")

    async def handle_messages(self) -> AsyncIterator[Dict[str, Any]]:
        """Handle incoming messages from the server.

        This method processes all incoming messages and yields
        client method calls that need to be handled by the SDK.

        Yields:
            Client method calls with their parameters
        """
        async for message in self.transport.receive():
            # Skip control messages
            if isinstance(message, str) and message.startswith("//"):
                logger.debug("Control message: %s", message)
                continue

            try:
                data = json.loads(message) if isinstance(message, str) else message

                # Handle method calls from server (client interface)
                if "method" in data and not "result" in data and not "error" in data:
                    yield await self._handle_client_method(data)

                # Handle responses to our requests
                elif "id" in data and ("result" in data or "error" in data):
                    await self._handle_response(data)

                    # Also yield completion notifications
                    if data.get("result") is not None:
                        yield {"type": "response", "id": data["id"], "result": data["result"]}
                if "error" in data:
                    yield await self._handle_client_error(data)
            except json.JSONDecodeError as e:
                logger.error("Failed to parse message: %s", e)
                raise JSONDecodeError("Invalid JSON received", message) from e

    async def _handle_client_method(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle client method calls from the server.

        Args:
            data: JSON-RPC request from server

        Returns:
            Processed client method call
        """
        method = data["method"]
        params = data.get("params", {})
        request_id = data.get("id")

        # Map method to response based on new protocol
        if method == "session/update":
            # Session update notification - no response needed for notifications
            update = params.get("update", {})
            update_type = update.get("sessionUpdate")

            # Map to internal message types
            result = {
                "type": "session_update",
                "sessionId": params.get("sessionId"),
                "update_type": update_type,
                "update": update,
            }

            # Add agentId if present (for SubAgent support)
            if "agentId" in update:
                result["agentId"] = update["agentId"]

            return result

        elif method == "session/request_permission":
            # Permission request from iFlow via ACP protocol
            # iFlow's CoreToolScheduler has already decided to request permission based on ApprovalMode
            # SDK's job is to forward this request to the user and send back their response
            tool_call = params.get("toolCall", {})
            options = params.get("options", [])
            session_id = params.get("sessionId")

            if request_id is not None:
                # Store the request_id and create a Future for the user's response
                response_future = asyncio.Future()
                self._pending_permission_requests[request_id] = response_future
                
                logger.info("Received permission request for tool '%s', waiting for user response", 
                           tool_call.get("title", "unknown"))
                
                # Return the permission request to the upper layer (client.py)
                # The response will be sent when user calls respond_to_permission_request()
                return {
                    "type": "permission_request", 
                    "request_id": request_id,
                    "session_id": session_id,
                    "tool_call": tool_call,
                    "options": options,
                    "needs_user_response": True
                }
            else:
                # No request_id means this is a notification, should not happen for permission requests
                logger.error("Permission request without request_id - cannot track response")
                return {"type": "error", "method": method, "error": "Permission request without request_id"}

        elif method == "fs/read_text_file":
            # File read request from iFlow
            file_path = params.get("path")
            session_id = params.get("sessionId")
            limit = params.get("limit")
            line = params.get("line")

            logger.info("fs/read_text_file request for: %s", file_path)

            # Check if file handler is registered
            if hasattr(self, "_file_handler") and self._file_handler:
                try:
                    content = await self._file_handler.read_file(
                        file_path, line=line, limit=limit
                    )
                    response = {"content": content}
                except Exception as e:
                    logger.error("Error reading file %s: %s", file_path, e)
                    if request_id is not None:
                        await self._send_error(request_id, -32603, str(e))
                    return {"type": "error", "method": method, "error": str(e)}
            else:
                # No file handler registered, return error
                error_msg = "File system access not configured"
                if request_id is not None:
                    await self._send_error(request_id, -32603, error_msg)
                return {"type": "error", "method": method, "error": error_msg}

            if request_id is not None:
                await self._send_response(request_id, response)

            return {"type": "file_read", "path": file_path, "response": response}

        elif method == "fs/write_text_file":
            # File write request from iFlow
            file_path = params.get("path")
            content = params.get("content")
            session_id = params.get("sessionId")

            logger.info("fs/write_text_file request for: %s", file_path)

            # Check if file handler is registered
            if hasattr(self, "_file_handler") and self._file_handler:
                try:
                    await self._file_handler.write_file(file_path, content)
                    response = {"success": True}
                except Exception as e:
                    logger.error("Error writing file %s: %s", file_path, e)
                    if request_id is not None:
                        await self._send_error(request_id, -32603, str(e))
                    return {"type": "error", "method": method, "error": str(e)}
            else:
                # No file handler registered, return error
                error_msg = "File system access not configured"
                if request_id is not None:
                    await self._send_error(request_id, -32603, error_msg)
                return {"type": "error", "method": method, "error": error_msg}

            if request_id is not None:
                await self._send_response(request_id, response)

            return {"type": "file_write", "path": file_path, "response": response}

        elif method == "pushToolCall":
            # Generate tool call ID
            tool_id = f"tool_{self._next_request_id()}"
            response = {"id": tool_id}

            if request_id is not None:
                await self._send_response(request_id, response)

            return {"type": "tool_call", "id": tool_id, "params": params}

        elif method == "updateToolCall":
            # Send acknowledgment
            if request_id is not None:
                await self._send_response(request_id, None)

            return {"type": "tool_update", "params": params}

        elif method == "notifyTaskFinish":
            # Send acknowledgment
            if request_id is not None:
                await self._send_response(request_id, None)

            return {"type": "task_finish", "params": params}

        else:
            logger.warning("Unknown method: %s", method)

            # Send error response for unknown methods
            if request_id is not None:
                await self._send_error(request_id, -32601, "Method not found")

            return {"type": "unknown", "method": method, "params": params}

    async def _handle_client_error(self, data: Dict[str, Any]) -> Dict[str, Any]:
        error = data.get("error", {})
        data = error.get("data", {})
        return {"type": "error", "code": error.get("code", -32603), "message": error.get("message", "Unknown error"), "details": data.get("details", None)}

    async def _send_response(self, request_id: int, result: Any) -> None:
        """Send a response to a server request.

        Args:
            request_id: ID of the request to respond to
            result: Result to send
        """
        response = {"jsonrpc": "2.0", "id": request_id, "result": result}
        await self.transport.send(response)

    async def _send_error(self, request_id: int, code: int, message: str) -> None:
        """Send an error response to a server request.

        Args:
            request_id: ID of the request to respond to
            code: Error code
            message: Error message
        """
        response = {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}
        await self.transport.send(response)

    async def respond_to_permission_request(
        self, 
        request_id: int, 
        option_id: str, 
        cancelled: bool = False
    ) -> None:
        """Respond to a permission request from the user.
        
        This method should be called by the client layer when the user
        makes a decision about a tool call confirmation.
        
        Args:
            request_id: The request ID from the permission request
            option_id: The selected option ID (e.g., "proceed_once", "proceed_always")
            cancelled: If True, the user cancelled/rejected the request
            
        Raises:
            ProtocolError: If the request_id is not found in pending requests
        """
        if request_id not in self._pending_permission_requests:
            raise ProtocolError(f"Unknown permission request ID: {request_id}")
        
        # Prepare the response
        if cancelled:
            response = {
                "outcome": {
                    "outcome": "cancelled"
                }
            }
        else:
            response = {
                "outcome": {
                    "outcome": "selected",
                    "optionId": option_id
                }
            }
        
        # Send the response to iFlow
        await self._send_response(request_id, response)
        
        # Resolve the future to unblock the message handler
        future = self._pending_permission_requests.pop(request_id)
        future.set_result(response)
        
        logger.info("Responded to permission request %d: %s (option: %s)", 
                   request_id, 
                   "cancelled" if cancelled else "approved",
                   option_id if not cancelled else "N/A")

    async def _handle_response(self, data: Dict[str, Any]) -> None:
        """Handle responses to our requests.

        Args:
            data: Response data
        """
        request_id = data.get("id")

        if request_id in self._pending_requests:
            future = self._pending_requests.pop(request_id)

            if "error" in data:
                future.set_exception(ProtocolError(f"Request failed: {data['error']}"))
            else:
                future.set_result(data.get("result"))
        else:
            logger.debug("Received response for unknown request ID: %s", request_id)
