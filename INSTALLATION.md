# Installation Guide

## ⚠️ Important Note About Data Files

This MCP server requires data files (`data/api_index.json` and `klayout-doc/markdown_docs/`) to function fully:
- `data/api_index.json` (39MB) - Required for `search_klayout_api`
- `klayout-doc/markdown_docs/` (~5MB) - Required for `search_klayout_docs`

## Recommended Installation Methods

### Method 1: Clone and Editable Install (Recommended for Users)

This ensures all data files are available:

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/klayout_mcp.git
cd klayout_mcp

# Install in editable mode using uv
uv venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
uv pip install -e ".[all]"

# Run the server
python src/server.py
```

**Pros:**
- ✅ All features work (including `search_klayout_docs`)
- ✅ Easy to update (`git pull`)
- ✅ Can modify code if needed

**Cons:**
- Requires git clone (~44MB download)

### Method 2: Direct from GitHub (Experimental)

```bash
uv pip install "git+https://github.com/YOUR_USERNAME/klayout_mcp"
```

**Note:** As of current version, this method may not include data files properly. Please use Method 1 instead.

### Method 3: Using pip

```bash
# Clone first
git clone https://github.com/YOUR_USERNAME/klayout_mcp.git
cd klayout_mcp

# Install using pip
pip install -e ".[all]"
```

## Verification

After installation, verify data files are accessible:

```bash
python -c "
from src.server import INDEX_PATH, DOCS_PATH
print(f'API Index: {INDEX_PATH}')
print(f'  Exists: {INDEX_PATH.exists()}')
print(f'Docs Path: {DOCS_PATH}')
print(f'  Exists: {DOCS_PATH.exists()}')
"
```

Expected output:
```
API Index: /path/to/klayout_mcp/data/api_index.json
  Exists: True
Docs Path: /path/to/klayout_mcp/klayout-doc/markdown_docs
  Exists: True
```

## Feature Availability by Installation Method

| Installation Method | API Search | Doc Search | KLayout Calls | Notes |
|---------------------|------------|------------|---------------|-------|
| `git clone + pip install -e .` | ✅ | ✅ | ✅ | Recommended |
| `pip install git+https://...` | ⚠️ | ⚠️ | ✅ | Data files may be missing |
| PyPI (future) | TBD | TBD | ✅ | Not yet published |

## Troubleshooting

### "API index not loaded" Error

**Cause:** `data/api_index.json` not found

**Solution:** Use editable install (Method 1)

```bash
cd klayout_mcp
uv pip install -e ".[all]"
```

### "Documentation not available" Error

**Cause:** `klayout-doc/markdown_docs/` not found

**Solution:** Ensure you cloned the full repository with all subdirectories

```bash
# Re-clone with full history
git clone --depth 1 https://github.com/YOUR_USERNAME/klayout_mcp.git
```

### Check What's Installed

```python
# Check installed paths
import src.server as server
print(f"Index path: {server.INDEX_PATH}")
print(f"Index exists: {server.INDEX_PATH.exists()}")
print(f"Docs path: {server.DOCS_PATH}")
print(f"Docs exists: {server.DOCS_PATH.exists()}")
```

## For Developers

### Setting up Development Environment

```bash
git clone https://github.com/YOUR_USERNAME/klayout_mcp.git
cd klayout_mcp

# Create virtual environment
uv venv
source .venv/bin/activate

# Install in editable mode with all dev dependencies
uv pip install -e ".[all]"

# Run tests
pytest tests/ -v

# Run verification
python scripts/verify_mcp.py
```

## Future: PyPI Installation

When published to PyPI, the installation will be:

```bash
uv pip install klayout-mcp
```

**Note:** PyPI version may have reduced functionality if data files are not included in the wheel. The recommended method will always be cloning from GitHub.

---

## Summary

**For most users:**
```bash
git clone https://github.com/YOUR_USERNAME/klayout_mcp.git
cd klayout_mcp
uv pip install -e ".[all]"
python src/server.py
```

This ensures all features are available and working correctly.
