#!/usr/bin/env python3
"""
KLayout MCP Server
Model Context Protocol server for KLayout API
"""

import sys
import asyncio
from mcp.server import FastMCP

# 创建 MCP 服务器实例
mcp = FastMCP(name="klayout-mcp-server")

@mcp.tool
def test_klayout_import() -> str:
    """Test if KLayout module is properly imported."""
    try:
        import klayout.db as db
        box = db.Box(0, 0, 10, 10)
        return f"KLayout imported successfully! Box: {box}"
    except Exception as e:
        return f"Error importing KLayout: {str(e)}"

@mcp.tool
def get_klayout_version() -> str:
    """Get KLayout version information."""
    try:
        import klayout.db as db
        return f"KLayout module loaded successfully"
    except Exception as e:
        return f"Error: {str(e)}"

if __name__ == "__main__":
    # 运行 MCP 服务器（使用 stdio 传输）
    mcp.run(transport='stdio')