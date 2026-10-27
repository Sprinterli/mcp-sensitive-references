# Threat model delta for `oauth-resolver-1` and `local-file-1`

**Status: proposed change, experimental.** This file adds to [SECURITY-MODEL.md](../SECURITY-MODEL.md). It
does not replace it. The trust boundaries and the required controls of that file stay valid.

## New assets

The two profiles add these assets to the model of concept 0.5:

- **The resolver token.** An OAuth access token and a refresh token that release plaintext values.
- **The consent record.** The approval of one user for one resolver client, one resource, the resolve
  scope and the set of sink profiles that the consent page showed (SC-06).
- **The resolve endpoint.** An HTTP endpoint that returns plaintext to a program outside the model.
- **The token cache of the host.** A local file that holds the resolver tokens.
- **The destination.** The local file that receives plaintext, and its path.

## Threats

Each threat has an id, a description, the control that the implementations use, the evidence, and the
residual risk.

### TM-1. Consent bypass

**Threat.** A local program that can open the browser of the user gets a resolver token without the
knowledge of the user. The browser session of the user signs the request.

**Control.** The authorization server shows a consent page for the first authorization of a client. A
browser session alone issues no code. The page cannot be framed. A one-time nonce binds the answer to the
user and to every request parameter. The consent post must carry a same-origin `Origin` header. SC-06
also binds the approval to the resource, the resolve scope and the sink profiles that the page names, so
that a later profile needs a new decision.

**Evidence.** Reference server tests `test_the_first_authorization_shows_a_consent_page_and_issues_no_code`,
`test_consent_cannot_be_given_without_the_users_own_answer_on_the_page` and
`test_a_consent_post_without_an_origin_header_grants_nothing`. The binding to resource, scope and profile
set is **not verified** in the reference server.

**Residual risk.** After consent, a program that can read the token cache of the host can use the token
without interaction (see TM-8). The consent page names the client and its return host. A user can still
approve a malicious client that has a plausible name. The page does not show the destination. This
package did not verify that the page of the reference server names the resource and the sink profiles.

### TM-2. Token class confusion

**Threat.** A resolver token works as an agent token, so a resolver client gets MCP tool access. Or an
agent token works at the resolve endpoint, so the MCP client gets plaintext.

**Control.** The resolver token is its own class with its own prefix and its own server-side record. Every
agent-token reader refuses it. The resolve endpoint accepts nothing else (SC-05). The host compares the
resolver token with the agent token and refuses to send an equal token.

**Evidence.** Reference server tests `test_a_resolver_token_is_refused_where_an_agent_token_is_expected`
and `test_an_agent_token_is_refused_at_the_resolve_endpoint`. Host test `test_the_agent_token_is_never_sent`.

**Residual risk.** A server that adds a new agent-token reader must keep the refusal. A test pins one
reader only (TM-3).

### TM-3. Bearer readers that match a suffix

**Threat.** An agent-token reader accepts a bearer by its suffix or by a truncated lookup. A resolver token
with a matching suffix passes that reader. The reference server had such a reader (plan section 6, M4,
"What the OAuth layer has today"; Gate A finding LOW).

**Control.** The reader refuses a bearer with the resolver prefix before the suffix lookup.

**Evidence.** Reference server test `test_a_resolver_token_never_reaches_the_agent_suffix_lookup`.

**Residual risk.** The control depends on a prefix. A generic rule for every server is SC-05: "more than
the scope" separates the classes. A server without a prefix needs another separation.

### TM-4. Mixed-scope requests

**Threat.** A client requests the resolve scope together with agent scopes. One token then carries both
rights. A generic MCP client that requests every scope in `scopes_supported` does this without intent.

**Control.** The authorization server refuses a request that mixes the resolve scope with other scopes
(`invalid_scope`). The server does not list the resolve scope in `scopes_supported` (SC-03).

**Evidence.** Reference server tests `test_a_request_that_mixes_the_resolve_scope_with_agent_scopes_gets_neither`
and `test_the_resolve_scope_stays_out_of_scopes_supported`.

**Residual risk.** A host learns the scope from the discovery object. If an attacker controls that object,
see TM-5.

### TM-5. Issuer confusion

**Threat.** The host records the wrong issuer for a reference, or resolves a reference at the wrong
endpoint. Variants:

- The metadata names another `resource`, so the host sends a token for one resource to another.
- A discovered resolve endpoint lies on another origin and receives a token for the resource.
- An HTTP redirect carries the `Authorization` header to another origin.
- The authorization server metadata names another issuer, or the authorization response comes from
  another authorization server (mix-up).
- The MCP URL and the RFC 9728 `resource` differ, and the host picks one by guess (F12, P16).

**Control.** The host keeps the issuer string as given, compares `resource` as an exact string and
requires that it is identical to the MCP URL (SC-01). It gets the metadata only from the two locations of
RFC 9728 and never from the origin root. The test host accepts a parent resource only through an explicit operator option
(`--resource`). That option is a non-conformant tolerance for the reference server (P16). The host accepts a resolve endpoint, discovered or configured, only on the resource origin (SC-04). Without metadata the host stops, unless the operator states that the server has none. The host follows no
redirect. The host checks the RFC 8414 issuer and the RFC 9207 `iss` parameter (SC-08). Metadata
without the discovery object stops the host, unless the operator states that the server publishes none
(SC-02); the report then labels the run as not conformant.

**Evidence.** Host tests `test_metadata_for_another_resource_is_refused`,
`test_a_discovered_cross_origin_endpoint_is_refused`, `test_a_configured_cross_origin_endpoint_is_refused`,
`test_unreachable_metadata_fails_closed`, `test_a_redirect_from_the_resolve_endpoint_is_not_followed`,
`test_a_callback_from_another_issuer_is_refused`, `test_a_resource_the_mcp_url_is_not_under_stops_the_host`,
`test_a_near_miss_of_the_issuer_is_refused`, `test_root_metadata_is_not_a_fallback_for_a_resource_with_a_path`,
`test_challenge_metadata_for_another_resource_is_refused` and
`test_a_callback_without_iss_is_refused_when_the_server_advertises_iss`.
Host test `test_authorization_server_metadata_for_another_issuer_is_refused` covers the RFC 8414 check.

**Residual risk.** The issuer identity is a URL, not a cryptographic identity (P10). An attacker who
controls DNS and a valid TLS certificate for the origin controls the issuer. With `--no-resource-metadata`
the host checks no resource identity: the operator statement replaces it.

### TM-6. Partial materialization

**Threat.** The sink writes some values and fails on others. A partial file can mislead a later process.
Or the server releases values for a batch that the host then discards.

**Control.** The host resolves every batch before it writes. The host writes a temporary file and replaces
the destination atomically. A failure leaves the destination unchanged (`local-file-1`, L9 to L11).

**Evidence.** Host tests `test_a_partially_invalid_batch_writes_nothing`,
`test_an_incomplete_or_extra_batch_writes_nothing` and `test_an_unreachable_resolve_endpoint_writes_nothing`.

**Residual risk.** If the host splits the references, the server releases the values of each successful
batch. If a later batch fails, the host discards them, but the values were in host memory and the server
audit shows a release (F7, SC-09). A crash between the write of the temporary file and the replace can
leave a temporary file with plaintext in the destination directory. That case is not tested.

### TM-7. Destination disclosure to the server

**Threat.** The resolve request carries the absolute local path. The path tells the server the layout of
the local file system, for example a user name in a home directory (F8).

**Control.** None in the test host today. The reference server checks only the length of the value and
does not write it to its audit event (read in its source).

**Evidence.** `prototype/src/sensitive_references/resolver_client.py`, `OAuthHttpResolver._batch`. Not
asserted by a test.

**Residual risk.** Open until SC-10 is accepted. The proposed change sends a label or a hash.

### TM-8. Token cache on the host

**Threat.** Another operating-system user, or another process of the same user, reads the token cache and
uses the resolver token or the refresh token.

**Control.** The host writes the cache with mode 0600 through a temporary file and an atomic replace. The
host refuses a cache file that others can read and does not repair it. A refresh token rotates and works
only for its own client (SC-07).

**Evidence.** Host tests `test_interactive_authorization_materializes_and_reports_no_secret` (mode 0600) and
`test_a_cache_file_that_others_can_read_is_refused`. Reference server tests
`test_refresh_rotates_and_the_old_refresh_token_is_dead` and `test_a_refresh_token_works_only_for_its_own_client`.

**Residual risk.** A process with the same operating-system privileges as the host can read the cache. This
matches the limit in `SECURITY-MODEL.md`, "Limits". The tokens are not sender-constrained (OQ-5). A stolen
refresh token works until the next rotation or until the consent ends. If the host stops after the server
rotated the token and before the host wrote the cache, the refresh token is lost and the user must
authorize again (F6).

### TM-9. Plugin hosts that cannot verify negotiation

**Threat.** A host that works through hooks sees tool results but not the negotiated capabilities, and not
an authenticated issuer. It treats token-shaped text as a reference. It can resolve a token from a file,
a web page or a model reply (P6, P11).

**Control.** Such a host is not a supporting host and must not declare the extension (SC-19). A server
renders canonical tokens only for a session that declared the extension (SC-16).

**Evidence.** Host tests `test_an_unobserved_or_forged_reference_is_not_sent` and
`test_without_negotiation_no_provenance_is_recorded_and_a_token_fails`. Production run E5 (legacy sessions
got no references).

**Residual risk.** A server cannot tell a supporting host from a host that declares the extension falsely.
The declaration is a claim of the client. A false declaration gives the client canonical tokens but no
plaintext, because resolution needs a separate consented resolver token.

### TM-10. A copied reference in an issuer-side sink

**Threat.** A model or an attacker copies a reference of another principal into the arguments of a tool
call. The issuer resolves it into its own outbound call, because the reference is valid and current.
Possession of the reference then acts as authorization.

**Control.** Possession of a reference does not authorize resolution. The issuer resolves a reference into
an issuer-side sink only after an explicit authorization decision for the tool execution. The decision uses
the authenticated principal, the authorized tool and action, and the owner of the reference. A reference of
another principal resolves nothing. No additional user confirmation is required (SC-18).

**Evidence.** **Not verified.** This package found no reference server test for an authorized tool call
with the reference of another principal.

**Residual risk.** Inside one principal, the control does not stop an injected instruction that moves a
value between two tools that the principal is authorized for (see the accepted risks below).

### TM-11. Server-side request forgery through discovery URLs

**Threat.** A remote MCP server names a URL that the host then fetches: the `resource_metadata` URL of its
challenge, an authorization server in its RFC 9728 metadata, or an endpoint in the authorization server
metadata. The URL points to a loopback, private or link-local address, for example a cloud metadata
service or an administration interface on the network of the user. The host sends a request into a
network that the server cannot reach itself (RFC 9728 section 7.7).

**Control.** The host applies a fetch policy (SC-01, profile rule D11). Before each request it resolves
the host name by DNS. It refuses an address that is not globally reachable (the IANA special-purpose
registries, plus multicast, site-local and an embedded IPv4 address that is not globally reachable), and
a name that does not resolve. It checks the authorization, token and registration endpoints of the
authorization server metadata when it reads the metadata, also the authorization endpoint that only the
browser opens. For the requests of its own HTTP client, the host follows no redirect and uses no proxy
from the environment, so a public URL cannot forward such a request to a private one. The system browser
opens the authorization endpoint. The host does not control the redirects, the proxy and the DNS
resolution of the browser; the residual risk below names that.

There is no automatic exception for a local MCP URL. Local mode needs an explicit operator option, and
all DNS addresses of the MCP host must be non-public. The host resolves the MCP host once, at
connection, and keeps that result. In local mode the host allows only the MCP origin and origins that the
operator configures, and never a link-local address (with 169.254.169.254), an unspecified, a broadcast
or a multicast address.

**Evidence.** `FetchPolicyTests` in `prototype/tests/test_mcp_host_resolve.py`: loopback, private, IPv6
unique-local, link-local, mixed and unresolvable targets for a public MCP URL, at the challenge, the
authorization server, its endpoints and the resolve endpoint; the address cases of the definition,
with IPv4-mapped, IPv4-compatible, NAT64 and 6to4 addresses; local mode only with the operator option,
not with mixed DNS records of the MCP host, only for the MCP origin and configured origins, never for
169.254.169.254 or another subnet, and with the DNS answer kept from the connection.
`NoRedirectNoProxyTests`: no client follows a redirect, and no client uses a proxy from the environment.
The fixtures on 127.0.0.1 use local mode through the option.

DNS rebinding: SC-01 requires that the host connects to an address that it checked, for each request of
the fetch policy that its own HTTP client sends. The test host does that (`test_the_request_connects_to_the_checked_address`). The
browser opens the authorization endpoint and resolves its name again. The host checks that name only
before it opens the browser.

**Residual risk.** A DNS server can answer the browser with a non-public address for the authorization
endpoint, after the check of the host, or the endpoint can redirect the browser to such an address. The
browser then sends a top-level GET request with the
authorization parameters to that address. The request carries no credential of the host. The HTTP client
of the MCP SDK resolves the MCP host again for the MCP session, so DNS rebinding can change the target of
the session; the MCP URL comes from the operator. For a request of the fetch policy, a host that resolves the name again for the connection does not
conform to SC-01, and
a DNS server that answers with a public address first and with a private address second passes its check.
In local mode,
a malicious local MCP server can reach other paths on its own origin and on the configured origins. The
operator accepts that when it enables local mode.

### TM-12. A credential in the query of the MCP URL

**Threat.** SC-01 makes the MCP URL with its query the issuer identity. If an operator puts a credential
into the query, for example `https://mcp.example.com/mcp?api_key=...`, the host sends that string as the
RFC 8707 `resource` parameter to the authorization server, keys its token cache with it and records it
with each observation. The credential then reaches the authorization server, its logs and the cache file.

**Control.** The proposed text of SC-01 says that a server SHOULD NOT put a credential into the query of
its MCP URL, and RFC 9728 section 1.2 says that a resource identifier SHOULD NOT include a query
component. The test host refuses user information in the URL, and its report shows the URL without the
query (`public_endpoint`).

**Evidence.** Host tests `test_a_url_with_user_information_or_a_fragment_is_no_issuer` and
`test_the_report_holds_no_user_information_and_no_query`. No test refuses a credential in the query: the
host cannot tell a credential from a tenant name.

**Residual risk.** A server that needs a credential in the query exposes it to the authorization server
and to the token cache. The host cannot detect this.

## Accepted residual risks of the reference server

The plan of the reference server accepts these risks (plan section 0 and section 8). They are not
consequences of the two profiles, but a reader of a SEP needs them:

- An injected instruction can move a value between authorised tools of the same principal through the
  issuer-side sink (SC-18). The authorization decision of SC-18 limits this to references that the
  principal owns and to tools and actions that the principal is authorized for. It does not stop it.
- The echo guard recognises a resolved value in known encodings. It does not prove absence. A transformed
  echo passes (plan section 8).
- A connector that logs its own exception can write a resolved value into a log line before the guard runs.
