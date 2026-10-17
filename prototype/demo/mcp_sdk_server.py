"""Actual MCP SDK registration for the same reference-bearing customer result."""

from __future__ import annotations

from typing import TypedDict

from mcp.server.fastmcp import FastMCP

from server import DemoMcpServer

mcp = FastMCP("Sensitive References demo")
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
