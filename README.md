# KLayout MCP Server

A Model Context Protocol (MCP) server that exposes 2000+ KLayout APIs through intelligent meta-tools, enabling LLMs to interact with KLayout's powerful layout design and verification capabilities.

## Features

- **Comprehensive API Coverage**: Access to 1,348 KLayout classes and 41,449+ methods
- **Meta-Tool Architecture**: 7 intelligent tools that dynamically handle 2000+ APIs without creating individual tool definitions
- **Dual-Mode Support**: Works with both KLayout GUI (`pya`) and standalone (`klayout.db`) modes
- **Smart API Search**: Fast keyword-based search with relevance ranking and filtering
- **Security Sandbox**: Protects against dangerous API calls and resource exhaustion
- **Flexible Output**: Supports both JSON and Markdown response formats
- **Object Handle Management**: Persistent object references with lifecycle management across API calls

## Installation

### Prerequisites

- Python 3.8+
- KLayout (standalone package or GUI)

### ⚠️ Important: Installation Methods

This server requires data files to function fully:
- `data/api_index.json` (39MB) - Required for `search_klayout_api`
- `klayout-doc/markdown_docs/` (~5MB) - Required for `search_klayout_docs`

#### ✅ Recommended: Clone and Editable Install

**This is the only method that guarantees all features work correctly.**

```bash
# Clone the repository (includes all data files)
git clone https://github.com/YOUR_USERNAME/klayout_mcp.git
cd klayout_mcp

# Create virtual environment
uv venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install in editable mode
uv pip install -e ".[all]"

# Or using pip instead of uv
pip install -e ".[all]"
```

#### ❌ Not Recommended: Direct pip install from Git

```bash
# DON'T DO THIS - Data files will be missing!
uv pip install git+https://github.com/YOUR_USERNAME/klayout_mcp
```

**Why not recommended?**
- ❌ `search_klayout_api` will fail (missing `data/api_index.json`)
- ❌ `search_klayout_docs` will fail (missing `klayout-doc/markdown_docs/`)
- ✅ Only `call_klayout_api` and `klayout_manage_handles` will work

#### Installation Options

```bash
# Basic installation (minimal dependencies)
uv pip install -e "."

# With standalone KLayout support
uv pip install -e ".[standalone]"

# With development tools (testing, type checking)
uv pip install -e ".[dev]"

# With all optional dependencies
uv pip install -e ".[all]"
```

### Verify Installation

```bash
# Check data files are accessible
python -c "
from src.server import INDEX_PATH, DOCS_PATH
print(f'API Index: {INDEX_PATH}')
print(f'  Exists: {INDEX_PATH.exists()}')
print(f'Docs Path: {DOCS_PATH}')
print(f'  Exists: {DOCS_PATH.exists()}')
"

# Expected output:
# API Index: /path/to/klayout_mcp/data/api_index.json
#   Exists: True
# Docs Path: /path/to/klayout_mcp/klayout-doc/markdown_docs
#   Exists: True

# Test KLayout availability
python -c "import klayout.db; print('KLayout installed successfully')"

# Run verification suite
python scripts/verify_mcp.py
```

## Quick Start

### Run the MCP Server

```bash
# Make sure you're in the project directory
cd klayout_mcp

# Run the server
python src/server.py
```

The server runs with stdio transport by default, suitable for integration with MCP clients.

**Note**: Make sure `python3` command is available in your PATH. The server requires Python 3.8+.

### Configure with Claude Desktop

Add to your Claude Desktop configuration (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "klayout": {
      "command": "python3",
      "args": ["/path/to/klayout_mcp/src/server.py"]
    }
  }
}
```

## Available Tools

### 1. `search_klayout_api`
Search KLayout APIs by keyword with filtering and pagination.

```python
# Example: Find box-related APIs
search_klayout_api(
    query="Box",
    module="db",
    search_type="class",
    limit=10,
    response_format="markdown"
)
```

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| query | string | required | Search query string |
| module | enum | null | Filter: "db", "lay", "tl", "rdb", "pex" |
| search_type | enum | null | Filter: "class" or "method" |
| limit | int | 20 | Max results (1-100) |
| offset | int | 0 | Pagination offset |
| response_format | enum | "json" | Output: "json" or "markdown" |

### 2. `describe_klayout_api`
Get detailed documentation for a KLayout class or method.

```python
# Example: Get Box class documentation
describe_klayout_api(
    class_name="Box",
    include_examples=True,
    response_format="markdown"
)

# Example: Get specific method documentation
describe_klayout_api(
    class_name="Box",
    method_name="area"
)
```

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| class_name | string | required | KLayout class name |
| method_name | string | null | Specific method to describe |
| include_examples | bool | true | Include code examples |
| response_format | enum | "json" | Output format |

### 3. `call_klayout_api`
Execute KLayout API calls dynamically.

```python
# Example: Create a Box
call_klayout_api(
    operation="constructor",
    class_name="Box",
    params={"left": 0, "bottom": 0, "right": 100, "top": 100}
)
# Returns: {"success": true, "handle": "box_abc123_1234567890", ...}

# Example: Call method on the Box
call_klayout_api(
    operation="method",
    class_name="Box",
    method_name="area",
    handle="box_abc123_1234567890"
)
# Returns: {"success": true, "value": 10000, ...}
```

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| operation | enum | required | "constructor", "method", or "static" |
| class_name | string | required | KLayout class name |
| method_name | string | null | Method name (required for method/static) |
| handle | string | null | Object handle (required for method) |
| params | dict | null | Parameters as key-value pairs |

### 4. `klayout_manage_handles`
Manage object handles created by `call_klayout_api`.

```python
# List all handles
klayout_manage_handles(action="list")

# List only Box handles
klayout_manage_handles(action="list", filter_type="Box")

# Set an alias for easier reference
klayout_manage_handles(
    action="alias",
    handle="box_abc123_1234567890",
    alias="my_box"
)

# Release a handle
klayout_manage_handles(action="release", handle="my_box")
```

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| action | enum | required | "list", "get", "release", "release_all", "alias" |
| handle | string | null | Handle ID (required for get/release/alias) |
| alias | string | null | Alias name (required for alias) |
| filter_type | string | null | Filter by type for list action |
| response_format | enum | "json" | Output format |

### 5. `search_klayout_docs`
Search KLayout general documentation and tutorials.

```python
# Search all documentation
search_klayout_docs(query="coordinate transformation")

# Get specific topic
search_klayout_docs(topic="transformations")

# Search within a topic
search_klayout_docs(query="rotation", topic="transformations")
```

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| query | string | "" | Search query |
| topic | string | null | Topic filter |
| limit | int | 10 | Max results (1-50) |
| response_format | enum | "json" | Output format |

### 6. `klayout_test_import`
Test KLayout availability and diagnose installation issues.

```python
klayout_test_import()
# Returns mode, availability status, and troubleshooting info
```

### 7. `klayout_get_status`
Get comprehensive server status information.

```python
klayout_get_status()
# Returns server health, API stats, handle count, etc.
```

## Usage Examples

### Create and Manipulate Geometry

```python
# 1. Create a Layout
call_klayout_api(operation="constructor", class_name="Layout")
# -> handle: layout_xyz123

# 2. Create a cell in the layout
call_klayout_api(
    operation="method",
    class_name="Layout",
    method_name="create_cell",
    handle="layout_xyz123",
    params={"name": "TOP"}
)
# -> handle: cell_abc456

# 3. Create a box
call_klayout_api(
    operation="constructor",
    class_name="Box",
    params={"left": 0, "bottom": 0, "right": 1000, "top": 1000}
)
# -> handle: box_def789

# 4. Get box area
call_klayout_api(
    operation="method",
    class_name="Box",
    method_name="area",
    handle="box_def789"
)
# -> value: 1000000
```

### Workflow Example: Design Rule Check Setup

```python
# 1. Search for DRC-related classes
search_klayout_api(query="Region", module="db")

# 2. Get detailed info about Region class
describe_klayout_api(class_name="Region", include_examples=True)

# 3. Create regions and perform operations
call_klayout_api(operation="constructor", class_name="Region")
```

## Project Structure

```
klayout_mcp/
├── src/                    # Core MCP server implementation
│   ├── server.py           # Main MCP server entry point
│   ├── models.py           # Pydantic input/output models
│   ├── formatters.py       # Response formatters (JSON/Markdown)
│   ├── index/              # API index and search engine
│   │   ├── api_index.py    # Index loader and search logic
│   │   └── index_builder.py # Index generation from docs
│   ├── docs/               # Documentation store and retrieval
│   │   ├── document_store.py # Document storage and search
│   │   └── doc_chunker.py    # Document chunking for search
│   ├── invoker/            # Dynamic API invocation engine
│   │   ├── api_invoker.py    # Core invocation logic
│   │   ├── handle_registry.py # Object lifecycle management
│   │   ├── klayout_compat.py  # Dual-mode (pya/db) compatibility
│   │   └── parameter_parser.py # Parameter type conversion
│   ├── security/           # Security sandbox
│   │   ├── sandbox.py        # API call filtering and limits
│   │   └── path_validator.py # Path traversal prevention
│   └── tools/              # MCP tool implementations (7 tools)
│       ├── search_api.py     # search_klayout_api
│       ├── describe_api.py   # describe_klayout_api
│       ├── call_api.py       # call_klayout_api
│       ├── manage_handles.py # klayout_manage_handles
│       └── search_docs.py    # search_klayout_docs + status/test tools
├── data/
│   └── api_index.json      # Pre-built API index (39MB, 1348 classes)
├── klayout-doc/            # KLayout documentation source
│   ├── markdown_docs/      # Parsed markdown docs (1,348 files)
│   └── downloaded_html/    # Original HTML documentation
├── scripts/                # Build and maintenance scripts
│   └── build_index.py      # API index builder from markdown docs
├── tests/
│   └── test_e2e.py         # End-to-end integration tests
├── pyproject.toml          # Python project configuration
├── LICENSE                 # BSD 3-Clause License
└── README.md               # This file
```

## API Statistics

- **Total Classes**: 1,348
- **Total Methods**: 41,449+
- **Modules**: `db` (database), `lay` (layout view), `tl` (tools), `rdb` (report database), `pex` (parameter extraction)
- **Index Size**: ~39MB (pre-built JSON)
- **Documentation Files**: 1,348 markdown files + HTML source
- **Meta-Tools**: 7 intelligent tools handling all 2000+ APIs dynamically

## Security

The server includes a security sandbox that:
- Blocks dangerous API calls (network, file write, process execution)
- Enforces execution time limits (60 seconds default)
- Limits object count to prevent memory exhaustion
- Validates file paths to prevent directory traversal

## Development

### Run Tests

```bash
pytest tests/ -v
```

### Rebuild API Index (Optional)

The project includes a pre-built API index in `data/api_index.json`. You only need to rebuild it if:
- KLayout version is updated
- Documentation parsing logic is modified
- You want to use custom documentation

```bash
python scripts/build_index.py

# Or with custom paths:
python scripts/build_index.py klayout-doc/markdown_docs data/api_index.json
```

### Type Checking

```bash
pip install mypy
mypy src/
```

## Verification

Run the verification suite to ensure everything is working:

```bash
# Quick verification (2 minutes)
./scripts/quick_verify.sh

# Comprehensive verification (5 minutes)
python scripts/verify_mcp.py --verbose
```

## License

BSD 3-Clause License - See [LICENSE](LICENSE) for details.

## Contributing

Contributions are welcome! Please ensure:
1. All tests pass
2. Code follows existing style
3. New features include tests
4. Documentation is updated

## Acknowledgments

- [KLayout](https://www.klayout.de/) - The amazing open-source layout viewer and editor
- [Model Context Protocol](https://modelcontextprotocol.io/) - The protocol enabling LLM-tool integration
