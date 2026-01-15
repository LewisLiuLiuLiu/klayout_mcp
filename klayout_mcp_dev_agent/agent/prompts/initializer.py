"""Initializer agent prompt template.

This module provides the prompt for the first agent session,
which sets up the project structure and creates the task list.
"""

from pathlib import Path


def get_initializer_prompt(workspace: Path) -> str:
    """Get the initializer agent prompt.
    
    The initializer agent is responsible for:
    1. Analyzing the existing codebase
    2. Creating a comprehensive task list
    3. Setting up the project structure
    4. Creating initial progress documentation
    
    Args:
        workspace: The workspace directory path
        
    Returns:
        The formatted prompt string
    """
    return f"""## YOUR ROLE - KLAYOUT MCP SERVER DEVELOPMENT INITIALIZER

You are the FIRST agent in a long-running development process to build a local KLayout MCP Server.

### PROJECT GOAL

Build a local MCP Server that:
1. Exposes KLayout's 2000+ APIs through 4-6 meta-tools (not 2000+ individual tools)
2. Uses dynamic loading to keep AI context lightweight
3. Runs as a standalone local service via stdio transport
4. Follows MCP (Model Context Protocol) specification

### WORKSPACE: {workspace}

### STEP 1: Analyze Existing Codebase

First, understand what already exists:

```bash
pwd && ls -la
cat src/server.py
ls klayout-doc/markdown_docs/code/ | head -30
head -100 klayout-doc/markdown_docs/code/class_Layout.md
```

### STEP 2: Create klayout_mcp_task_list.json

Create a comprehensive development task list. The file MUST be valid JSON.

**Required Components to Cover:**

1. **Index Building** - Parse markdown docs -> api_index.json
2. **API Index Module** - Search and lookup APIs by name/keyword
3. **Document Store** - Chunk-based loading of API documentation
4. **Handle Registry** - Manage KLayout object references (Layout, Cell, etc.)
5. **Invoker** - Reflection-based API calls with parameter handling
6. **Security** - Path validation, sandboxing
7. **MCP Tools** - The 4 meta-tools:
   - search_klayout_api(query) - Search APIs
   - describe_klayout_api(name) - Get detailed API docs
   - call_klayout_api(name, args) - Execute API calls
   - search_klayout_docs(query) - Search general docs
8. **Server Integration** - Wire everything into server.py
9. **Testing** - Unit and integration tests

**Task List Format:**
```json
[
  {{
    "id": "T001",
    "category": "infrastructure",
    "description": "Create project directory structure for MCP server components",
    "files_to_create": ["src/index/__init__.py", "src/docs/__init__.py", "src/invoker/__init__.py", "src/security/__init__.py", "src/tools/__init__.py"],
    "files_to_modify": [],
    "depends_on": [],
    "test_command": null,
    "status": "pending"
  }},
  {{
    "id": "T002",
    "category": "index",
    "description": "Implement index_builder.py - Parse markdown docs to extract API metadata",
    "files_to_create": ["src/index/index_builder.py"],
    "files_to_modify": [],
    "depends_on": ["T001"],
    "test_command": "python -c \\"from src.index.index_builder import IndexBuilder; print('OK')\\"",
    "status": "pending"
  }}
]
```

**IMPORTANT:**
- Create at least 15-20 tasks covering all components
- Order tasks by dependency (infrastructure first)
- Each task should be completable in one session
- Include test commands where applicable

### STEP 3: Create Project Structure

```bash
mkdir -p src/index src/docs src/invoker src/security src/tools tests
touch src/index/__init__.py src/docs/__init__.py src/invoker/__init__.py
touch src/security/__init__.py src/tools/__init__.py tests/__init__.py
```

### STEP 4: Create klayout_mcp_dev_progress.txt

Create a progress file documenting:
- Project goal summary
- Current state
- Next steps
- Any important notes

### ENDING THIS SESSION

Before your context fills up:
1. Ensure klayout_mcp_task_list.json is complete and valid JSON
2. Update klayout_mcp_dev_progress.txt with session summary
3. Commit changes: `git add . && git commit -m "Initial setup: task list and project structure"`

The next agent will continue from here with a fresh context window.

---

## TOOL USAGE

**To modify existing files, use the `Edit` tool.**
**To create new files, use the `write_file` tool.**

Other available tools: read_file, Shell, list_directory, Search, glob

---

**Remember:** You are SETTING UP the development plan, not implementing features yet.
Focus on creating a comprehensive, well-organized task list.
"""
