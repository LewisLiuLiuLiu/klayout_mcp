"""Development task progress tracking.

This module tracks the progress of development tasks for building
the KLayout MCP Server, using a JSON task list file.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from enum import Enum
from datetime import datetime


class TaskStatus(str, Enum):
    """Status of a development task."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


@dataclass
class DevTask:
    """A development task for building the MCP Server.
    
    Attributes:
        id: Unique task identifier (e.g., "T001")
        category: Task category (infrastructure, index, docs, etc.)
        description: Human-readable description
        files_to_create: List of files this task should create
        files_to_modify: List of existing files to modify
        depends_on: List of task IDs that must complete first
        test_command: Optional command to test the implementation
        status: Current task status
        completed_at: ISO timestamp when completed
        error: Error message if failed
    """
    id: str
    category: str
    description: str
    files_to_create: List[str] = field(default_factory=list)
    files_to_modify: List[str] = field(default_factory=list)
    depends_on: List[str] = field(default_factory=list)
    test_command: Optional[str] = None
    status: str = "pending"
    completed_at: Optional[str] = None
    error: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DevTask":
        """Create DevTask from dictionary."""
        return cls(
            id=data.get("id", ""),
            category=data.get("category", ""),
            description=data.get("description", ""),
            files_to_create=data.get("files_to_create", []),
            files_to_modify=data.get("files_to_modify", []),
            depends_on=data.get("depends_on", []),
            test_command=data.get("test_command"),
            status=data.get("status", "pending"),
            completed_at=data.get("completed_at"),
            error=data.get("error"),
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "id": self.id,
            "category": self.category,
            "description": self.description,
            "files_to_create": self.files_to_create,
            "files_to_modify": self.files_to_modify,
            "depends_on": self.depends_on,
            "test_command": self.test_command,
            "status": self.status,
        }
        if self.completed_at:
            result["completed_at"] = self.completed_at
        if self.error:
            result["error"] = self.error
        return result


class ProgressTracker:
    """Tracks development progress using a JSON task list.
    
    The task list file contains all development tasks for building
    the KLayout MCP Server. This tracker provides methods to query
    and summarize progress.
    """
    
    def __init__(self, workspace: Path):
        """Initialize progress tracker.
        
        Args:
            workspace: The workspace directory for the project
        """
        self.workspace = Path(workspace)
        self.task_list_file = self.workspace / "klayout_mcp_task_list.json"
        self.progress_file = self.workspace / "klayout_mcp_dev_progress.txt"
    
    def task_list_exists(self) -> bool:
        """Check if the task list file exists.
        
        Returns:
            True if task_list.json exists
        """
        return self.task_list_file.exists()
    
    def load_tasks(self) -> List[DevTask]:
        """Load all tasks from the task list file.
        
        Supports two JSON formats:
        1. Array format: [{...}, {...}]
        2. Object format: {"tasks": [{...}, {...}]}
        
        Returns:
            List of DevTask objects
        """
        if not self.task_list_file.exists():
            return []
        
        try:
            data = json.loads(self.task_list_file.read_text(encoding='utf-8'))
            
            # Handle nested format: {"tasks": [...]}
            if isinstance(data, dict):
                tasks_data = data.get("tasks", [])
            elif isinstance(data, list):
                tasks_data = data
            else:
                print(f"Warning: Unexpected task list format: {type(data)}")
                return []
            
            return [DevTask.from_dict(t) for t in tasks_data]
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Could not load task list: {e}")
            return []
    
    def save_tasks(self, tasks: List[DevTask]) -> None:
        """Save tasks to the task list file.
        
        Args:
            tasks: List of DevTask objects to save
        """
        try:
            data = [t.to_dict() for t in tasks]
            self.task_list_file.write_text(
                json.dumps(data, indent=2),
                encoding='utf-8'
            )
        except IOError as e:
            print(f"Warning: Could not save task list: {e}")
    
    def get_summary(self) -> Dict[str, int]:
        """Get a summary of task progress.
        
        Returns:
            Dictionary with task counts by status
        """
        tasks = self.load_tasks()
        
        summary = {
            "total": len(tasks),
            "completed": 0,
            "failed": 0,
            "pending": 0,
            "in_progress": 0,
            "blocked": 0,
        }
        
        for task in tasks:
            status = task.status.lower()
            if status in summary:
                summary[status] += 1
            elif status == TaskStatus.COMPLETED.value:
                summary["completed"] += 1
            elif status == TaskStatus.FAILED.value:
                summary["failed"] += 1
            elif status == TaskStatus.PENDING.value:
                summary["pending"] += 1
            elif status == TaskStatus.IN_PROGRESS.value:
                summary["in_progress"] += 1
            elif status == TaskStatus.BLOCKED.value:
                summary["blocked"] += 1
        
        return summary
    
    def is_all_completed(self) -> bool:
        """Check if all tasks are completed.
        
        Returns:
            True if no pending or in-progress tasks remain
        """
        summary = self.get_summary()
        return (
            summary["total"] > 0 and
            summary["pending"] == 0 and
            summary["in_progress"] == 0
        )
    
    def get_next_task(self) -> Optional[DevTask]:
        """Get the next task to work on.
        
        Finds the highest-priority pending task with all dependencies completed.
        
        Returns:
            The next DevTask to work on, or None if none available
        """
        tasks = self.load_tasks()
        completed_ids = {t.id for t in tasks if t.status == TaskStatus.COMPLETED.value}
        
        for task in tasks:
            if task.status != TaskStatus.PENDING.value:
                continue
            
            # Check if all dependencies are completed
            deps_met = all(dep in completed_ids for dep in task.depends_on)
            if deps_met:
                return task
        
        return None
    
    def print_summary(self) -> None:
        """Print a formatted summary of progress."""
        summary = self.get_summary()
        
        if summary["total"] > 0:
            completed = summary["completed"]
            total = summary["total"]
            pct = (completed / total) * 100
            print(f"\nProgress: {completed}/{total} tasks ({pct:.1f}%)")
            
            if summary["failed"] > 0:
                print(f"  Failed: {summary['failed']}")
            if summary["in_progress"] > 0:
                print(f"  In Progress: {summary['in_progress']}")
            if summary["blocked"] > 0:
                print(f"  Blocked: {summary['blocked']}")
        else:
            print("\nProgress: task_list.json not yet created")
    
    def update_progress_file(self, notes: str) -> None:
        """Update the progress file with notes.
        
        Args:
            notes: Notes to append to the progress file
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        summary = self.get_summary()
        
        content = f"""=== KLayout MCP Server Development Progress ===
Last Updated: {timestamp}

Total Tasks: {summary['total']}
Completed: {summary['completed']}
Failed: {summary['failed']}
Pending: {summary['pending']}
In Progress: {summary['in_progress']}
Blocked: {summary['blocked']}

--- Latest Notes ---
{notes}
"""
        
        try:
            self.progress_file.write_text(content, encoding='utf-8')
        except IOError as e:
            print(f"Warning: Could not update progress file: {e}")
