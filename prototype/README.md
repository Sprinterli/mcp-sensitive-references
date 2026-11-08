# Sensitive References prototype

This is a small, dependency-free feasibility prototype for the Sensitive References MCP extension draft. It demonstrates a server emitting opaque text tokens, a host retaining trusted `(token, issuer)` observations, and a protected local-file sink resolving values without returning plaintext in the model-facing write result.

**Concept 0.7.** The prototype implements the rules of Concept 0.7 for a host and for an issuer: the
discovery object with `sinks`, the sink scopes, the sink profiles `local-file-1`, `process-1` and `display-1`,
consent at every authorization, references per principal (account), `account_hint`, no value without its audit event, and
revocation per device. Section "Concept 0.7" below says what is demo level.

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

The tested configuration is Python 3.14.8 on macOS (POSIX) with `mcp` 2.3.0 and `PYTHONPATH=src`. On
2026-11-08, at commit `65f17e5` (branch `concept-0.7`, Concept 0.7), these commands gave these results:

```bash
cd prototype
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m pytest -q -p no:cacheprovider  # 212 passed, 393 subtests passed
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m unittest discover -s tests     # Ran 212 tests, OK
python tests/tools/mutation_probe.py                                              # see below
```

The new tests of Concept 0.7 are `tests/test_issuer_server.py` (38) and `tests/test_concept_07_host.py` (41).
On a platform without named pipes, the `process-1` tests are skipped. Round 10 of the mutation probe (the
Concept 0.7 guards) killed 60 of 60 mutants on 2026-11-08; the whole probe (rounds 2 to 10) killed 114 of 114. The earlier result (133 tests, 54 of 54 mutants,
2026-10-27, commit `6cdd658`) is in `protocol-package/CONFORMANCE-RESULTS.md` ("Test run").

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
- If the metadata holds the `sensitive_references` object (the name is fixed in Concept 0.7), the object must
  have `resolve_endpoint`, `resolve_scope`, `resolver_profiles`, `sink_profiles` and `sinks` with the right types,
  and must list both profiles. Each member of `sinks` needs a `sink_type` and a `scopes` array that holds the
  resolve scope. `process_scope` and `display_scope` must be the sink scopes that `sinks` names, and
  `max_references` must be an integer of 100 or more. Otherwise the host stops, also when an option is set. The endpoint and the scope come from the object, unless
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
  authorization, token and registration endpoints of the authorization server metadata in the same way. Its
  HTTP client follows no redirect and uses no proxy from the environment. There is no automatic exception for a local MCP
  URL: `--allow-local-targets` enables local mode, only if all DNS addresses of the MCP host are non-public
  (resolved once at connection). Local mode allows the MCP origin and each `--local-origin ORIGIN`, never a
  link-local, unspecified, broadcast or multicast address. Each request of the HTTP client connects to an
  address that the policy checked, so a second DNS answer cannot change the target (DNS rebinding). The
  system browser opens the authorization endpoint; the host does not control its redirects, proxy or DNS
  (`protocol-package/THREAT-MODEL.md`, TM-11).
- The resolver token is a second credential. It comes from the cache file (`--resolver-token-cache`, mode 0600),
  from a refresh, or from a new authorization: dynamic client registration, Authorization Code + PKCE S256, the
  `resource` indicator, the scope set that `sinks` names for the sink profiles of the run (for a file run: the
  resolve scope only), and a redirect to `127.0.0.1`. The host opens the browser and waits
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

### Commands and the screen (`--run-command`, `--reveal`)

`--run-command 'COMMAND {ref}'` uses `process-1`. After the MCP session, the host replaces `{ref}` with the
trusted references of the first call and runs the command once in `/bin/sh`. The host asks on the terminal
before the command runs (`--yes` skips the question). `--reveal` uses `display-1`. The host offers each
trusted reference on the terminal; "y" shows its value on the terminal (`/dev/tty`), never on stdout or
stderr. Without a terminal there is no explicit action of the person, so the host reveals nothing. The host
asks for the scope set of every sink of the run in one authorization. The report holds counts, the program
name and the exit status, never a value or a reference.

```bash
python3 demo/mcp_host.py --url https://server.example/mcp --extension-id <identifier> \
    --tool <read tool> --expect-negotiation --reveal --run-command 'docker login -u app --password-stdin registry.example <<EOF
{ref}
EOF'
```

The value reaches the shell through a pipe. The shell puts it where the reference stands. In an argument, the
program gets the value in its argument list, which other processes of the computer can read. So put the
reference where the program reads it from its standard input, as in the here-document above.

The tests in `tests/test_mcp_host_resolve.py` run offline. A local server plays the protected-resource metadata,
the authorization server and the resolve endpoint. Two tests run `mcp_host.main` against a real MCP SDK 2.x server.
The protocol gaps that this work found are in `M4-FINDINGS.md`.

## Concept 0.7

### The prototype issuer

`src/sensitive_references/issuer_server.py` is a dependency-free issuer: an authorization server and a resolve
endpoint for one protected resource, in memory. `IssuerHttp` serves it on a loopback port. It implements the
server rules of `RESOLVER-PROFILE.md`:

- The discovery object names `sinks` with the scope set of each sink profile, and `process_scope` and
  `display_scope` (section 4). The prototype publishes `process-1` (OQ-21).
  The resolve scope and the sink scopes are not in `scopes_supported`.
- The authorization server accepts the resolve scope, plus sink scopes that it offers, plus `openid`. Every other
  combination gets `invalid_scope` and no code (section 5.2). A refresh keeps the granted set and adds no scope
  (section 5.3).
- A token without the sink scope of the `sink_type` gets `403 insufficient_scope` before any lookup, with no
  value and no audit event. The `WWW-Authenticate` header and the body name the whole scope set and an
  `error_description` (section 5.4).
- Every authorization request gets the consent page; a stored approval never replaces it (section 10.1). The
  page names the account with a "Use another account" action, the client, the loopback host and port, the time
  of the request, the resource and one line per sink scope (section 10.2). The consent post and the switch need a
  single-use nonce bound to the browser session and the `Origin` of the server.
- A loopback redirect URI takes any port; everything else must match (section 9.2). Registration takes only
  `http://127.0.0.1` redirect URIs.
- The server looks up a reference only in the records of the token subject. A reference of another person is
  `409 unresolvable` with the reason `unknown` (section 12.2). Token and refresh answers carry `account_hint`
  (section 11.2).
- The audit event is written before the values. If the write fails, the answer is `503 audit_unavailable`
  (section 15). For `process-1` the event keeps the program name or `other`; for `display-1`, `screen`.
- A display request needs the destination `screen` and exactly one reference (DISPLAY-PROFILE.md, section 3).
- The person and an administrator list and revoke a device (a principal and a client). Every credential
  carries the epoch of its device; the revocation raises the epoch first, and the write of a new credential
  checks it in the same locked step (section 10.4).

**Demo level.** The accounts and passwords are fixtures, there is no identity provider and no persistence. The
server keeps no refusal line in its audit. The minimum audit content (OQ-18) and rate limits beyond a daily
quota are not implemented. The issuer serves no MCP endpoint: `POST /mcp` answers 401 with the
`resource_metadata` challenge only.

### The host sinks

- `src/sensitive_references/process_sink.py` (`process-1`). The destination is the program name: the first word
  after `NAME=value` assignments, its last path part. Each occurrence of a trusted reference becomes a command
  substitution that reads a named pipe. The host resolves all references of the command in one step when the
  command opens the first pipe, so a refused command, or a command that never reads a value, costs no resolve.
  A failed resolve kills the command; it ends with status 97 and gets no value. The value is never in the
  command line of the shell; where the reference stands in an argument, the program gets the value in its own
  argument list. The host collects the whole
  output and masks every released value before the model sees it, also after a non-zero status, a signal or a
  timeout.
- `src/sensitive_references/display_sink.py` (`display-1`). A reveal needs a `UserAction` object, which only the
  user interface makes. One action resolves one reference, with `sink_type` `display` and the destination
  `screen`. The value goes to the screen callback only; `reveal` returns nothing. The host keeps the value, so
  a paste is masked back and a second action sends no request. A copy needs a second action on a shown value.
  The default limit is 20 resolves per session.
- `output_guard.SessionMask` keeps the released values of the session and masks them in later text.

**Demo level, and what it does not cover.**

- `process-1` runs on POSIX only. On another platform the host does not declare `process-1` and does not ask
  for the process scope.
- The mask finds a value in clear text, percent-encoded and in base64 (standard and URL-safe). A program that
  changes the value in another way, writes it to a file or sends it to the network passes the mask
  (PROCESS-PROFILE.md, section 7). There is no sandbox.
- A reference in a command must stand where the shell expands a command substitution (unquoted or in double
  quotes). Each pipe gives its value once, so a command that reads one occurrence twice waits until the timeout.
- The `display-1` screen of `mcp_host.py` is the terminal (`/dev/tty`). A screen share, a screenshot or a
  terminal log sees the value (DISPLAY-PROFILE.md, section 7). The host has no clipboard copy.
- The host prints `account_hint` on stderr for the person. It never puts it in the report or uses it for a
  decision.

### Demo

`demo/concept07_demo.py` starts the issuer on loopback and runs the three sinks with one authorization. The
consent page opens in the system browser (account `demo@example.com`, password `demo`); `--headless` uses the
scripted browser of `demo/scripted_browser.py`. `--reveal` asks on the terminal before each reveal.

```bash
PYTHONPATH=src python3 demo/concept07_demo.py --headless
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
- `oidc.py` and `http_resolver.py` are early probes for the Keycloak demos. They use `urlopen` and do not
  apply the SC-01 fetch policy, the redirect rule or the address binding. The test host does not use them,
  and they are not a conformant implementation of the profile.
- `src/sensitive_references/output_guard.py` — re-redacts only values from the current protected operation if a downstream action echoes them.
- `src/sensitive_references/capabilities.py` — version/profile intersection before the host records provenance.
- `src/sensitive_references/resolver_client.py` — host-side `oauth-resolver-1` client: resource and authorization-server discovery, token cache, PKCE with a loopback redirect, and the resolve call.
- `M4-FINDINGS.md` — protocol gaps found when the test host materialized references.
- `src/sensitive_references/sink_profiles.py` — the sink profiles of Concept 0.7, their `sink_type` and scopes.
- `src/sensitive_references/issuer_server.py` — the prototype issuer of Concept 0.7 (authorization server and
  resolve endpoint) and its loopback HTTP server.
- `src/sensitive_references/process_sink.py` and `display_sink.py` — the host sinks `process-1` and `display-1`.
- `demo/scripted_browser.py` and `demo/concept07_demo.py` — a scripted browser for the consent page, and the
  Concept 0.7 demo.
