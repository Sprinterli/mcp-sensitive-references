"""Actual MCP SDK registration for the same reference-bearing customer result."""

from __future__ import annotations

from typing import TypedDict

try:  # MCP SDK 2.x renamed FastMCP to MCPServer.
    from mcp.server.mcpserver import MCPServer as _Server
except ImportError:  # MCP SDK 1.x
    from mcp.server.fastmcp import FastMCP as _Server

from server import DemoMcpServer

mcp = _Server("Sensitive References demo")
_demo = DemoMcpServer()


class Customer(TypedDict):
    customer_id: str
    email: str
    phone: str
    amount: int


class CustomerList(TypedDict):
    customers: list[Customer]


@mcp.tool(structured_output=True)
def list_customers() -> CustomerList:
    """Return customers whose sensitive string fields are canonical Sensitive References."""
    return _demo.list_customers()["structuredContent"]


if __name__ == "__main__":
    mcp.run(transport="stdio")
