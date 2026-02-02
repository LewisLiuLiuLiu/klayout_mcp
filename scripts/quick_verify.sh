#!/bin/bash
#
# Quick Verification Script for KLayout MCP Server
# Run this for a fast check of the most critical functionality
#

set -e  # Exit on error

echo "=========================================="
echo "KLayout MCP Server - Quick Verification"
echo "=========================================="
echo ""

cd "$(dirname "$0")/.."
PROJECT_ROOT=$(pwd)

ERRORS=0

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

check_pass() {
    echo -e "${GREEN}✅${NC} $1"
}

check_fail() {
    echo -e "${RED}❌${NC} $1"
    ERRORS=$((ERRORS + 1))
}

check_warn() {
    echo -e "${YELLOW}⚠️${NC} $1"
}

# 1. Check Python version
echo "1. Checking Python version..."
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
if python3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)" 2>/dev/null; then
    check_pass "Python $PYTHON_VERSION (>= 3.8)"
else
    check_fail "Python $PYTHON_VERSION (< 3.8 required)"
fi
echo ""

# 2. Check project files
echo "2. Checking project structure..."
if [ -f "$PROJECT_ROOT/pyproject.toml" ]; then
    check_pass "pyproject.toml exists"
else
    check_fail "pyproject.toml missing"
fi

if [ -f "$PROJECT_ROOT/requirements.txt" ]; then
    check_fail "requirements.txt should be removed (use pyproject.toml)"
else
    check_pass "requirements.txt removed"
fi

if [ -f "$PROJECT_ROOT/evaluation.xml" ]; then
    check_pass "evaluation.xml exists"
else
    check_warn "evaluation.xml missing"
fi

if [ -f "$PROJECT_ROOT/data/api_index.json" ]; then
    INDEX_SIZE=$(du -h "$PROJECT_ROOT/data/api_index.json" | cut -f1)
    check_pass "API index exists ($INDEX_SIZE)"
else
    check_fail "API index missing"
fi
echo ""

# 3. Check Python syntax
echo "3. Checking Python syntax..."
if python3 -m py_compile "$PROJECT_ROOT/src/server.py" 2>/dev/null; then
    check_pass "src/server.py syntax OK"
else
    check_fail "src/server.py has syntax errors"
fi

if python3 -m py_compile "$PROJECT_ROOT/src/models.py" 2>/dev/null; then
    check_pass "src/models.py syntax OK"
else
    check_fail "src/models.py has syntax errors"
fi
echo ""

# 4. Check for async patterns
echo "4. Checking async implementation..."
ASYNC_COUNT=$(grep -c "async def" "$PROJECT_ROOT/src/server.py" || echo "0")
AWAIT_COUNT=$(grep -c "await " "$PROJECT_ROOT/src/server.py" || echo "0")
CONTEXT_COUNT=$(grep -c "ctx: Context" "$PROJECT_ROOT/src/server.py" || echo "0")
STRUCTURED_COUNT=$(grep -c "structured_output=True" "$PROJECT_ROOT/src/server.py" || echo "0")

if [ "$ASYNC_COUNT" -ge 10 ]; then
    check_pass "Found $ASYNC_COUNT async functions"
else
    check_fail "Only $ASYNC_COUNT async functions (expected >= 10)"
fi

if [ "$AWAIT_COUNT" -ge 50 ]; then
    check_pass "Found $AWAIT_COUNT await calls"
else
    check_fail "Only $AWAIT_COUNT await calls (expected >= 50)"
fi

if [ "$CONTEXT_COUNT" -ge 10 ]; then
    check_pass "Found $CONTEXT_COUNT Context parameters"
else
    check_fail "Only $CONTEXT_COUNT Context parameters (expected >= 10)"
fi

if [ "$STRUCTURED_COUNT" -ge 7 ]; then
    check_pass "Found $STRUCTURED_COUNT structured_output=True"
else
    check_fail "Only $STRUCTURED_COUNT structured_output (expected >= 7)"
fi
echo ""

# 5. Try importing key modules
echo "5. Checking module imports..."
cd "$PROJECT_ROOT"

if python3 -c "from src.models import SearchAPIInput, CallAPIInput; print('OK')" 2>/dev/null | grep -q "OK"; then
    check_pass "Models import OK"
else
    check_fail "Models import failed"
fi

if python3 -c "from src.index.api_index import APIIndex; print('OK')" 2>/dev/null | grep -q "OK"; then
    check_pass "APIIndex import OK"
else
    check_fail "APIIndex import failed"
fi

if python3 -c "from src.invoker.handle_registry import HandleRegistry; print('OK')" 2>/dev/null | grep -q "OK"; then
    check_pass "HandleRegistry import OK"
else
    check_fail "HandleRegistry import failed"
fi
echo ""

# 6. Check evaluation.xml
echo "6. Checking evaluation.xml..."
if [ -f "$PROJECT_ROOT/evaluation.xml" ]; then
    if python3 -c "import xml.etree.ElementTree as ET; ET.parse('$PROJECT_ROOT/evaluation.xml')" 2>/dev/null; then
        QA_COUNT=$(python3 -c "import xml.etree.ElementTree as ET; print(len(ET.parse('$PROJECT_ROOT/evaluation.xml').getroot().findall('qa_pair')))" 2>/dev/null || echo "0")
        check_pass "evaluation.xml valid ($QA_COUNT questions)"
    else
        check_fail "evaluation.xml has XML errors"
    fi
else
    check_warn "evaluation.xml not found"
fi
echo ""

# 7. Check dependencies
echo "7. Checking dependencies..."

if python3 -c "import mcp" 2>/dev/null; then
    MCP_VERSION=$(python3 -c "import mcp; print(getattr(mcp, '__version__', 'unknown'))" 2>/dev/null)
    check_pass "MCP SDK installed ($MCP_VERSION)"
else
    check_fail "MCP SDK not installed (pip install mcp[cli])"
fi

if python3 -c "import pydantic" 2>/dev/null; then
    PYD_VERSION=$(python3 -c "import pydantic; print(pydantic.__version__)" 2>/dev/null)
    if python3 -c "import pydantic; assert pydantic.__version__.startswith('2.')" 2>/dev/null; then
        check_pass "Pydantic v2 installed ($PYD_VERSION)"
    else
        check_warn "Pydantic v1 installed ($PYD_VERSION), v2 recommended"
    fi
else
    check_fail "Pydantic not installed"
fi

# Optional: KLayout
if python3 -c "import klayout.db" 2>/dev/null || python3 -c "import pya" 2>/dev/null; then
    check_pass "KLayout available"
else
    check_warn "KLayout not installed (optional for standalone mode)"
fi
echo ""

# Summary
echo "=========================================="
echo "Summary"
echo "=========================================="
if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}✅ All checks passed!${NC}"
    echo ""
    echo "Your KLayout MCP Server is ready to use."
    echo "Run with: python src/server.py"
    exit 0
else
    echo -e "${RED}❌ $ERRORS check(s) failed${NC}"
    echo ""
    echo "Please fix the issues above before using the server."
    exit 1
fi
