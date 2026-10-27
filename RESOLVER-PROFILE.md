# Resolver profile `oauth-resolver-1`

**Status: Concept 0.6 draft, normative profile.** The conventions and terms of
[SPEC-DRAFT.md](SPEC-DRAFT.md#1-conventions) apply. This profile builds on the core documents. It does not
need any other document.

The profile defines how a host gets a separate OAuth resolver token and how it calls a resolve endpoint of
the issuer. Each rule names a provisional decision where one applies. The evidence for each rule is in
[protocol-package/PROFILE-oauth-resolver-1.md](protocol-package/PROFILE-oauth-resolver-1.md) and
[protocol-package/CONFORMANCE-RESULTS.md](protocol-package/CONFORMANCE-RESULTS.md).

## 1. Scope

The profile uses OAuth 2.0 Authorization Code with PKCE (RFC 7636), resource indicators (RFC 8707),
protected-resource metadata (RFC 9728), authorization server metadata (RFC 8414) and the authorization
response `iss` parameter (RFC 9207). It applies to an MCP server over HTTP.

## 2. Roles

| Role | Function |
|---|---|
| Protected resource | The MCP server. Its RFC 9728 `resource` value is the issuer identity of its references. |
| Authorization server | Issues resolver tokens. |
| Resolver client | A separate OAuth client of the host. It is not the MCP client that holds the agent token. |
| Resolve endpoint | An HTTP endpoint of the protected resource. It returns plaintext values to the resolver client only. |

## 3. Issuer identity and protected-resource metadata

A server MUST publish RFC 9728 protected-resource metadata whose `resource` value is identical to the URL
of the MCP endpoint (RFC 9728 section 3.3). That value is the issuer identity
([HOST-INTEGRATION.md](HOST-INTEGRATION.md#2-issuer-identity)).

A host MUST get the metadata in this order:

1. The host sends a request without a token to the MCP endpoint. If the 401 answer has a
   `WWW-Authenticate` header with a `resource_metadata` parameter, the host MUST use that URL (RFC 9728
   section 5.1) and no other URL.
2. Else the host MUST use the well-known URL that RFC 9728 section 3.1 builds from the MCP URL. The host
   inserts `/.well-known/oauth-protected-resource` between the host component and the path, and keeps the
   path and the query.

A host MUST NOT try another URL. In particular, a host MUST NOT use the well-known URL at the origin root
for an MCP URL with a path or a query.

If the metadata `resource` is not identical to the issuer identity, the host MUST NOT use the metadata,
MUST NOT record an observation with that issuer and MUST NOT resolve. A host MUST NOT change the case of
either string to make them match.

If the host finds no metadata, or the server does not answer, the host MUST NOT resolve. If the challenge
names a `resource_metadata` URL and that URL gives no metadata document, the host MUST NOT resolve.

**Note.** An implementation can offer an operator override for a server that publishes no metadata. A run
with such an override does not conform to this profile. The host should label the run as not conformant
in its report.

**Note.** For the trailing slash in step 2, this profile reads RFC 9728 section 3.1 as follows: the host
removes only a slash that is the whole path. `https://mcp.example.com/mcp/` gives
`https://mcp.example.com/.well-known/oauth-protected-resource/mcp/`. The authors of RFC 9728 did not
confirm this reading (OQ-13).

**Open (OQ-13).** The MCP authorization specification (version 2025-11-25) permits a last fallback to the
well-known URL at the origin root. This profile does not permit it for resolution. A root document must
name the origin as `resource` (RFC 9728 section 3.3), so it cannot name the MCP URL. For the MCP connection
itself, a host can still use the MCP fallback. A SEP must resolve this conflict.

## 4. Discovery object

A server that offers `oauth-resolver-1` MUST publish a `sensitive_references` object in its RFC 9728
protected-resource metadata. A server MUST NOT publish the object while it does not accept resolve
requests.

| Member | Type | Presence |
|---|---|---|
| `resolve_endpoint` | URL string | required |
| `resolve_scope` | non-empty string | required |
| `resolver_profiles` | array of strings | required |
| `sink_profiles` | array of strings | required |
| `max_references` | integer of 100 or more | optional (section 12.3) |
| `status` | string | optional |

```json
{
  "resource": "https://mcp.example.com/mcp",
  "authorization_servers": ["https://mcp.example.com"],
  "scopes_supported": ["mcp"],
  "sensitive_references": {
    "resolve_endpoint": "https://mcp.example.com/sensitive-references/resolve",
    "resolve_scope": "sensitive-references.resolve",
    "resolver_profiles": ["oauth-resolver-1"],
    "sink_profiles": ["local-file-1"],
    "status": "experimental"
  }
}
```

A host MUST refuse the object, and MUST NOT resolve, in each of these cases:

- a required member is absent or has another type;
- the object does not list the resolver profile and the sink profile that the host and the server
  negotiated.

A host MUST NOT put a default value in place of a missing or malformed member. A host MAY use an
operator-configured endpoint or scope in place of a discovered value of a valid object. An
operator-configured value MUST NOT make a refused object acceptable.

If the host and the server negotiated both profiles and the metadata holds no `sensitive_references`
object, the host MUST NOT resolve.

**Provisional (OQ-8).** The discovery object lives in the RFC 9728 metadata. The field name
`sensitive_references` is not registered in the IANA "OAuth Protected Resource Metadata" registry.

## 5. Resolve scope

A server MUST name the resolve scope in `sensitive_references.resolve_scope`. A server SHOULD NOT list the
resolve scope in `scopes_supported` of its RFC 9728 or RFC 8414 metadata.

An authorization server MUST refuse an authorization request that names the resolve scope together with
any scope other than `openid`. It MUST answer with `invalid_scope`.

A host MUST request no scope other than the resolve scope and, optionally, `openid`. If a token response
names a scope set without the resolve scope, the host MUST NOT use the token. If a token response has no
`scope` parameter, the granted scope is the requested scope (RFC 6749 section 5.1), and the host MAY use the
token.

## 6. Resolve endpoint

A host MUST send a resolver token only to a resolve endpoint on the origin of the `resource` value. This
applies to a discovered endpoint and to an operator-configured endpoint. A host MUST refuse an endpoint on
another origin before it starts an authorization.

A host MUST use `https` for the resolve endpoint. A host MAY use `http` only on a loopback address, for
tests.

**Open (OQ-14).** A deployment that needs the resolve endpoint on another origin needs a separately
authenticated binding of the endpoint to the resource, and a token with the endpoint as its audience. This
version does not define it.

## 7. Fetch policy

### 7.1 Non-public address

An address is *non-public* if it is not globally reachable. That is the case if one of these conditions is
true:

- The IANA IPv4 Special-Purpose Address Registry or the IANA IPv6 Special-Purpose Address Registry gives
  the address "Globally Reachable: False", "N/A" or no value.
- The address is a multicast address.
- The address is an IPv6 site-local address (`fec0::/10`, RFC 3879).

If more than one registry entry contains the address, the most specific entry (the longest prefix)
decides. A host uses the current version of the registries. A conformance test names the version that it
uses.

For an IPv4-mapped (`::ffff:0:0/96`), IPv4-compatible (`::/96` without `::` and `::1`), NAT64
(`64:ff9b::/96`) or 6to4 (`2002::/16`) address, the host MUST also judge the embedded IPv4 address. If that
IPv4 address is non-public, the IPv6 address is non-public.

### 7.2 Rule

Before a host sends a request to a URL that a server supplied, the host MUST resolve its host name by DNS.
If one address is non-public, or if the name does not resolve, the host MUST NOT send the request and MUST
NOT resolve.

The rule applies to:

- the `resource_metadata` URL of the challenge;
- the metadata URLs of the authorization server;
- the `authorization_endpoint`, `token_endpoint` and `registration_endpoint` of the authorization server
  metadata;
- every other endpoint of the metadata that the host uses, for example `jwks_uri`;
- the resolve endpoint.

The host MUST also refuse an authorization endpoint on a non-public address, although only the browser
opens it. The fetch policy does not cover the MCP URL, which the operator gives.

### 7.3 Checked address

For each request of this policy that the host sends with its own HTTP client, the host MUST connect to an
address that it checked. It MUST NOT resolve the host name again for the connection. If the check gave
more than one address, the host MAY try them in turn. If the HTTP client cannot connect to a given
address, the host MUST NOT send the request.

For TLS, the host MUST verify the certificate for the host of the URL (RFC 9110 section 4.3.4, RFC 9525),
not for the checked address.

**Note.** The browser resolves the name of the authorization endpoint again. Section 7.3 cannot apply to
that connection (SECURITY-MODEL.md, TM-11).

### 7.4 Redirects and proxies

The HTTP clients of a host for protected-resource metadata, authorization server metadata, client
registration, the token endpoint and the resolve endpoint MUST NOT follow an HTTP redirect. The host
treats a 3xx answer as a failed request. A host MUST NOT send these requests through a proxy that does not
apply this fetch policy, for example a proxy that an environment variable selects.

### 7.5 Local mode

A host MUST NOT make an exception to the fetch policy by itself. A host MAY allow a non-public target only
if all these conditions are true:

1. An operator enables local mode explicitly, with a host option for this MCP server.
2. All DNS addresses of the host of the MCP URL are non-public. The host resolves the MCP host once, when it
   connects to the MCP server, and keeps that result for the session. The host uses that result only to
   decide if local mode applies. It still checks each request by sections 7.2 and 7.3.
3. The target is on the origin of the MCP URL, or on an origin that the operator configures. The host
   compares the scheme, the host and the port exactly.

Also in local mode, a host MUST NOT send a request to a link-local address (`169.254.0.0/16`, `fe80::/10`),
an unspecified address (`0.0.0.0/8`, `::`), the limited broadcast address or a multicast address. This
applies also to such an address embedded in an IPv6 address.

**Note.** RFC 9728 section 7.7 says that clients SHOULD take precautions against SSRF. The MUST of this
section is a decision of this profile.

## 8. Token classes

A resolver token MUST NOT authorize an MCP request. An agent token MUST NOT authorize a resolve request. A
server SHOULD make the two classes distinct by more than the scope, for example by a separate token record
or a separate audience.

A host MUST NOT send the agent token to the resolve endpoint. A host MUST refuse to send a resolver token
that is equal to the agent token.

## 9. Client registration and authorization

### 9.1 Authorization request and response

The resolver client is a separate OAuth client. The host registers it by dynamic client registration
(RFC 7591) or uses a configured `client_id`.

A host MUST use Authorization Code with PKCE S256 and the `resource` parameter (RFC 8707), with the issuer
identity as its value. A host MUST check `state`.

If the authorization response has an `iss` parameter, the host MUST compare it with the `issuer` of the
validated authorization server metadata. The host MUST refuse the response if they differ (RFC 9207). If
the authorization server metadata has `authorization_response_iss_parameter_supported: true` and the
response has no `iss` parameter, the host MUST refuse the response (RFC 9207 section 2.4).

A host MUST refuse authorization server metadata whose `issuer` is not the requested issuer (RFC 8414
section 3.3). A host MUST refuse authorization server metadata in which `code_challenge_methods_supported`
is absent, is not an array or does not list `S256`. A host MUST build the RFC 8414 well-known URL without a
terminating slash of the issuer path (RFC 8414 section 3.1).

If the RFC 9728 metadata lists more than one authorization server, the host MUST NOT select one
automatically.

### 9.2 Loopback redirect URIs

If `local-file-1` is the only sink profile that a server offers, the authorization server MUST issue a
resolver authorization code only to a loopback IP redirect URI (RFC 8252 section 7.3).

An authorization server MUST compare a redirect URI of a resolver client with the registered redirect
URIs of that client by exact simple string comparison (RFC 3986 section 6.2.1). There is one exception. If
the registered URI is a loopback IP redirect URI, the authorization server MUST accept any port in the
requested URI (RFC 8252 section 7.3, RFC 9700 section 2.1). Every other part of the URI, including the
scheme, the host, the path and the query, MUST match exactly.

An authorization server MUST accept the IPv4 loopback literal `127.0.0.1` as the host of a loopback
redirect URI. A host SHOULD use `127.0.0.1`.

**Provisional (OQ-15).** An authorization server MAY refuse the IPv6 literal `[::1]`. If it refuses it, it
MUST refuse it at client registration or at the authorization request, before the consent page. This
permission restricts RFC 8252 section 7.3. A device with only an IPv6 loopback interface cannot complete
the flow at such a server.

If the consent page carries a Content Security Policy with a `form-action` directive, that directive MUST
permit the exact origin (scheme, host and port) of the validated loopback redirect URI of this request, for
example `form-action 'self' http://127.0.0.1:53124`. The same rule applies to every other response of the
authorization server in the redirect chain after the consent post.

**Provisional (OQ-4).** A host keeps one resolver client and uses a new loopback port for each
authorization. The port rule above makes this possible.

## 10. Consent

An authorization server MUST get an explicit approval from the user before it issues the first
authorization code with the resolve scope for a tuple of subject, client, resource, resolve scope and
sink-profile set. The consent page MUST name the client, the protected resource (its `resource` value) and
the sink profiles that the approval covers.

The authorization server MUST store the approval bound to the tuple of subject, client, resource, resolve
scope and the set of sink profiles that the consent page showed. The approval covers resolution of every
reference of that subject at that resource into those sink profiles only. For a sink profile that the
server offers later, another resource or a broader scope, the authorization server MUST get a new decision
from the user.

An authorization server MUST NOT issue a resolver code on the basis of a browser session alone. It MUST send
the consent page with a policy that forbids every framing origin, for example
`Content-Security-Policy: frame-ancestors 'none'`. The consent post MUST carry a single-use nonce that the
server bound to the browser session and to the authorization request. The consent post MUST carry an
`Origin` header equal to the origin of the authorization server. If the nonce is absent, unknown, already
used, or bound to another session or request, or if the `Origin` header is absent or different, the
authorization server MUST NOT record an approval and MUST NOT issue a code.

A withdrawn or expired approval MUST stop the refresh of resolver tokens. It MUST also stop every live
resolver access token that the approval covered. An authorization server SHOULD NOT ask for consent per
reference or per tool call.

## 11. Token lifetime, cache and renewal

A server MUST enforce the expiry of a resolver access token. A server SHOULD issue resolver access tokens
with a lifetime of one hour or less. A server MUST rotate a resolver refresh token on each use. A server
MUST bind a refresh token to the client that received it.

A host that keeps a resolver token MUST store it so that no other operating-system user can read it. On a
POSIX system, the file MUST have owner-only permissions (mode 0600 or stricter). The file MUST NOT have an
access control list entry that grants access to another user. On another system, the host MUST use an
equivalent store that is bound to the user, for example the credential store of the operating system.

A host MUST key a cached token by the triple of resource, authorization server and scope.

After a 401 answer from the resolve endpoint, a host MAY get one new token and try once again. After a
second 401 answer, the host MUST stop and MUST NOT write the sink.

**Provisional (OQ-5).** This profile version does not require sender-constrained tokens. A server and a
host MAY use DPoP (RFC 9449). Short access-token lifetimes and refresh rotation bound to the client limit
the risk of a stolen token.

## 12. Resolve request and response

### 12.1 Request

```http
POST /sensitive-references/resolve HTTP/1.1
Host: mcp.example.com
Authorization: Bearer <resolver access token>
Content-Type: application/json

{"references": ["⟦sref:email:AbCdEfGhIjKlMnOpQrStUvWx1234⟧"],
 "sink_type": "local_file",
 "destination": "customers.csv"}
```

- `references` MUST be an array of references in canonical form.
- A resolve request MUST NOT carry a principal. The server MUST take the principal from the resolver token.
- A resolve request MUST carry `sink_type`. The value for `local-file-1` is `local_file`. A server MUST
  refuse a `sink_type` that it does not offer.
- A resolve request MUST carry `destination`: a JSON string of 1 to 4096 characters without control
  characters (U+0000 to U+001F and U+007F). A server MUST answer a request without a valid `destination`
  with `400 invalid_request`.
- A server MUST use `destination` for audit only. A server MUST NOT return `destination` in an answer.

**Provisional (OQ-6).** A host SHOULD send a destination label, not an absolute path. A host MAY send a
keyed one-way hash of the path, as lower-case hexadecimal.

### 12.2 Authorization of each request

For each request, the server MUST check all of these conditions:

1. The audience or resource of the resolver token is the protected resource.
2. The resolver token has the resolve scope and an active approval (section 10).
3. The subject of the resolver token is the owner of every reference in the request.
4. Every reference was issued by this server, did not expire, and was not revoked.
5. The request is within the limits of the server.

If one condition fails for one reference, the server MUST return no value for the whole request.

### 12.3 Batch limits and duplicates

A server MUST accept at least 100 references in one resolve request. A server MAY publish a larger limit as
`sensitive_references.max_references`. The effective limit of a server is its published `max_references`,
or 100 if it publishes none. A server MUST answer a request with more references than its effective limit
with `413 too_many_references`. A request with no reference gets `400 invalid_request`.

A host MUST NOT send more references than the effective limit in one request. A host SHOULD send all
references of one sink write in one request if the effective limit permits it. If the host must split the
references, the host MUST NOT write the sink until every request succeeded. The host MUST discard all
values if one request fails.

A host SHOULD remove duplicate references before it sends a request. A server MUST treat a duplicate
reference as one reference.

### 12.4 Success

A server MUST answer a successful request with `200` and a JSON object `{"values": {"<reference>":
"<value>"}}`. The answer MUST carry `Cache-Control: no-store`.

A host MUST accept a `200` answer only if the key set of `values` is exactly the set of references of the
request, and each value is a string. Else the host MUST discard the answer and MUST NOT write the sink.

## 13. Error format

A resolve endpoint MUST answer a failure with one JSON object `{"error": "<code>"}` and an optional
`reasons` object that maps a reason to a count. The answer MUST NOT contain protected data (SPEC-DRAFT.md,
section 8). The endpoint MUST use these codes:

| Status | `error` | Meaning |
|---|---|---|
| 400 | `invalid_request` | The body is malformed or empty, or has no valid destination. |
| 401 | `invalid_token` | The token is absent, unknown or expired, is for another resource, or its approval ended. |
| 403 | `insufficient_scope` | The token has no resolve scope. |
| 403 | `ineligible_sink` | The server does not offer the `sink_type`. |
| 403 | `not_enabled` | The server does not allow resolution for this principal. |
| 409 | `unresolvable` | At least one reference does not resolve. `reasons` counts `malformed`, `unknown`, `revoked` and `expired`. |
| 413 | `too_many_references` | The request exceeds the effective limit. |
| 429 | `quota_exceeded` | The principal exceeded a rate or a quota. |

**Note.** The reference server reports a reference of another principal as `unknown`. Then the answer does
not show that the reference exists.

A 401 answer MUST carry a `WWW-Authenticate` header with the `Bearer` scheme (RFC 6750 section 3). A 403
`insufficient_scope` answer SHOULD carry it with `error="insufficient_scope"`.

A host MUST treat only 401 as a reason to get a new token. A host MUST fail closed for every non-200
answer, also for a code that it does not know. A host MUST NOT show a server message to the model.

| Answer | Result |
|---|---|
| `{"error": "unresolvable", "reasons": {"unknown": 1}}` | allowed |
| `{"error": "invalid_token"}` | allowed |
| `{"error": "unresolvable", "reference": "⟦sref:email:AbCdEfGhIjKlMnOpQrStUvWx1234⟧"}` | refused: protected data, item 3 |
| `{"error": "unresolvable", "id": "AbCdEfGh"}` | refused: item 4, a part of 8 characters |
| `{"error": "unresolvable", "id": "AbCdEfG"}` | allowed: a part of 7 characters |
| `{"error": "unresolvable", "detail": "alice@ex"}` | refused: item 2, where the value is `alice@example.com` |
| `{"error": "unresolvable", "v": "YWxpY2VAZXhhbXBsZS5jb20"}` | refused: item 1, base64url without padding |
| `{"error": "unresolvable", "alice%40example.com": 1}` | refused: item 1, percent-encoded, in a member name |
| `{"error": "invalid_request", "destination": "report.txt"}` | refused: item 5 |
| `{"error": "invalid_token", "client_id": "c-123"}` | allowed: public client |

## 14. Subject binding

The resource server MUST bind each resolver token to a stable subject. It MUST NOT infer the subject from a
display name, from reference text or from model input.

**Provisional (OQ-10).** The profile does not require JWT access tokens. The resource server can bind the
subject by any means, for example by a server-side token record. If a deployment uses JWT access tokens,
it SHOULD use the `sub` claim or declare an equivalent stable claim.

## 15. Audit and limits

A server SHOULD record one audit event for each resolve request. The event MUST NOT contain a value, a
reference in canonical form or a credential. A server MAY limit the number of values per principal and
period. It answers with `429 quota_exceeded` after the limit.

**Open (OQ-18).** The minimum content of the audit event, the rate limits and the recovery rules are not
decided.

## 16. Not in this profile

- Sender-constrained tokens as a requirement (section 11).
- Token introspection.
- Server-to-server redemption and cross-server delegation.
- A resolve endpoint on another origin (section 6).
- An issuer-side sink (SPEC-DRAFT.md, section 6.3).

## 17. Evidence

**Note.** Two implementations follow most of this profile: the reference server MCPGate and the reference
host in `prototype/`. Neither implements the whole profile. The reference server does not conform to
section 3: its challenge names the metadata of its base URL. No conformant end-to-end run succeeded. See
[IMPLEMENTATION-EVIDENCE.md](IMPLEMENTATION-EVIDENCE.md).
