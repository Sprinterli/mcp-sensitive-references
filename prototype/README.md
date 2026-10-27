# Sensitive References prototype

This is a small, dependency-free feasibility prototype for the Sensitive References MCP extension draft. It demonstrates a server emitting opaque text tokens, a host retaining trusted `(token, issuer)` observations, and a protected local-file sink resolving values without returning plaintext in the model-facing write result.

The core remains dependency-free. `demo/mcp_sdk_server.py` is an additional MCP SDK registration probe. It uses `MCPServer` (MCP SDK 2.x) and falls back to `FastMCP` (MCP SDK 1.x). It does not implement OAuth transport, persistence, policy, or a filesystem sandbox.

## Run

Use Python 3.10 or later.

```bash
cd prototype
python3 -m pip install -e '.[mcp-demo,resolver-http-demo]'
python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 demo/client.py
PYTHONPATH=src python3 -m unittest tests.test_mcp_sdk_demo -v
```

### Supported configuration

The tested configuration is Python 3.14.8 with `mcp` 2.3.0 and `PYTHONPATH=src`. On 2026-10-27 these
commands gave these results:

```bash
cd prototype
PYTHONPATH=src python -m pytest -q                  # 126 passed, 175 subtests passed
PYTHONPATH=src python -m unittest discover -s tests # Ran 126 tests, OK
```

The tested commit is recorded in `protocol-package/CONFORMANCE-RESULTS.md` ("Test run").

MCP SDK 1.x was not tested in this run. An earlier version of this file named `mcp` 1.21.0 for the SDK
probe. That result is older than the 2.x change and was not repeated.

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
  credentials, query or fragment. The host keeps every other character as given (no change of case, port or
  trailing slash) and compares issuers as exact strings. **This issuer identity is experimental.** A URL is a locator, not an
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

### Materialization through a resolver (`--resolve-into`)

With `--resolve-into PATH`, the host also resolves references into a local file. It uses the
`oauth-resolver-1` and `local-file-1` profiles of `EXTENSION-PROFILE-DRAFT.md`. After the MCP session, the host
writes `--materialize-template` (default `{ref}` and a newline) once for each reference of the first call that
has exactly one trusted issuer. It writes through `ProtectedFileSink`, so a failure leaves the file as it was.

- The host declares both profiles. It resolves only if both are in the negotiated intersection.
- The host reads the RFC 9728 protected-resource metadata of the MCP URL in the order of the MCP authorization
  specification, with one difference. First it sends a request without a token to the MCP URL. If the 401 answer
  names a `resource_metadata` URL in `WWW-Authenticate`, the host reads that URL only. Else it reads the
  path-inserted well-known URL (RFC 9728 section 3.1). The query and a trailing slash of the MCP URL stay in that
  URL. The host never tries the origin root, which the MCP specification allows as a last fallback (SC-01). The
  metadata `resource` must be the MCP URL as an exact string. The issuer is the MCP URL exactly as given. A URL
  with user information or a fragment stops the host. The report shows the URL without user information and query.
- If the metadata holds the provisional `sensitive_references` object, the object must have `resolve_endpoint`,
  `resolve_scope`, `resolver_profiles` and `sink_profiles` with the right types, and must list both profiles.
  Otherwise the host stops, also when an option is set. The endpoint and the scope come from the object, unless
  `--resolve-endpoint` or `--resolve-scope` replaces them. The endpoint must be on the origin of the resource, also
  when it is configured (SC-04). The host refuses an endpoint on another origin.
- The authorization server metadata must name the configured or discovered issuer and must list `S256` in
  `code_challenge_methods_supported`. If the member is absent or malformed, the host stops.
- **Without metadata the host stops.** This applies when no metadata exists and when the server does not answer.
  It applies also when the 401 answer names a `resource_metadata` URL that gives no document: then the option
  below does not help, because the challenge says that metadata exists.
  If the server publishes no RFC 9728 metadata, the operator can set `--no-resource-metadata`. Then the host needs
  `--resolve-endpoint` and `--authorization-server`. **This mode is not conformant to SC-01 or SC-02**
  (`protocol-package/SPEC-CHANGES.md`): the host checks no resource identity and no discovery object. The host still
  checks that the endpoint is on the origin of the MCP URL.
- **Metadata without the object stops the host.** If the metadata has no `sensitive_references` object, the
  host stops, also with `--resolve-endpoint`. Only `--no-discovery-object` (the operator says that the server
  publishes no object) selects configuration mode: the host needs `--resolve-endpoint`, and the scope is
  `--resolve-scope`, else `sensitive-references.resolve`. This mode checks SC-01 but is not SC-02 conformant.
  `--resource` (a parent resource, for a server with the known deviation P16) is not SC-01 conformant.
- **Non-conformant runs are labelled.** The report field `materialization.non_conformant` lists each deviation
  that `--no-resource-metadata`, `--no-discovery-object` or `--resource` selected. It is empty for a run that
  follows SC-01 and SC-02.
- **Fetch policy (SC-01, D11, RFC 9728 section 7.7).** Before each request, the host resolves the host name and
  refuses an address that is not globally reachable, and a name that does not resolve. It checks the
  authorization, token and registration endpoints of the authorization server metadata in the same way. It
  follows no redirect and uses no proxy from the environment. There is no automatic exception for a local MCP
  URL: `--allow-local-targets` enables local mode, only if all DNS addresses of the MCP host are non-public
  (resolved once at connection). Local mode allows the MCP origin and each `--local-origin ORIGIN`, never a
  link-local, unspecified, broadcast or multicast address. Each request connects to an address that the
  policy checked, so a second DNS answer cannot change the target (DNS rebinding).
- The resolver token is a second credential. It comes from the cache file (`--resolver-token-cache`, mode 0600),
  from a refresh, or from a new authorization: dynamic client registration, Authorization Code + PKCE S256, the
  `resource` indicator, the resolve scope only, and a redirect to `127.0.0.1`. The host opens the browser and waits
  for the redirect. Use `--no-browser` to print the page URL to stderr, and `--no-interactive` to use the cache only.
- The host never sends the MCP agent token to the resolve endpoint. It does not follow redirects. After a 401, it
  gets one new token and tries once again.
- The report holds `materialized`, the count of sentinel values in the file, whether the model-facing content still
  holds the references, the token source (`cache`, `refresh`, `interactive`) and a failure code. It never holds a
  reference, a value or a credential.

```bash
export MCP_TOKEN=...                  # the agent token, for the MCP endpoint only
export SREF_SENTINELS='a@example.com' # values that must reach the file, never the report
python3 demo/mcp_host.py --url https://server.example/mcp --extension-id <identifier> \
    --tool <read tool> --arguments '{...}' --expect-negotiation \
    --resolve-into ./out.txt --resolver-token-cache ~/.config/sref/resolver-tokens.json
# Optional: --resolve-endpoint URL --resolve-scope SCOPE --authorization-server ISSUER --no-resource-metadata
#           --no-discovery-object
#           --resolver-client-id ID --materialize-template 'To: {ref}\n' --no-browser --no-interactive
```

The tests in `tests/test_mcp_host_resolve.py` run offline. A local server plays the protected-resource metadata,
the authorization server and the resolve endpoint. Two tests run `mcp_host.main` against a real MCP SDK 2.x server.
The protocol gaps that this work found are in `M4-FINDINGS.md`.

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
- `src/sensitive_references/resolver_client.py` — host-side `oauth-resolver-1` client: resource and authorization-server discovery, token cache, PKCE with a loopback redirect, and the resolve call.
- `M4-FINDINGS.md` — protocol gaps found when the test host materialized references.
