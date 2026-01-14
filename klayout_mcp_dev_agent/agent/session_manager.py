"""Session persistence management for long-running agent.

This module handles saving and restoring session IDs to enable
continuation of development work across multiple agent runs.
"""

import json
from pathlib import Path
from typing import Optional
from datetime import datetime


class SessionManager:
    """Manages session persistence for long-running development agent.
    
    The session ID is saved to a JSON file in the workspace directory,
    allowing the agent to resume from where it left off in previous runs.
    """
    
    def __init__(self, workspace: Path):
        """Initialize session manager.
        
        Args:
            workspace: The workspace directory for the project
        """
        self.workspace = Path(workspace)
        self.session_file = self.workspace / ".klayout_dev_session.json"
    
    def get_session_id(self) -> Optional[str]:
        """Get the session ID from the last run.
        
        Returns:
            The session ID if available, None otherwise
        """
        if not self.session_file.exists():
            return None
        
        try:
            data = json.loads(self.session_file.read_text(encoding='utf-8'))
            return data.get("session_id")
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Could not read session file: {e}")
            return None
    
    def save_session_id(self, session_id: str) -> None:
        """Save the session ID for next run.
        
        Args:
            session_id: The session ID to save
        """
        if session_id is None:
            return
        
        data = {
            "session_id": session_id,
            "workspace": str(self.workspace),
            "last_updated": datetime.now().isoformat()
        }
        
        try:
            self.session_file.write_text(
                json.dumps(data, indent=2),
                encoding='utf-8'
            )
        except IOError as e:
            print(f"Warning: Could not save session file: {e}")
    
    def clear(self) -> None:
        """Clear the saved session, forcing a fresh start on next run."""
        if self.session_file.exists():
            try:
                self.session_file.unlink()
                print("Session cleared. Next run will start fresh.")
            except IOError as e:
                print(f"Warning: Could not clear session file: {e}")
    
    def get_session_info(self) -> Optional[dict]:
        """Get full session information.
        
        Returns:
            Dictionary with session info or None
        """
        if not self.session_file.exists():
            return None
        
        try:
            return json.loads(self.session_file.read_text(encoding='utf-8'))
        except (json.JSONDecodeError, IOError):
            return None
