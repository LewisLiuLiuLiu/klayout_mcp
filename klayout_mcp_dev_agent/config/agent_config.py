"""Agent configuration for KLayout MCP Server development.

This module provides configuration options for the development agent,
including system prompts, approval modes, and security hooks.
"""

from pathlib import Path
from typing import Optional
import sys

# Add iflow_sdk to path if not already available
sdk_path = Path(__file__).parent.parent.parent / "iflow_sdk"
if sdk_path.exists() and str(sdk_path.parent) not in sys.path:
    sys.path.insert(0, str(sdk_path.parent))

from iflow_sdk import (
    IFlowOptions,
    ApprovalMode,
    SessionSettings,
    HookEventType,
    HookEventConfig,
    HookCommand,
)


# Base system prompt for the development agent
BASE_SYSTEM_PROMPT = """You are an expert Python developer building a KLayout MCP Server.
Your task is to implement code that enables AI agents to interact with KLayout's 2000+ APIs
through a lightweight MCP interface using only 4-6 meta-tools.

IMPORTANT - File Operations:
- To modify existing files: use the Edit tool
- To create new files: use the write_file tool

Key principles:
- Write clean, well-documented Python code
- Use type hints consistently (from typing import ...)
- Handle errors gracefully with try/except
- Follow the existing code style in the project
- Test your implementations before marking tasks complete
- Commit your changes with descriptive messages

The MCP Server architecture:
- api_index.json: Pre-built index of all KLayout APIs
- search_klayout_api: Searches the index by keyword
- describe_klayout_api: Returns detailed docs for one API
- call_klayout_api: Executes an API via reflection
- Handle registry: Manages Layout/Cell object references
"""

# Prompt suffix for initializer agent
INITIALIZER_PROMPT_SUFFIX = """
INITIALIZER MODE:
- Your first task is to analyze the project requirements
- Create a comprehensive klayout_mcp_task_list.json with all development tasks
- Set up the project directory structure
- Create klayout_mcp_dev_progress.txt
- Do NOT start implementing features yet - just plan
"""

# Prompt suffix for coding agent
CODING_PROMPT_SUFFIX = """
CODING MODE:
- Read klayout_mcp_dev_progress.txt to understand current state
- Select ONE pending task with all dependencies completed
- Implement the task fully with proper error handling
- Test the implementation
- Update task status in klayout_mcp_task_list.json
- Commit your changes with descriptive message
- Update klayout_mcp_dev_progress.txt with session notes
"""


def get_security_hooks() -> dict:
    """Get security hooks to restrict dangerous commands.
    
    Returns:
        Dictionary of hook configurations
    """
    # Security hook to block dangerous bash commands
    # This runs before each Bash tool use
    security_check_script = '''python3 -c "
import sys
cmd = ' '.join(sys.argv[1:])
blocked = ['rm -rf /', 'sudo rm', 'mkfs', ':(){', 'dd if=', '> /dev/sd']
if any(b in cmd for b in blocked):
    print(f'BLOCKED: {cmd}')
    sys.exit(1)
sys.exit(0)
"'''
    
    return {
        HookEventType.PRE_TOOL_USE: [
            HookEventConfig(
                matcher="Bash",
                hooks=[
                    HookCommand(
                        command=security_check_script,
                        timeout=5
                    )
                ]
            )
        ]
    }


def get_agent_options(
    workspace: Path,
    session_id: Optional[str] = None,
    session_type: str = "CODING"
) -> IFlowOptions:
    """Get IFlowOptions configured for the development agent.
    
    Args:
        workspace: The workspace directory for the project
        session_id: Optional session ID to resume from
        session_type: Either "INITIALIZER" or "CODING"
        
    Returns:
        Configured IFlowOptions instance
    """
    # Choose prompt suffix based on session type
    if session_type == "INITIALIZER":
        append_prompt = INITIALIZER_PROMPT_SUFFIX
    else:
        append_prompt = CODING_PROMPT_SUFFIX
    
    # Create session settings
    settings = SessionSettings(
        system_prompt=BASE_SYSTEM_PROMPT,
        append_system_prompt=append_prompt,
        max_turns=500,  # Allow long sessions
    )
    
    # Create options
    options = IFlowOptions(
        cwd=str(workspace),
        session_id=session_id,
        approval_mode=ApprovalMode.AUTO_EDIT,  # Auto-execute tools
        session_settings=settings,
        hooks=get_security_hooks(),
        timeout=300.0,  # 5 minute timeout for long operations
        log_level="INFO",
        auto_start_process=True,
    )
    
    return options


def get_sandbox_options(
    workspace: Path,
    session_id: Optional[str] = None,
) -> IFlowOptions:
    """Get IFlowOptions configured for sandbox/testing mode.
    
    This mode uses more restrictive settings suitable for testing.
    
    Args:
        workspace: The workspace directory for the project
        session_id: Optional session ID to resume from
        
    Returns:
        Configured IFlowOptions instance
    """
    settings = SessionSettings(
        system_prompt=BASE_SYSTEM_PROMPT,
        append_system_prompt="\nSANDBOX MODE: Be extra careful with file operations.",
        max_turns=100,
    )
    
    options = IFlowOptions(
        cwd=str(workspace),
        session_id=session_id,
        approval_mode=ApprovalMode.DEFAULT,  # Require confirmation
        session_settings=settings,
        hooks=get_security_hooks(),
        timeout=60.0,
        log_level="DEBUG",
        auto_start_process=True,
    )
    
    return options
