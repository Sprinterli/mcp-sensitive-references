"""MCP-shaped demo server fixture; no MCP SDK is needed for this protocol exercise."""

from __future__ import annotations

import json

from sensitive_references.issuer import InMemoryIssuer

ISSUER = "https://demo-sensitive-references.example/mcp"
PRINCIPAL = "demo-user"


class DemoMcpServer:
    def __init__(self) -> None:
        self.issuer = InMemoryIssuer(ISSUER)

    def list_customers(self) -> dict:
        email = self.issuer.issue("email", "alice@example.com", principal=PRINCIPAL)
        phone = self.issuer.issue("phone", "+1-555-0100", principal=PRINCIPAL)
        customer = {"customer_id": "C-42", "email": email.token, "phone": phone.token, "amount": 12450}
        return {
            "content": [{"type": "text", "text": json.dumps({"customers": [customer]})}],
            "structuredContent": {"customers": [customer]},
        }


if __name__ == "__main__":
    print(json.dumps(DemoMcpServer().list_customers(), indent=2))
