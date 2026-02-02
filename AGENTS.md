# KLayout MCP Server - Agent Guide

This document provides essential information for AI coding agents working on the KLayout MCP Server project.

## Project Overview

KLayout MCP Server is a Model Context Protocol (MCP) server that exposes 2000+ KLayout APIs through 7 intelligent meta-tools. It enables LLMs to interact with KLayout's powerful IC layout design and verification capabilities.

- **Repository**: klayout_mcp
- **License**: BSD 3-Clause License (Copyright 2026, Lewis Liu)
- **Language**: English (all code and documentation)

### Key Features
- Comprehensive API coverage: 1,348 classes and 41,449+ methods
- Meta-tool architecture: 7 tools dynamically handle all APIs
- Dual-mode support: Works with KLayout GUI (`pya`) and standalone (`klayout.db`)
- Security sandbox: Blocks dangerous API calls and enforces resource limits
- Object handle management: Persistent object references across API calls

## Technology Stack

- **Python**: 3.8+
- **MCP Framework**: `mcp[cli]>=1.0.0` (FastMCP)
- **Validation**: `pydantic>=2.0.0`
- **Documentation Parsing**: `markdown-it-py>=3.0.0`, `python-frontmatter>=1.0.0`
- **Testing**: `pytest>=7.0.0`
- **Optional**: `klayout>=0.28.0` (for standalone mode)

## Project Structure

```
klayout_mcp/
├── src/                          # Core MCP server implementation
│   ├── server.py                 # Main entry point, async MCP tools
│   ├── models.py                 # Pydantic input/output models
│   ├── formatters.py             # JSON/Markdown response formatters
│   ├── index/                    # API index and search engine
│   │   ├── api_index.py          # Index loader and search logic
│   │   └── index_builder.py      # Index generation from docs
│   ├── invoker/                  # Dynamic API invocation engine
│   │   ├── api_invoker.py        # Core invocation logic
│   │   ├── handle_registry.py    # Object lifecycle management
│   │   ├── klayout_compat.py     # Dual-mode (pya/db) compatibility
│   │   └── parameter_parser.py   # Parameter type conversion
│   ├── security/                 # Security sandbox
│   │   ├── sandbox.py            # API call filtering and limits
│   │   └── path_validator.py     # Path traversal prevention
│   ├── docs/                     # Documentation store
│   │   ├── document_store.py     # Document storage and search
│   │   └── doc_chunker.py        # Document chunking for search
│   └── tools/                    # MCP tool implementations
│       ├── search_api.py         # search_klayout_api
│       ├── describe_api.py       # describe_klayout_api
│       ├── call_api.py           # call_klayout_api
│       ├── manage_handles.py     # klayout_manage_handles
│       └── search_docs.py        # search_klayout_docs + utilities
├── data/
│   └── api_index.json            # Pre-built API index (~39MB)
├── klayout-doc/                  # KLayout documentation source
│   └── markdown_docs/            # Parsed markdown docs (1,348 files)
├── scripts/
│   └── build_index.py            # API index builder from markdown docs
├── tests/
│   └── test_e2e.py               # End-to-end integration tests
├── pyproject.toml                # Python project configuration
└── README.md                     # Project documentation
```

## Build and Run Commands

### Installation
```bash
# Install from pyproject.toml (editable mode)
pip install -e .

# For standalone mode (includes klayout package)
pip install -e ".[standalone]"

# For development (includes testing tools)
pip install -e ".[dev]"

# Install all optional dependencies
pip install -e ".[all]"
```

### Run the Server
```bash
python src/server.py
```
The server runs with stdio transport by default, suitable for MCP clients like Claude Desktop.

### Testing
```bash
# Run all tests (async mode enabled)
pytest tests/ -v

# Run specific test class
pytest tests/test_e2e.py::TestAPIIndex -v
```

### Type Checking (optional)
```bash
# mypy is included in dev dependencies
mypy src/
```

### Rebuild API Index (optional)
Only needed when KLayout is updated or documentation parsing logic changes:
```bash
python scripts/build_index.py

# Or with custom paths:
python scripts/build_index.py klayout-doc/markdown_docs data/api_index.json
```

## Code Organization

### Main Entry Point (`src/server.py`)
- Creates `FastMCP` server instance
- Defines 7 MCP tools with annotations
- Uses lazy initialization for components
- Tools: `search_klayout_api`, `describe_klayout_api`, `call_klayout_api`, `klayout_manage_handles`, `search_klayout_docs`, `klayout_test_import`, `klayout_get_status`

### Input Models (`src/models.py`)
- All input models inherit from `pydantic.BaseModel`
- Use `ConfigDict(extra='forbid')` to reject unknown fields
- Use `Field()` for validation and documentation
- Enums defined for constrained choices: `ResponseFormat`, `SearchType`, `ModuleType`, `OperationType`, `HandleAction`

### API Index (`src/index/`)
- `APIIndex`: Loads JSON index, provides search with relevance scoring
- `IndexBuilder`: Parses markdown docs to generate the index
- Search supports filtering by module (db, lay, tl, rdb, pex) and type (class/method)

### API Invoker (`src/invoker/`)
- `APIInvoker`: Executes KLayout API calls using reflection
- `HandleRegistry`: Manages object handles with lifecycle tracking
- `KLayoutCompat`: Unifies `pya` and `klayout.db` module access
- `ParameterParser`: Resolves handle references in parameters

### Security (`src/security/`)
- `Sandbox`: Blocks dangerous classes/methods, enforces execution time limits (60s default)
- `PathValidator`: Prevents directory traversal attacks
- Blocked classes: `QProcess`, `QTcpSocket`, `QFile`, etc.

### Response Formatters (`src/formatters.py`)
- `ResponseFormatter`: Formats responses as JSON or Markdown
- `ErrorHelper`: Creates actionable error messages with suggestions

## Code Style Guidelines

### Python Style
- Follow PEP 8 conventions
- Use type hints for function signatures and variables
- Docstrings use triple double quotes with format:
  ```python
  """
  Brief description.
  
  Longer description if needed.
  
  Args:
      param: Description
      
  Returns:
      Description of return value
  """
  ```

### Naming Conventions
- Classes: `PascalCase` (e.g., `APIInvoker`, `HandleRegistry`)
- Functions/Methods: `snake_case` (e.g., `invoke_constructor`, `check_api_call`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `HANDLE_TYPES`, `STANDALONE_MODULES`)
- Private members: `_leading_underscore` (e.g., `_index`, `_registry`)

### Module Organization
- Each module has a module docstring at the top
- Imports grouped: standard library, third-party, local
- Use relative imports within packages (e.g., `from ..invoker.api_invoker import APIInvoker`)

### Error Handling
- Return dictionaries with `{"success": False, "error": "...", "suggestion": "..."}` pattern
- Use specific error codes (e.g., `CLASS_NOT_FOUND`, `HANDLE_NOT_FOUND`)
- Include actionable suggestions in error responses

## Testing Strategy

### Test Structure (`tests/test_e2e.py`)
- Organized by class: `TestAPIIndex`, `TestDocumentStore`, `TestHandleRegistry`, `TestAPIInvoker`, `TestSandbox`, `TestIntegration`
- Uses pytest fixtures for common dependencies
- Tests marked with `@pytest.mark.skipif` when KLayout not available

### Running Tests
```bash
# All tests
pytest tests/ -v

# Specific test class
pytest tests/test_e2e.py::TestAPIIndex -v

# With coverage
pytest tests/ --cov=src --cov-report=html
```

## Evaluation

The project includes an `evaluation.xml` file with 10 comprehensive test questions designed to verify that LLMs can effectively use the KLayout MCP server to accomplish real-world tasks.

### Evaluation Questions Overview

| # | Topic | Complexity | Tools Used |
|---|-------|------------|------------|
| 1 | Box class API discovery | Low | search, describe |
| 2 | Object creation and methods | Low | call, manage_handles |
| 3 | Area method discovery | Medium | search |
| 4 | Documentation search | Medium | search_docs |
| 5 | Object transformation | Medium | call, manage_handles |
| 6 | Layout/Cell hierarchy | High | search, describe |
| 7 | Geometric intersection | High | call, manage_handles |
| 8 | Module organization | Medium | search |
| 9 | Edge and vector operations | High | call, search, describe |
| 10 | Comprehensive polygon workflow | High | All tools |

### Running Evaluation

The evaluation questions are in XML format at `evaluation.xml`. These can be used with automated evaluation frameworks or manual testing.

### Test Fixtures
- `api_index`: Creates and loads API index
- `doc_store`: Creates document store
- `registry`: Creates handle registry
- `invoker`: Creates API invoker with sandbox

## Development Conventions

### Adding New MCP Tools
1. Define input model in `src/models.py` (inherit from `BaseModel`)
2. Add tool implementation in `src/tools/` if complex
3. Add tool function in `src/server.py` with `@mcp.tool()` decorator
4. Add annotations for hints: `readOnlyHint`, `destructiveHint`, `idempotentHint`
5. Include comprehensive docstring with examples
6. Update tests if needed

### Modifying API Index
- The index is a large JSON file (~39MB) tracking 1,348 classes
- Only rebuild when necessary (KLayout updates or parsing changes)
- Use `scripts/build_index.py` for rebuilding

### Handle Management
- Handles are strings like `box_abc123_1234567890`
- Complex objects are registered as handles automatically
- Use `klayout_manage_handles` tool to list/release handles
- Aliases can be set for easier reference

## Configuration and Environment

### KLayout Modes
The server auto-detects the environment:
1. **GUI Mode**: `import pya` (running inside KLayout GUI)
2. **Standalone Mode**: `import klayout.db` (separate Python process)

### Environment Variables
No specific environment variables required. KLayout modules are detected automatically.

### File Paths
- Index path: `data/api_index.json` (relative to project root)
- Docs path: `klayout-doc/markdown_docs/` (relative to project root)
- Paths resolved using `Path(__file__).parent.parent`

## Security Considerations

### Sandbox Protection
- **Blocked Classes**: `QProcess`, `QTcpSocket`, `QNetworkAccessManager`, `QFile`
- **Blocked Methods**: `system`, `exec`, `eval`, `compile`, `__import__`, `open`
- **Blocked Patterns**: `*socket*`, `*network*`, `*process*`, `*file*write*`
- **Resource Limits**: 60s execution time, 1000 max objects

### Path Validation
- Prevents directory traversal (`../../../etc/passwd`)
- Validates paths against allowed directories
- Blocks system paths like `/etc/passwd`

## Common Tasks

### Adding a New API Search Filter
1. Update `SearchAPIInput` model in `src/models.py`
2. Modify `APIIndex.search()` in `src/index/api_index.py`
3. Update `SearchAPITool.search()` in `src/tools/search_api.py` if needed

### Adding New Response Format
1. Add format option to `ResponseFormat` enum in `src/models.py`
2. Add formatter method in `ResponseFormatter` class
3. Update tool functions to use new format

### Debugging API Calls
1. Use `klayout_test_import()` to verify KLayout availability
2. Use `klayout_get_status()` to check server health
3. Use `klayout_manage_handles(action="list")` to see active objects
4. Check execution time in response (`execution_time_ms`)

## Dependencies and External APIs

### KLayout Modules
- `klayout.db` (or `pya`): Database/geometry classes (Box, Layout, Cell, etc.)
- `klayout.lay`: GUI/layout view classes (LayoutView, CellView)
- `klayout.tl`: Utility classes (Progress, Logger, Expression)
- `klayout.rdb`: Report database classes
- `klayout.lib`: Library and PCell classes

### MCP Protocol
- Uses `FastMCP` from the official `mcp` Python package
- Tools use `transport='stdio'` for communication
- Tool annotations provide hints to MCP clients

## Notes for AI Agents

- **Do not assume** KLayout is installed in the environment. Tests should handle missing KLayout gracefully.
- **Do not rebuild the index** unless explicitly requested. The pre-built index at `data/api_index.json` is large and rebuilding is slow.
- **Maintain backward compatibility** when adding new tools or parameters. The project includes deprecated tool aliases for backward compatibility.
- **Follow the existing error response pattern**: Always include `success`, `error`, and `suggestion` fields in error responses.
- **Keep imports organized**: Standard library, third-party packages, then local imports.
- **Document parameters thoroughly**: Use Pydantic `Field()` with descriptions, examples, and validation constraints.
