"""MCP server exposing the per-round interview prep guides in resources/.

Run with:  fastmcp run mcp/server.py
"""
from __future__ import annotations

import sys
from pathlib import Path

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

# Make the project root importable so we can reuse app.data (the only module that touches disk),
# no matter which directory the server is launched from.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import data  # noqa: E402  (import must follow the sys.path tweak above)

mcp = FastMCP("Interview-guides")


@mcp.tool
def list_guides() -> list[str]:
    """List the available interview prep guides by name (e.g. 'system-design-guide')."""
    return data.list_guides()


@mcp.tool
def get_guide(name: str) -> str:
    """Return the full markdown of one prep guide. Use list_guides() to see valid names."""
    try:
        return data.load_guide(name)
    except FileNotFoundError:
        available = ", ".join(data.list_guides())
        raise ToolError(f"No guide named '{name}'. Available guides: {available}") from None


if __name__ == "__main__":
    mcp.run()
