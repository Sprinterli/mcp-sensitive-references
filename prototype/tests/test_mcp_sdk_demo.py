import asyncio
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "demo"))
from mcp_sdk_server import mcp  # noqa: E402


class McpSdkDemoTests(unittest.TestCase):
    def test_sdk_tool_preserves_structured_string_fields_without_plaintext(self):
        result = asyncio.run(mcp.call_tool("list_customers", {}))
        # SDK 1.x returns (content, structured); SDK 2.x returns a CallToolResult.
        structured_content = result[1] if isinstance(result, tuple) else result.structured_content
        customer = structured_content["customers"][0]
        self.assertIsInstance(customer["email"], str)
        self.assertTrue(customer["email"].startswith("⟦sref:email:"))
        self.assertNotIn("alice@example.com", str(structured_content))
