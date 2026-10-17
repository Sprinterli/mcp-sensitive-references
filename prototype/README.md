# Sensitive References prototype

This is a small, dependency-free feasibility prototype for the Sensitive References MCP extension draft. It demonstrates a server emitting opaque text tokens, a host retaining trusted `(token, issuer)` observations, and a protected local-file sink resolving values without returning plaintext in the model-facing write result.

The core remains dependency-free. `demo/mcp_sdk_server.py` is an additional FastMCP SDK registration probe, tested against locally installed `mcp` 1.21.0. It does not implement OAuth transport, persistence, policy, or a filesystem sandbox.

## Run

Use Python 3.10 or later.

```bash
cd prototype
python3 -m pip install -e '.[mcp-demo,resolver-http-demo]'
python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 demo/client.py
PYTHONPATH=src python3 -m unittest tests.test_mcp_sdk_demo -v
```

The demo prints only model-facing reference text and the path of the protected file. It writes the materialized CSV to `demo/output/customers.csv` so it can be inspected locally; it deliberately does not echo its content.

For the optional Keycloak probes, start the isolated development container. Its `admin` credentials are
fixed test fixtures. Do not use this configuration outside local development.

```bash
cd demo
docker compose -f keycloak-compose.yml up -d
cd ..
```

The probes create and remove isolated realm objects. They verify a Keycloak-signed resolver JWT through
the issuer JWKS and send it through the issuer-bound HTTP resolver path without printing credentials,
tokens, or plaintext:

```bash
PYTHONPATH=src python3 demo/keycloak_oidc_probe.py
PYTHONPATH=src python3 demo/keycloak_pkce_probe.py
```

## Mechanics demonstrated

- `DemoMcpServer.list_customers()` returns normal MCP-shaped `content` and `structuredContent`; sensitive string fields contain canonical `⟦sref:kind:opaque-id⟧` tokens.
- `ProvenanceStore` accepts references only from an authenticated-result simulation where the extension was negotiated. It does not derive an issuer from token text.
- `ProtectedFileSink` resolves only trusted, unambiguous references, using `Resolver.resolve(issuer, references, sink_context)`.
- `InMemoryResolver` requires separate resolver authorization. A reference token alone is insufficient.
- Resolution validates all values before returning any values to the sink, so an invalid batch leaves the destination untouched.

## Layout

- `src/sensitive_references/reference.py` — canonical token grammar and opaque IDs.
- `src/sensitive_references/provenance.py` — trusted host observations and issuer ambiguity handling.
- `src/sensitive_references/issuer.py` — in-memory immutable-generation issuer registry and revocation.
- `src/sensitive_references/resolver.py` — resolver interface and fake authorization/profile implementation.
- `src/sensitive_references/sink.py` — atomic protected local-file materialization.
- `demo/` — MCP-shaped server fixture and host simulation.
- `tests/` — focused security and workflow tests.
- `EXTENSION-PROFILE-DRAFT.md` — concrete candidate host, OAuth resolver, and local-file sink semantics.
- `CONFORMANCE.md` — security-property-to-evidence matrix and remaining standardization work.
- `POC-FINDINGS.md` — evidence-backed questions and recommendations for a community discussion.
- `COMMUNITY-DISCUSSION-POC-ADDENDUM.md` — implementation evidence to append to the existing pre-SEP discussion draft.
- `schema/sensitive-references-settings.schema.json` — candidate settings-object schema for the standard MCP extensions map.
- `COMPLETION-AUDIT.md` — requirement-by-requirement evidence for the prototype scope.
- `src/sensitive_references/oidc.py` and `resolve_http.py` — PKCE/OIDC and a non-model resolver-endpoint PoC.
- `src/sensitive_references/http_resolver.py` — host adapter that calls only issuer-configured resolver endpoints and rejects partial responses.
- `src/sensitive_references/output_guard.py` — re-redacts only values from the current protected operation if a downstream action echoes them.
- `src/sensitive_references/capabilities.py` — version/profile intersection before the host records provenance.
