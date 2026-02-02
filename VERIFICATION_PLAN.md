# KLayout MCP Server - Complete Verification Plan

This document outlines the comprehensive verification strategy for the KLayout MCP Server.

## Quick Start

```bash
# Run quick verification (2 minutes)
./scripts/quick_verify.sh

# Run comprehensive verification (5 minutes)
python3 scripts/verify_mcp.py --verbose

# Run with MCP Inspector (requires npm/npx)
npx @modelcontextprotocol/inspector python3 src/server.py
```

## Verification Levels

### Level 1: Quick Checks (2 minutes)

**Script:** `./scripts/quick_verify.sh`

Checks:
- Python version >= 3.8
- Project structure (pyproject.toml exists, requirements.txt removed)
- Python syntax validation
- Async patterns (async def >= 10, await >= 50)
- Context usage (ctx: Context >= 10)
- Structured output (>= 7 tools)
- Module imports
- evaluation.xml validity
- Dependencies (MCP SDK, Pydantic v2)

### Level 2: Component Tests (5 minutes)

**Script:** `python3 scripts/verify_mcp.py`

Tests:
1. Import all modules
2. Load API index
3. Handle registry operations
4. Security sandbox rules
5. Search functionality
6. Async initialization
7. Tool registration with outputSchema
8. Resource registration

### Level 3: Integration Tests (10 minutes)

Requires KLayout installed:

```bash
# Test with KLayout
python3 -c "
from src.invoker.klayout_compat import get_klayout_compat
compat = get_klayout_compat()
print(f'KLayout available: {compat.is_available}')
print(f'Mode: {compat.mode}')

if compat.is_available:
    from src.invoker.api_invoker import APIInvoker
    from src.invoker.handle_registry import HandleRegistry
    from src.security.sandbox import Sandbox
    
    invoker = APIInvoker(HandleRegistry(), Sandbox())
    result = invoker.invoke_constructor('Box', 'db', {'left': 0, 'bottom': 0, 'right': 100, 'top': 100})
    print(f'Box created: {result.success}')
    if result.success:
        area = invoker.invoke_method(result.return_handle, 'area')
        print(f'Area: {area.return_value}')
"
```

### Level 4: MCP Inspector Test (15 minutes)

Install and run MCP Inspector:

```bash
npm install -g @modelcontextprotocol/inspector

# Run inspector
npx @modelcontextprotocol/inspector python3 src/server.py
```

Then test:
1. List tools - verify all 10 tools appear
2. Check outputSchema - verify structured output
3. Test search_klayout_api with query="Box"
4. Test describe_klayout_api with class_name="Box"
5. Test klayout_test_import
6. Test klayout_get_status

### Level 5: Evaluation Questions (30 minutes)

Use the questions in `evaluation.xml` to test LLM interaction:

1. Provide the first 3 questions to an LLM
2. Verify it can use the tools correctly
3. Check answers match expected results

---

## Automated Verification

Run all verifications:

```bash
# 1. Quick check
./scripts/quick_verify.sh

# 2. Comprehensive Python tests
python3 scripts/verify_mcp.py --verbose

# 3. Syntax check all Python files
python3 -m py_compile src/server.py src/models.py

# 4. Check async implementation
grep -c "async def" src/server.py  # Should be >= 16
grep -c "await " src/server.py     # Should be >= 88

# 5. Check Context usage
grep -c "ctx: Context" src/server.py  # Should be >= 15
grep -c "ctx.report_progress" src/server.py  # Should be >= 30
grep -c "ctx.log_" src/server.py  # Should be >= 20

# 6. Check structured output
grep -c "structured_output=True" src/server.py  # Should be >= 10

# 7. Validate XML
python3 -c "import xml.etree.ElementTree as ET; ET.parse('evaluation.xml')"

# 8. Check pyproject.toml
python3 -c "import tomllib; tomllib.load(open('pyproject.toml', 'rb'))"
```

---

## Expected Results

### Quick Verify Script
All checks should pass with output:
```
✅ All checks passed!
```

### Python Verification
Should show:
```
Total Tests: 20+
✅ Passed: 20+
❌ Failed: 0
```

### MCP Inspector
- Tools: 10 registered
- Resources: 5 registered
- All tools have outputSchema
- search_klayout_api returns results
- klayout_test_import shows mode

---

## Troubleshooting

### Import Errors
```bash
# Install in editable mode
pip install -e ".[dev]"
```

### KLayout Not Found
```bash
# Install standalone KLayout
pip install klayout
```

### MCP SDK Issues
```bash
# Reinstall MCP SDK
pip install --upgrade "mcp[cli]>=1.0.0"
```

### Async Test Failures
```bash
# Check Python version
python3 --version  # Must be >= 3.8

# Check pytest-asyncio
pip install pytest-asyncio
```

---

## Sign-off Checklist

- [ ] Level 1: Quick checks pass
- [ ] Level 2: Component tests pass
- [ ] Level 3: Integration tests pass (if KLayout available)
- [ ] Level 4: MCP Inspector shows all tools
- [ ] Level 5: Evaluation questions can be answered

**When all levels pass, the MCP server is production-ready.**
