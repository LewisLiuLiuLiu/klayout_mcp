"""KLayout MCP Server 开发智能体入口

This is the entry point for the long-running development agent that helps
build a local KLayout MCP Server.

Usage:
    # First run (Initializer Agent)
    python -m klayout_mcp_dev_agent.agent.main

    # Subsequent runs (Coding Agent, auto-resume session)
    python -m klayout_mcp_dev_agent.agent.main

    # Limit iterations
    python -m klayout_mcp_dev_agent.agent.main --max-iterations 5

    # Start fresh (clear session)
    python -m klayout_mcp_dev_agent.agent.main --fresh
"""

import asyncio
import argparse
import sys
from pathlib import Path

from .agent_loop import run_development_agent
from .session_manager import SessionManager


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="KLayout MCP Server Development Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Run with default settings
    python -m klayout_mcp_dev_agent.agent.main

    # Limit to 5 iterations
    python -m klayout_mcp_dev_agent.agent.main --max-iterations 5

    # Start fresh (clear previous session)
    python -m klayout_mcp_dev_agent.agent.main --fresh

    # Custom workspace
    python -m klayout_mcp_dev_agent.agent.main --workspace /path/to/project
        """
    )
    
    parser.add_argument(
        "--workspace",
        type=Path,
        default=Path("/mnt/d/iflowProject/project03_klayout_mcp/project03_klayout_mcp_try"),
        help="Path to the workspace directory (default: project root)"
    )
    
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=None,
        help="Maximum number of agent iterations (default: unlimited)"
    )
    
    parser.add_argument(
        "--auto-continue-delay",
        type=int,
        default=3,
        help="Delay in seconds between automatic iterations (default: 3)"
    )
    
    parser.add_argument(
        "--fresh",
        action="store_true",
        help="Start fresh by clearing the previous session"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        default=True,
        help="Enable verbose output (default: True)"
    )
    
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Disable verbose output"
    )
    
    return parser.parse_args()


async def main() -> int:
    """Main entry point for the development agent."""
    args = parse_args()
    
    # Validate workspace
    workspace = args.workspace.resolve()
    if not workspace.exists():
        print(f"Error: Workspace directory does not exist: {workspace}")
        return 1
    
    # Handle --fresh flag
    if args.fresh:
        print("Clearing previous session...")
        session_mgr = SessionManager(workspace)
        session_mgr.clear()
        print("Session cleared. Starting fresh.")
    
    # Determine verbosity
    verbose = args.verbose and not args.quiet
    
    # Print startup banner
    print("\n" + "=" * 60)
    print("  KLayout MCP Server Development Agent")
    print("=" * 60)
    print(f"  Workspace: {workspace}")
    print(f"  Max iterations: {args.max_iterations or 'unlimited'}")
    print(f"  Auto-continue delay: {args.auto_continue_delay}s")
    print(f"  Verbose: {verbose}")
    print("=" * 60 + "\n")
    
    try:
        await run_development_agent(
            workspace=workspace,
            max_iterations=args.max_iterations,
            auto_continue_delay=args.auto_continue_delay,
            verbose=verbose,
        )
        return 0
    except KeyboardInterrupt:
        print("\n\nInterrupted by user. Exiting...")
        return 130
    except Exception as e:
        print(f"\nError: {e}")
        if verbose:
            import traceback
            traceback.print_exc()
        return 1


def run() -> None:
    """Synchronous entry point."""
    sys.exit(asyncio.run(main()))


if __name__ == "__main__":
    run()
