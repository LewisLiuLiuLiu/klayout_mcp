"""Core agent loop for long-running development.

This module implements the main agent loop that orchestrates
multiple sessions of development work on the KLayout MCP Server.
"""

import asyncio
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime

# Add iflow_sdk to path if not already available
sdk_path = Path(__file__).parent.parent.parent / "iflow_sdk"
if sdk_path.exists() and str(sdk_path.parent) not in sys.path:
    sys.path.insert(0, str(sdk_path.parent))

from iflow_sdk import (
    IFlowClient,
    AssistantMessage,
    ToolCallMessage,
    TaskFinishMessage,
    ErrorMessage,
    PlanMessage,
)

from .session_manager import SessionManager
from .progress_tracker import ProgressTracker
from .prompts.initializer import get_initializer_prompt
from .prompts.coding import get_coding_prompt

# Import config with proper path handling
import sys
config_path = Path(__file__).parent.parent / "config"
if str(config_path.parent) not in sys.path:
    sys.path.insert(0, str(config_path.parent))
from config.agent_config import get_agent_options


async def run_development_agent(
    workspace: Path,
    max_iterations: Optional[int] = None,
    auto_continue_delay: int = 3,
    verbose: bool = True,
) -> None:
    """Run the long-running development agent.
    
    This function orchestrates multiple agent sessions, each working
    on development tasks for building the KLayout MCP Server.
    
    The agent uses two modes:
    1. INITIALIZER: First session sets up task list and structure
    2. CODING: Subsequent sessions implement one task at a time
    
    Args:
        workspace: The workspace directory for the project
        max_iterations: Maximum number of sessions (None for unlimited)
        auto_continue_delay: Seconds to wait between sessions
        verbose: Whether to print detailed output
    """
    workspace = Path(workspace)
    
    # Initialize managers
    session_mgr = SessionManager(workspace)
    progress = ProgressTracker(workspace)
    
    iteration = 0
    is_first_run = not progress.task_list_exists()
    
    print("\n" + "=" * 70)
    print("  KLAYOUT MCP SERVER DEVELOPMENT AGENT")
    print("=" * 70)
    print(f"\nWorkspace: {workspace}")
    print(f"Max iterations: {max_iterations or 'Unlimited'}")
    
    if is_first_run:
        print("\nFirst run detected - will use INITIALIZER mode")
    else:
        print("\nContinuing existing project")
        progress.print_summary()
    
    print()
    
    while True:
        iteration += 1
        
        # Check max iterations
        if max_iterations and iteration > max_iterations:
            print(f"\nReached max iterations ({max_iterations})")
            print("To continue, run the script again without --max-iterations")
            break
        
        # Determine session type and get prompt
        if is_first_run:
            prompt = get_initializer_prompt(workspace)
            session_type = "INITIALIZER"
            is_first_run = False  # Only use initializer once
        else:
            prompt = get_coding_prompt(workspace, progress.get_summary())
            session_type = "CODING"
        
        # Print session header
        print_session_header(iteration, session_type)
        
        # Get agent options
        options = get_agent_options(
            workspace=workspace,
            session_id=session_mgr.get_session_id(),
            session_type=session_type
        )
        
        # Run single session
        try:
            async with IFlowClient(options) as client:
                status, session_id = await run_single_session(
                    client, prompt, progress, verbose
                )
                
                # Save session ID for next run
                if session_id:
                    session_mgr.save_session_id(session_id)
        
        except Exception as e:
            print(f"\nError during session: {e}")
            status = "error"
        
        # Handle session result
        if status == "error":
            print("\nSession encountered an error. Will retry with fresh session...")
            session_mgr.clear()  # Clear session to start fresh
            await asyncio.sleep(auto_continue_delay)
            continue
        
        # Check if all tasks are completed
        if progress.is_all_completed():
            print("\n" + "=" * 70)
            print("  ALL TASKS COMPLETED!")
            print("=" * 70)
            progress.print_summary()
            break
        
        # Auto-continue to next session
        print(f"\nAuto-continuing in {auto_continue_delay} seconds...")
        progress.print_summary()
        await asyncio.sleep(auto_continue_delay)
        
        # Small delay between sessions
        if max_iterations is None or iteration < max_iterations:
            print("\nPreparing next session...\n")
            await asyncio.sleep(1)
    
    # Final summary
    print("\n" + "=" * 70)
    print("  SESSION COMPLETE")
    print("=" * 70)
    print(f"\nWorkspace: {workspace}")
    progress.print_summary()
    print("\nDone!")


async def run_single_session(
    client: IFlowClient,
    prompt: str,
    progress: ProgressTracker,
    verbose: bool = True,
) -> tuple[str, Optional[str]]:
    """Run a single agent session.
    
    Args:
        client: The IFlowClient instance
        prompt: The prompt to send
        progress: Progress tracker instance
        verbose: Whether to print detailed output
        
    Returns:
        Tuple of (status, session_id) where status is:
        - "continue" if agent should continue working
        - "error" if an error occurred
    """
    print("Sending prompt to agent...\n")
    
    try:
        # Send the prompt
        await client.send_message(prompt)
        
        # Collect response
        response_text = []
        
        async for message in client.receive_messages():
            # Handle different message types
            if isinstance(message, AssistantMessage):
                if message.chunk.text:
                    if verbose:
                        print(message.chunk.text, end="", flush=True)
                    response_text.append(message.chunk.text)
                
                if message.chunk.thought and verbose:
                    # Show thinking (truncated)
                    thought = message.chunk.thought[:100]
                    print(f"\n[Thinking] {thought}...", flush=True)
            
            elif isinstance(message, ToolCallMessage):
                if verbose:
                    tool_name = message.tool_name or message.label
                    print(f"\n[Tool: {tool_name}]", flush=True)
                    if message.args:
                        args_str = str(message.args)
                        if len(args_str) > 200:
                            args_str = args_str[:200] + "..."
                        print(f"   Input: {args_str}", flush=True)
            
            elif isinstance(message, PlanMessage):
                if verbose:
                    print("\n[Plan Update]", flush=True)
                    for entry in message.entries[:5]:  # Show first 5
                        print(f"   - [{entry.status}] {entry.content[:50]}...", flush=True)
            
            elif isinstance(message, TaskFinishMessage):
                reason = message.stop_reason.value if message.stop_reason else "unknown"
                print(f"\n[Session Finished: {reason}]")
                break
            
            elif isinstance(message, ErrorMessage):
                print(f"\n[Error] {message.message}")
                if message.details:
                    print(f"   Details: {message.details}")
                return "error", client._session_id
        
        print("\n" + "-" * 70 + "\n")
        return "continue", client._session_id
    
    except Exception as e:
        print(f"\nError during agent session: {e}")
        return "error", getattr(client, '_session_id', None)


def print_session_header(session_num: int, session_type: str) -> None:
    """Print a formatted header for the session.
    
    Args:
        session_num: The session number
        session_type: Either "INITIALIZER" or "CODING"
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    print("\n" + "=" * 70)
    print(f"  SESSION {session_num}: {session_type}")
    print(f"  Started: {timestamp}")
    print("=" * 70)
    print()
