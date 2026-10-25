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

## Independent MCP test host

`demo/mcp_host.py` is a host for any MCP server that implements the extension. It connects by URL with the
MCP SDK client, declares the extension (or, with `--legacy`, nothing), and checks every tool result as a host
receives it, before a model sees it:

- the server advertised the extension with a version the host declared;
- each canonical token gets a trusted observation with its issuer: the server URL the host connected to, without
  credentials, query or fragment. **This issuer identity is experimental.** A URL is a locator, not an
  independently verified issuer identity (a TLS origin at best); which identity a host should record is an open
  question, and the RFC 9728 resource identifier is one candidate;
- every reference-like string in the result is a canonical token, and no sentinel value appears;
- a host that declared nothing sees no canonical token.

A second call may pass an observed reference (`{ref}` in `--then-arguments`); only a reference with exactly one
trusted issuer is sent. The extension identifier is not fixed by concept 0.5, so it is a required option.
Credentials and sentinel values come from the environment and are never printed; the report holds counts and
verdicts.

```bash
python3 -m venv .venv-host && . .venv-host/bin/activate
pip install -e '.[mcp-host]'
export MCP_TOKEN=...                 # the server's bearer token
export SREF_SENTINELS='a@example.com' # values that must never reach the model
python3 demo/mcp_host.py --url https://server.example/mcp --extension-id <identifier> \
    --tool <read tool> --arguments '{...}' --expect-negotiation \
    --then-tool <write tool> --then-arguments '{"text": "to {ref}"}'
python3 demo/mcp_host.py --legacy --url https://server.example/mcp --extension-id <identifier> --tool <read tool>
```

The host's checks are tested without a network in `tests/test_mcp_host.py`. In a run against one server every
token has that one issuer, so the live run shows that observations are recorded only after negotiation; the
fail-closed path for a token seen from two issuers is shown by the unit test. With `--expect-success`, a
call fails the run when it returns `isError` or when a structured field (`error_code`, `code`, `error`) names a
reference failure (`--refusal-pattern`; the default matches the failure reasons of concept 0.5), because a
server may report a refused resolution inside a successful result. The report holds the endpoint without
credentials, query or fragment, counts and verdicts; never a token, a sentinel value or a server message.

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
