"""End-to-end host simulation. It never prints the materialized plaintext."""

from pathlib import Path

from server import DemoMcpServer, ISSUER, PRINCIPAL
from sensitive_references import InMemoryResolver, ProtectedFileSink, ProvenanceStore, ResolverAuthorization


def main() -> None:
    server = DemoMcpServer()
    result = server.list_customers()
    host = ProvenanceStore()
    host.observe_mcp_result(ISSUER, extension_negotiated=True, result=result)
    authorization = ResolverAuthorization()
    authorization.grant(ISSUER, PRINCIPAL)
    sink = ProtectedFileSink(host, InMemoryResolver({ISSUER: server.issuer}, authorization), principal=PRINCIPAL)
    token = result["structuredContent"]["customers"][0]["email"]
    model_content = f"Name,Email\nCustomer 42,{token}\n"
    written = sink.write(Path(__file__).parent / "output" / "customers.csv", model_content)
    print("Model-facing content:")
    print(written.model_facing_content)
    print(f"Materialized protected file: {written.path}")


if __name__ == "__main__":
    main()
