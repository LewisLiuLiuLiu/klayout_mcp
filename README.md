# KLayout MCP Server

A Model Context Protocol (MCP) server that exposes 2000+ KLayout APIs through intelligent meta-tools, enabling LLMs to interact with KLayout's powerful layout design and verification capabilities.

## Features

- **Comprehensive API Coverage**: Access to 1,348 KLayout classes and thousands of methods
- **Meta-Tool Architecture**: 7 well-designed tools that dynamically access all APIs
- **Dual-Mode Support**: Works with both KLayout GUI (pya) and standalone (klayout.db) modes
- **Security Sandbox**: Protects against dangerous API calls and resource exhaustion
- **Flexible Output**: Supports both JSON and Markdown response formats
- **Object Handle Management**: Persistent object references across API calls

## Installation

### Prerequisites

- Python 3.8+
- KLayout (standalone package or GUI)

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Install KLayout (Standalone Mode)

```bash
pip install klayout
```

### Verify Installation

```bash
python -c "import klayout.db; print('KLayout installed successfully')"
```

## Quick Start

### Run the MCP Server

```bash
cd src
python server.py
```

The server runs with stdio transport by default, suitable for integration with MCP clients.

### Configure with Claude Desktop

Add to your Claude Desktop configuration (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "klayout": {
      "command": "python",
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
├── src/
│   ├── server.py           # Main MCP server
│   ├── models.py           # Pydantic input/output models
│   ├── formatters.py       # Response formatters (JSON/Markdown)
│   ├── index/              # API index and search
│   │   ├── api_index.py
│   │   └── index_builder.py
│   ├── docs/               # Documentation store
│   │   ├── document_store.py
│   │   └── doc_chunker.py
│   ├── invoker/            # API invocation engine
│   │   ├── api_invoker.py
│   │   ├── handle_registry.py
│   │   ├── klayout_compat.py
│   │   └── parameter_parser.py
│   ├── security/           # Security sandbox
│   │   ├── sandbox.py
│   │   └── path_validator.py
│   └── tools/              # Tool implementations
│       ├── search_api.py
│       ├── describe_api.py
│       ├── call_api.py
│       ├── manage_handles.py
│       └── search_docs.py
├── data/
│   └── api_index.json      # Pre-built API index (39MB)
├── klayout-doc/
│   └── markdown_docs/      # KLayout documentation (1,348 files)
├── tests/
│   └── test_e2e.py         # End-to-end tests
├── requirements.txt
└── README.md
```

## API Statistics

- **Total Classes**: 1,348
- **Modules**: db, lay, tl, rdb, pex
- **Index Size**: 39MB (pre-built JSON)
- **Documentation Files**: 1,348 markdown files

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

### Build API Index

```bash
python -m src.index.index_builder
```

### Type Checking

```bash
pip install mypy
mypy src/
```

## License

MIT License - See [LICENSE](LICENSE) for details.

## Contributing

Contributions are welcome! Please ensure:
1. All tests pass
2. Code follows existing style
3. New features include tests
4. Documentation is updated

## Acknowledgments

- [KLayout](https://www.klayout.de/) - The amazing open-source layout viewer and editor
- [Model Context Protocol](https://modelcontextprotocol.io/) - The protocol enabling LLM-tool integration
