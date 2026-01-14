"""Type definitions for iFlow SDK.

This module contains all type definitions used throughout the SDK,
including message types, configuration options, and protocol structures.
"""

import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Union

# Protocol version
PROTOCOL_VERSION = 1  # WebSocket ACP v1


# Enums
class ToolCallStatus(str, Enum):
    """Status of a tool call."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    # Legacy aliases for backward compatibility
    RUNNING = "in_progress"
    FINISHED = "completed"
    ERROR = "failed"


class ToolCallConfirmationOutcome(str, Enum):
    """Outcome of a tool call confirmation request.
    
    Maps to iFlow's permission option IDs:
    - proceed_once: Allow this specific tool call once
    - proceed_always: Always allow this type of tool
    - proceed_always_server: Always allow this MCP server
    - proceed_always_tool: Always allow this specific MCP tool
    - cancel: Reject/cancel the tool call
    """

    PROCEED_ONCE = "proceed_once"  # iFlow's standard option
    PROCEED_ALWAYS = "proceed_always"  # Always allow this tool type
    PROCEED_ALWAYS_SERVER = "proceed_always_server"  # Always allow this MCP server
    PROCEED_ALWAYS_TOOL = "proceed_always_tool"  # Always allow this MCP tool
    CANCEL = "cancel"  # Reject the tool call
    
    # Legacy aliases for backward compatibility
    ALLOW = "proceed_once"
    ALWAYS_ALLOW = "proceed_always"
    ALWAYS_ALLOW_MCP_SERVER = "proceed_always_server"
    ALWAYS_ALLOW_TOOL = "proceed_always_tool"
    REJECT = "cancel"


class ApprovalMode(str, Enum):
    """Approval mode for tool execution (iFlow specific).
    
    This controls how iFlow handles tool call permissions:
    - DEFAULT: Request user confirmation for each tool call via ACP protocol
    - AUTO_EDIT: Automatically execute all tools without confirmation
    - YOLO: Automatically execute all tools, auto-fallback on errors
    - PLAN: Only allow read-only tools, block write operations
    
    Note: The SDK passes this mode to iFlow via session_settings.permission_mode.
    iFlow's CoreToolScheduler decides whether to call requestPermission() based on this mode.
    """

    DEFAULT = "default"      # Request confirmation for each tool (calls requestPermission)
    AUTO_EDIT = "smart"   # Auto-execute all tools (no requestPermission)
    YOLO = "yolo"            # Auto-execute with auto-fallback
    PLAN = "plan"            # Only allow read-only tools


class HookEventType(str, Enum):
    """Hook event types for various lifecycle events."""

    PRE_TOOL_USE = "PreToolUse"
    POST_TOOL_USE = "PostToolUse"
    STOP = "Stop"
    SUBAGENT_STOP = "SubagentStop"
    SET_UP_ENVIRONMENT = "SetUpEnvironment"


class StopReason(str, Enum):
    """Reason for stopping a prompt turn."""

    END_TURN = "end_turn"  # The language model finishes responding without requesting more tools
    MAX_TOKENS = "max_tokens"  # The maximum token limit is reached
    REFUSAL = "refusal"  # The Agent refuses to continue
    CANCELLED = "cancelled"  # The Client cancels the turn


# Message chunks
@dataclass
class UserMessageChunk:
    """A chunk of a user message."""

    content: Union[str, Path]

    def to_dict(self) -> Dict[str, str]:
        """Convert to protocol format."""
        if isinstance(self.content, str):
            return {"text": self.content}
        else:
            return {"path": str(self.content)}


@dataclass
class AssistantMessageChunk:
    """A chunk of an assistant message."""

    text: Optional[str] = None
    thought: Optional[str] = None

    def __post_init__(self):
        """Validate that either text or thought is provided."""
        if self.text is None and self.thought is None:
            raise ValueError("Either text or thought must be provided")
        if self.text is not None and self.thought is not None:
            raise ValueError("Only one of text or thought can be provided")


# Tool call types
@dataclass
class ToolCallConfirmation:
    """Tool call confirmation details."""

    type: Literal["edit", "execute", "mcp", "fetch", "other"]
    description: Optional[str] = None

    # Type-specific fields
    command: Optional[str] = None  # For execute
    root_command: Optional[str] = None  # For execute
    server_name: Optional[str] = None  # For mcp
    tool_name: Optional[str] = None  # For mcp
    tool_display_name: Optional[str] = None  # For mcp
    urls: Optional[List[str]] = None  # For fetch

    def to_dict(self) -> Dict[str, Any]:
        """Convert to protocol format."""
        result: Dict[str, Any] = {"type": self.type}

        if self.description:
            result["description"] = self.description

        if self.type == "execute":
            if self.command:
                result["command"] = self.command
            if self.root_command:
                result["rootCommand"] = self.root_command

        elif self.type == "mcp":
            if self.server_name:
                result["serverName"] = self.server_name
            if self.tool_name:
                result["toolName"] = self.tool_name
            if self.tool_display_name:
                result["toolDisplayName"] = self.tool_display_name

        elif self.type == "fetch":
            if self.urls:
                result["urls"] = self.urls

        return result


@dataclass
class ToolCallContent:
    """Tool call content."""

    type: Literal["markdown", "diff"]

    # Content fields
    markdown: Optional[str] = None  # For markdown
    path: Optional[str] = None  # For diff
    old_text: Optional[str] = None  # For diff
    new_text: Optional[str] = None  # For diff
    fileDiff: Optional[str] = None  # Deprecated field for diff

    def to_dict(self) -> Dict[str, Any]:
        """Convert to protocol format."""
        if self.type == "markdown":
            return {"type": "markdown", "markdown": self.markdown or ""}
        else:  # diff
            return {
                "type": "diff",
                "path": self.path or "",
                "oldText": self.old_text,
                "newText": self.new_text or "",
                "fileDiff": self.fileDiff or "",
            }


@dataclass
class ToolCallLocation:
    """File location for a tool call."""

    path: str
    line_start: Optional[int] = None
    line_end: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to protocol format."""
        result = {"path": self.path}
        if self.line_start is not None:
            result["lineStart"] = self.line_start
        if self.line_end is not None:
            result["lineEnd"] = self.line_end
        return result


@dataclass
class Icon:
    """Icon for tool calls."""

    type: Literal["emoji", "url"]
    value: str

    def to_dict(self) -> Dict[str, str]:
        """Convert to protocol format."""
        return {"type": self.type, "value": self.value}


@dataclass
class PermissionOption:
    """Permission option for tool call confirmation.
    
    Represents a single option that user can choose when confirming a tool call.
    """
    
    option_id: str  # The option ID (e.g., "proceed_once", "proceed_always")
    name: str  # Display name for the option
    kind: Literal["allow_once", "allow_always", "reject_once", "reject_always"]  # Option kind
    
    def to_dict(self) -> Dict[str, str]:
        """Convert to protocol format."""
        return {
            "optionId": self.option_id,
            "name": self.name,
            "kind": self.kind
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PermissionOption":
        """Create from protocol format."""
        return cls(
            option_id=data.get("optionId", ""),
            name=data.get("name", ""),
            kind=data.get("kind", "allow_once")
        )


@dataclass 
class ToolCall:
    """Tool call information from permission request."""
    
    tool_call_id: str
    status: ToolCallStatus
    title: str
    kind: Literal["read", "edit", "delete", "move", "search", "execute", "think", "fetch", "other"]
    content: Optional[List[ToolCallContent]] = None
    locations: Optional[List[ToolCallLocation]] = None
    raw_input: Optional[Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to protocol format."""
        result: Dict[str, Any] = {
            "toolCallId": self.tool_call_id,
            "status": self.status.value if isinstance(self.status, ToolCallStatus) else self.status,
            "title": self.title,
            "kind": self.kind
        }
        
        if self.content:
            result["content"] = [c.to_dict() for c in self.content]
        if self.locations:
            result["locations"] = [loc.to_dict() for loc in self.locations]
        if self.raw_input is not None:
            result["rawInput"] = self.raw_input
            
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ToolCall":
        """Create from protocol format."""
        content = None
        if data.get("content"):
            content = []
            for c in data["content"]:
                content_type = c.get("type")
                if content_type == "diff":
                    content.append(ToolCallContent(
                        type="diff",
                        path=c.get("path", ""),
                        old_text=c.get("oldText"),
                        new_text=c.get("newText", ""),
                        fileDiff=c.get("fileDiff")
                    ))
                else:
                    content.append(ToolCallContent(
                        type="markdown",
                        markdown=c.get("content", {}).get("text", "")
                    ))
        
        locations = None
        if data.get("locations"):
            locations = [
                ToolCallLocation(
                    path=loc.get("path", ""),
                    line_start=loc.get("lineStart"),
                    line_end=loc.get("lineEnd")
                )
                for loc in data["locations"]
            ]
        
        return cls(
            tool_call_id=data.get("toolCallId", ""),
            status=ToolCallStatus(data.get("status", "pending")),
            title=data.get("title", ""),
            kind=data.get("kind", "other"),
            content=content,
            locations=locations,
            raw_input=data.get("rawInput")
        )


# Agent Info
@dataclass
class AgentInfo:
    """Agent information parsed from iFlow's agentId.
    
    Contains core agent identification fields extracted from iFlow protocol.
    """
    
    # Core fields only
    agent_id: str                           # Raw agentId from iFlow ACP
    agent_index: Optional[int] = None       # Agent index within task
    task_id: Optional[str] = None           # Task/call ID from agentId  
    timestamp: Optional[int] = None         # Creation/event timestamp
    
    @classmethod
    def parse_agent_id(cls, agent_id: str) -> Dict[str, Optional[str]]:
        """Parse iFlow agentId format.
        
        iFlow generates agentIds in format: subagent-[taskId|instanceId]-{index}-{timestamp}
        
        Args:
            agent_id: The agent ID string from iFlow
            
        Returns:
            Dictionary with parsed components: task_id, agent_index, timestamp
            
        Examples:
            >>> AgentInfo.parse_agent_id("subagent-task-abc123-2-1735123456789")
            {'task_id': 'task-abc123', 'agent_index': '2', 'timestamp': '1735123456789'}
            
            >>> AgentInfo.parse_agent_id("subagent-instance-def456-0-1735123457000")
            {'task_id': 'instance-def456', 'agent_index': '0', 'timestamp': '1735123457000'}
        """
        if not agent_id or not isinstance(agent_id, str):
            return {'task_id': None, 'agent_index': None, 'timestamp': None}
            
        parts = agent_id.split('-')
        if len(parts) < 4 or parts[0] != 'subagent':
            return {'task_id': None, 'agent_index': None, 'timestamp': None}
            
        # Handle multi-part task IDs (e.g., "task-abc123" or "instance-def456")
        if len(parts) >= 5:
            task_id = '-'.join(parts[1:-2])  # Join middle parts as task_id
            agent_index = parts[-2]
            timestamp = parts[-1]
        else:
            task_id = parts[1] if parts[1] not in ['undefined', 'null'] else None
            agent_index = parts[2] if parts[2].isdigit() else None
            timestamp = parts[3] if parts[3].isdigit() else None
        
        return {
            'task_id': task_id,
            'agent_index': agent_index,
            'timestamp': timestamp
        }
    
    @classmethod
    def from_acp_data(cls, acp_data: Dict[str, Any]) -> Optional['AgentInfo']:
        """Create AgentInfo from ACP session_update data.
        
        Args:
            acp_data: Complete ACP message data containing agentId and other fields
            
        Returns:
            AgentInfo instance or None if no valid agent data found
        """
        agent_id = acp_data.get('agentId')
        if not agent_id:
            return None
            
        # Parse the agent ID
        parsed = cls.parse_agent_id(agent_id)
        
        return cls(
            agent_id=agent_id,
            agent_index=int(parsed['agent_index']) if parsed['agent_index'] and parsed['agent_index'].isdigit() else None,
            task_id=parsed['task_id'],
            timestamp=acp_data.get('timestamp')
        )
    
    @classmethod 
    def from_agent_id_only(cls, agent_id: str) -> Optional['AgentInfo']:
        """Create minimal AgentInfo from just the agent ID.
        
        This is useful when only the agentId is available (most common case).
        
        Args:
            agent_id: The agent ID string from iFlow
            
        Returns:
            AgentInfo instance with parsed fields from agentId
        """
        if not agent_id:
            return None
            
        parsed = cls.parse_agent_id(agent_id)
        if not any(parsed.values()):
            return None
            
        return cls(
            agent_id=agent_id,
            agent_index=int(parsed['agent_index']) if parsed['agent_index'] and parsed['agent_index'].isdigit() else None,
            task_id=parsed['task_id'],
            timestamp=int(parsed['timestamp']) if parsed['timestamp'] and parsed['timestamp'].isdigit() else None
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format, excluding None values.
        
        Returns:
            Dictionary representation with non-None fields only
        """
        return {k: v for k, v in self.__dict__.items() if v is not None}
    
    def __str__(self) -> str:
        """Human-readable string representation."""
        parts = [f"AgentInfo(id={self.agent_id}"]
        if self.agent_index is not None:
            parts.append(f"index={self.agent_index}")
        if self.task_id:
            parts.append(f"task={self.task_id}")
        if self.timestamp:
            parts.append(f"timestamp={self.timestamp}")
        return ", ".join(parts) + ")"


# Messages
@dataclass
class Message:
    """Base class for all messages."""

    type: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {"type": self.type}


@dataclass
class UserMessage(Message):
    """User message."""

    chunks: List[UserMessageChunk]

    def __init__(self, chunks: List[UserMessageChunk]):
        super().__init__(type="user")
        self.chunks = chunks

    def to_dict(self) -> Dict[str, Any]:
        """Convert to protocol format."""
        return {"type": self.type, "chunks": [chunk.to_dict() for chunk in self.chunks]}


@dataclass
class AssistantMessage(Message):
    """Assistant message."""

    chunk: AssistantMessageChunk
    agent_id: Optional[str] = None
    agent_info: Optional[AgentInfo] = None

    def __init__(self, chunk: AssistantMessageChunk, agent_id: Optional[str] = None, agent_info: Optional[AgentInfo] = None):
        super().__init__(type="assistant")
        self.chunk = chunk
        self.agent_id = agent_id
        self.agent_info = agent_info

    def to_dict(self) -> Dict[str, Any]:
        """Convert to protocol format."""
        result = {"type": self.type}
        if self.chunk.text is not None:
            result["text"] = self.chunk.text
        if self.chunk.thought is not None:
            result["thought"] = self.chunk.thought
        if self.agent_id is not None:
            result["agent_id"] = self.agent_id
        if self.agent_info is not None:
            result["agent_info"] = self.agent_info.to_dict()
        return result


@dataclass
class ToolCallMessage(Message):
    """Tool call message."""

    id: str
    label: str
    icon: Icon
    status: ToolCallStatus
    tool_name: Optional[str] = None  # New field added in protocol
    content: Optional[ToolCallContent] = None
    locations: Optional[List[ToolCallLocation]] = None
    confirmation: Optional[ToolCallConfirmation] = None
    agent_id: Optional[str] = None
    agent_info: Optional[AgentInfo] = None
    args: Optional[Dict[str, Any]] = None

    def __init__(
        self,
        id: str,
        label: str,
        icon: Icon,
        status: ToolCallStatus = ToolCallStatus.RUNNING,
        tool_name: Optional[str] = None,
        content: Optional[ToolCallContent] = None,
        locations: Optional[List[ToolCallLocation]] = None,
        confirmation: Optional[ToolCallConfirmation] = None,
        agent_id: Optional[str] = None,
        agent_info: Optional[AgentInfo] = None,
        args: Optional[Dict[str, Any]] = None
    ):
        super().__init__(type="tool_call")
        self.id = id
        self.label = label
        self.icon = icon
        self.status = status
        self.tool_name = tool_name
        self.content = content
        self.locations = locations
        self.confirmation = confirmation
        self.agent_id = agent_id
        self.agent_info = agent_info
        self.args = args


@dataclass
class ToolResultMessage(Message):
    id: str
    status: ToolCallStatus
    tool_name: Optional[str] = None  # New field added in protocol
    content: Optional[ToolCallContent] = None
    locations: Optional[List[ToolCallLocation]] = None
    confirmation: Optional[ToolCallConfirmation] = None
    agent_id: Optional[str] = None
    agent_info: Optional[AgentInfo] = None
    args: Optional[Dict[str, Any]] = None

    def __init__(
            self,
            id: str,
            status: ToolCallStatus = ToolCallStatus.COMPLETED,
            tool_name: Optional[str] = None,
            content: Optional[ToolCallContent] = None,
            locations: Optional[List[ToolCallLocation]] = None,
            confirmation: Optional[ToolCallConfirmation] = None,
            agent_id: Optional[str] = None,
            agent_info: Optional[AgentInfo] = None,
            args: Optional[Dict[str, Any]] = None
    ):
        super().__init__(type="tool_call")
        self.id = id
        self.status = status
        self.tool_name = tool_name
        self.content = content
        self.locations = locations
        self.confirmation = confirmation
        self.agent_id = agent_id
        self.agent_info = agent_info
        self.args = args


@dataclass
class ToolConfirmationRequestMessage(Message):
    """Tool confirmation request message.
    
    This message is sent when a tool requires user confirmation before execution.
    The user should respond by calling approve_tool_call() or reject_tool_call().
    """
    
    session_id: str
    tool_call: ToolCall
    options: List[PermissionOption]
    request_id: Optional[int] = None  # Internal request ID for tracking
    
    def __init__(
        self, 
        session_id: str, 
        tool_call: ToolCall, 
        options: List[PermissionOption],
        request_id: Optional[int] = None
    ):
        super().__init__(type="tool_confirmation_request")
        self.session_id = session_id
        self.tool_call = tool_call
        self.options = options
        self.request_id = request_id
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        result = {
            "type": self.type,
            "session_id": self.session_id,
            "tool_call": self.tool_call.to_dict(),
            "options": [opt.to_dict() for opt in self.options]
        }
        if self.request_id is not None:
            result["request_id"] = self.request_id
        return result


@dataclass
class PlanEntry:
    """Plan entry for task planning."""

    content: str
    priority: Literal["high", "medium", "low"]
    status: Literal["pending", "in_progress", "completed"]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to protocol format."""
        return {"content": self.content, "priority": self.priority, "status": self.status}


@dataclass
class PlanMessage(Message):
    """Plan update message."""

    entries: List[PlanEntry]

    def __init__(self, entries: List[PlanEntry]):
        super().__init__(type="plan")
        self.entries = entries

    def to_dict(self) -> Dict[str, Any]:
        """Convert to protocol format."""
        return {"type": self.type, "entries": [entry.to_dict() for entry in self.entries]}


@dataclass
class TaskFinishMessage(Message):
    """Task finish notification with stop reason."""

    stop_reason: Optional[StopReason] = None

    def __init__(self, stop_reason: Optional[StopReason] = None):
        super().__init__(type="task_finish")
        self.stop_reason = stop_reason

    def to_dict(self) -> Dict[str, Any]:
        """Convert to protocol format."""
        result = {"type": self.type}
        if self.stop_reason:
            result["stop_reason"] = self.stop_reason.value
        return result


@dataclass
class ErrorMessage(Message):
    """Error message."""

    code: int
    message: str
    details: Optional[Dict[str, Any]] = None

    def __init__(self, code: int, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(type="error")
        self.code = code
        self.message = message
        self.details = details


# Protocol configuration types
@dataclass 
class EnvVariable:
    """Environment variable for MCP servers."""
    
    name: str
    value: str
    
    def to_dict(self) -> Dict[str, str]:
        """Convert to protocol format."""
        return {"name": self.name, "value": self.value}


@dataclass
class McpServer:
    """MCP server configuration.

    Supports multiple transport types:
    - stdio: command, args, env, cwd
    - sse: url
    - http/streamable-http: httpUrl, headers
    - websocket: tcp
    """

    # Common fields
    name: Optional[str] = None
    description: Optional[str] = None
    type: Optional[Literal['stdio', 'sse', 'http', 'streamable-http']] = None
    timeout: Optional[int] = None
    trust: Optional[bool] = None

    # Stdio transport
    command: Optional[str] = None
    args: Optional[List[str]] = None
    env: Optional[List[EnvVariable]] = None
    cwd: Optional[str] = None

    # SSE transport
    url: Optional[str] = None

    # HTTP transport
    httpUrl: Optional[str] = None
    headers: Optional[Dict[str, str]] = None

    # WebSocket transport
    tcp: Optional[str] = None

    # Tool filtering
    includeTools: Optional[List[str]] = None
    excludeTools: Optional[List[str]] = None

    # Extension metadata
    extensionName: Optional[str] = None

    # OAuth configuration (placeholder for future implementation)
    oauth: Optional[Dict[str, Any]] = None
    authProviderType: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to protocol format."""
        result: Dict[str, Any] = {}

        # Add all non-None fields
        if self.name is not None:
            result["name"] = self.name
        if self.description is not None:
            result["description"] = self.description
        if self.type is not None:
            result["type"] = self.type
        if self.timeout is not None:
            result["timeout"] = self.timeout
        if self.trust is not None:
            result["trust"] = self.trust

        # Stdio transport
        if self.command is not None:
            result["command"] = self.command
        if self.args is not None:
            result["args"] = self.args
        if self.env is not None:
            result["env"] = [e.to_dict() for e in self.env]
        if self.cwd is not None:
            result["cwd"] = self.cwd

        # SSE transport
        if self.url is not None:
            result["url"] = self.url

        # HTTP transport
        if self.httpUrl is not None:
            result["httpUrl"] = self.httpUrl
        if self.headers is not None:
            result["headers"] = self.headers

        # WebSocket transport
        if self.tcp is not None:
            result["tcp"] = self.tcp

        # Tool filtering
        if self.includeTools is not None:
            result["includeTools"] = self.includeTools
        if self.excludeTools is not None:
            result["excludeTools"] = self.excludeTools

        # Extension metadata
        if self.extensionName is not None:
            result["extensionName"] = self.extensionName

        # OAuth
        if self.oauth is not None:
            result["oauth"] = self.oauth
        if self.authProviderType is not None:
            result["authProviderType"] = self.authProviderType

        return result


@dataclass
class HookCommand:
    """Hook command configuration."""
    
    type: Literal["command"] = "command"
    command: str = ""
    timeout: Optional[int] = None  # timeout in seconds
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to protocol format."""
        result = {"type": self.type, "command": self.command}
        if self.timeout is not None:
            result["timeout"] = self.timeout
        return result


@dataclass
class HookEventConfig:
    """Hook event configuration."""
    
    hooks: List[HookCommand]
    matcher: Optional[str] = None  # Pattern to match tool names (for PreToolUse/PostToolUse only)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to protocol format."""
        result = {"hooks": [h.to_dict() for h in self.hooks]}
        if self.matcher:
            result["matcher"] = self.matcher
        return result


@dataclass
class CommandConfig:
    """Command configuration."""
    
    name: str
    content: str
    
    def to_dict(self) -> Dict[str, str]:
        """Convert to protocol format."""
        return {"name": self.name, "content": self.content}


@dataclass
class CreateAgentConfig:
    """Agent creation configuration."""
    
    agentType: str
    whenToUse: str
    allowedTools: List[str]
    systemPrompt: str
    name: Optional[str] = None
    description: Optional[str] = None
    allowedMcps: Optional[List[str]] = None
    proactive: Optional[bool] = None
    location: Optional[Literal["global", "project"]] = None
    model: Optional[str] = None
    isInheritTools: Optional[bool] = None
    isInheritMcps: Optional[bool] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to protocol format."""
        result = {
            "agentType": self.agentType,
            "whenToUse": self.whenToUse,
            "allowedTools": self.allowedTools,
            "systemPrompt": self.systemPrompt
        }
        if self.name:
            result["name"] = self.name
        if self.description:
            result["description"] = self.description
        if self.allowedMcps:
            result["allowedMcps"] = self.allowedMcps
        if self.proactive is not None:
            result["proactive"] = self.proactive
        if self.location:
            result["location"] = self.location
        if self.model:
            result["model"] = self.model
        if self.isInheritTools is not None:
            result["isInheritTools"] = self.isInheritTools
        if self.isInheritMcps is not None:
            result["isInheritMcps"] = self.isInheritMcps
        return result


@dataclass
class SessionSettings:
    """Session settings configuration."""
    
    allowed_tools: Optional[List[str]] = None
    system_prompt: Optional[str] = None
    append_system_prompt: Optional[str] = None
    permission_mode: Optional[ApprovalMode] = None
    max_turns: Optional[int] = None
    disallowed_tools: Optional[List[str]] = None
    add_dirs: Optional[List[str]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to protocol format."""
        result = {}
        if self.allowed_tools:
            result["allowed_tools"] = self.allowed_tools
        if self.system_prompt:
            result["system_prompt"] = self.system_prompt
        if self.append_system_prompt:
            result["append_system_prompt"] = self.append_system_prompt
        if self.permission_mode:
            result["permission_mode"] = self.permission_mode.value
        if self.max_turns is not None:
            result["max_turns"] = self.max_turns
        if self.disallowed_tools:
            result["disallowed_tools"] = self.disallowed_tools
        if self.add_dirs:
            result["add_dirs"] = self.add_dirs
        return result


@dataclass
class AuthMethodInfo:
    """Authentication method information.
    
    This dataclass encapsulates authentication credentials and configuration
    for various authentication methods used by iFlow.
    
    Attributes:
        api_key: API key for authentication
        base_url: Base URL for the authentication service
        model_name: Model name for specific authentication schemes
    """
    
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model_name: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to protocol format for authentication requests.
        
        Returns a dictionary with non-None fields in camelCase format
        for ACP protocol compatibility.
        """
        result = {}
        
        # Map snake_case to camelCase for protocol compatibility
        field_mappings = {
            'api_key': 'apiKey',
            'base_url': 'baseUrl',
            'model_name': 'modelName',
        }
        
        for snake_name, camel_name in field_mappings.items():
            value = getattr(self, snake_name)
            if value is not None:
                result[camel_name] = value

            
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AuthMethodInfo":
        """Create AuthMethodInfo from dictionary.
        
        Handles both camelCase (protocol format) and snake_case (Python format) keys.
        
        Args:
            data: Dictionary containing authentication information
            
        Returns:
            AuthMethodInfo instance
        """
        # Handle camelCase to snake_case conversion
        field_mappings = {
            'apiKey': 'api_key',
            'baseUrl': 'base_url', 
            'modelName': 'model_name',
        }
        
        kwargs = {}
        
        for key, value in data.items():
            # Check if it's a known camelCase field
            if key in field_mappings:
                kwargs[field_mappings[key]] = value
            # Check if it's already in snake_case
            elif key in ['api_key', 'base_url', 'model_name']:
                kwargs[key] = value
        return cls(**kwargs)


# Configuration
@dataclass
class IFlowOptions:
    """Configuration options for iFlow SDK.

    Attributes:
        url: WebSocket URL for iFlow connection
        cwd: Working directory for CLI operations
        mcp_servers: List of MCP servers to configure (can be Dict or McpServer objects)
        hooks: Hook configurations for various events
        commands: Command configurations
        agents: Agent configurations
        session_settings: Session-specific settings
        approval_mode: How iFlow handles tool call permissions (DEFAULT/AUTO_EDIT/YOLO/PLAN)
        auto_approve_types: Tool types to auto-approve (legacy, not used with ApprovalMode)
        timeout: Connection and operation timeout in seconds
        log_level: Logging level
        metadata: Additional metadata to send with requests
        file_access: Enable file system access for iFlow
        file_allowed_dirs: List of directories iFlow can access
        file_read_only: If True, only allow read operations
        file_max_size: Maximum file size in bytes for read operations
        auto_start_process: Automatically start iFlow process if not running
        process_start_port: Starting port number for auto-started iFlow process
        auth_method_id: Authentication method ID (e.g., "use_iflow_ak")
        auth_method_info: Authentication method info (AuthMethodInfo object or dict)
    """

    url: str = "ws://localhost:8090/acp"
    cwd: str = field(default_factory=lambda: os.getcwd())
    mcp_servers: List[Union[Dict[str, Any], McpServer]] = field(default_factory=list)
    hooks: Optional[Dict[HookEventType, List[HookEventConfig]]] = None
    commands: Optional[List[CommandConfig]] = None
    agents: Optional[List[CreateAgentConfig]] = None
    session_settings: Optional[SessionSettings] = None
    approval_mode: ApprovalMode = ApprovalMode.YOLO
    auto_approve_types: List[str] = field(default_factory=lambda: ["edit", "fetch"])
    timeout: float = 30.0
    log_level: str = "INFO"
    metadata: Dict[str, Any] = field(default_factory=dict)
    file_access: bool = False  # Disabled by default for security
    file_allowed_dirs: Optional[List[str]] = None  # None = current directory only
    file_read_only: bool = False  # Allow writes by default when enabled
    file_max_size: int = 10 * 1024 * 1024  # 10MB default
    auto_start_process: bool = True  # Automatically start iFlow process
    process_start_port: int = 8090  # Starting port for iFlow process
    auth_method_id: Optional[str] = None  # Authentication method ID
    auth_method_info: Optional[Union[Dict[str, Any], AuthMethodInfo]] = None  # Authentication info
    session_id: Optional[str] = None

    def for_sandbox(
        self, sandbox_url: str = "wss://sandbox.iflow.ai/acp?peer=iflow"
    ) -> "IFlowOptions":
        """Create options for sandbox mode.

        Args:
            sandbox_url: Sandbox WebSocket URL

        Returns:
            New IFlowOptions configured for sandbox
        """
        return IFlowOptions(
            url=sandbox_url,
            permission_mode=self.permission_mode,
            auto_approve_types=self.auto_approve_types.copy(),
            timeout=self.timeout,
            log_level=self.log_level,
            metadata=self.metadata.copy(),
        )
