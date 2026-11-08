# Resolver profile `oauth-resolver-1`

**Status: Concept 0.7 draft, normative profile.** The conventions and terms of
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

The profile assumes that the authorization server and the protected resource share state. The resource
must see the approval of section 10 (to stop live tokens when it ends, and to check an active approval on
each request), and the consent page must name the sink scopes of the request. The authorization server
can be the same service as the resource, or share a store with it. A deployment with an independent
authorization server needs a mechanism for this shared state, for example token introspection. This
profile does not define one (section 16).

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
| `sinks` | object | required |
| `process_scope` | non-empty string | required if `sink_profiles` lists `process-1` |
| `display_scope` | non-empty string | required if `sink_profiles` lists `display-1` |
| `max_references` | integer of 100 or more | optional (section 12.3) |
| `status` | string | optional |

`sinks` has one member for each entry of `sink_profiles`, with the profile identifier as its name. Each
member is an object with two members:

| Member | Type | Content |
|---|---|---|
| `sink_type` | non-empty string | The wire value of `sink_type` for this profile (section 12.1). |
| `scopes` | array of non-empty strings | The whole scope set that a resolver token needs for this profile. It holds the resolve scope, and the sink scope of the profile if the profile has one (section 5). |

```json
{
  "resource": "https://mcp.example.com/mcp",
  "authorization_servers": ["https://mcp.example.com"],
  "scopes_supported": ["mcp"],
  "sensitive_references": {
    "resolve_endpoint": "https://mcp.example.com/sensitive-references/resolve",
    "resolve_scope": "sensitive-references.resolve",
    "process_scope": "sensitive-references.resolve.process",
    "display_scope": "sensitive-references.resolve.display",
    "resolver_profiles": ["oauth-resolver-1"],
    "sink_profiles": ["display-1", "local-file-1", "process-1"],
    "sinks": {
      "display-1": {"sink_type": "display",
                    "scopes": ["sensitive-references.resolve", "sensitive-references.resolve.display"]},
      "local-file-1": {"sink_type": "local_file", "scopes": ["sensitive-references.resolve"]},
      "process-1": {"sink_type": "process",
                    "scopes": ["sensitive-references.resolve", "sensitive-references.resolve.process"]}
    },
    "status": "experimental"
  }
}
```

A host MUST refuse the object, and MUST NOT resolve, in each of these cases:

- a required member is absent or has another type;
- the object does not list the resolver profile and the sink profile that the host and the server
  negotiated;
- `sinks` has no member for a negotiated sink profile, or that member has no valid `sink_type` or
  `scopes`, or its `scopes` does not hold the resolve scope;
- `process_scope` or `display_scope` is present and is not the sink scope that `sinks` names for
  `process-1` or `display-1`;
- `max_references` is present and is not an integer of 100 or more.

A host MUST take the scope set of a sink profile from `sinks`. The members `process_scope` and
`display_scope` repeat the sink scopes of the two profiles for hosts that show them to a person.

The field name of the discovery object is `sensitive_references`. This version fixes the name.

A host MUST NOT put a default value in place of a missing or malformed member. A host MAY use an
operator-configured endpoint or scope in place of a discovered value of a valid object. An
operator-configured value MUST NOT make a refused object acceptable.

If the host and the server negotiated both profiles and the metadata holds no `sensitive_references`
object, the host MUST NOT resolve.

**Note.** The discovery object lives in the RFC 9728 metadata (OQ-8, decided in Concept 0.7). The field
name `sensitive_references` is not registered in the IANA "OAuth Protected Resource Metadata" registry. A
SEP must register it.

## 5. Resolve scope and sink scopes

### 5.1 The scopes

The *resolve scope* authorizes resolution. A *sink scope* is a second scope that a sink profile can
require in addition to the resolve scope. A sink profile states whether it requires a sink scope. In this
version, `local-file-1` requires none, and `process-1` and `display-1` each require their own sink scope
([PROCESS-PROFILE.md](PROCESS-PROFILE.md), [DISPLAY-PROFILE.md](DISPLAY-PROFILE.md)).

A server MUST name the resolve scope in `sensitive_references.resolve_scope` and the scope set of each
sink profile in `sensitive_references.sinks` (section 4). Two sink profiles MUST NOT share a sink scope. A
sink scope MUST NOT be the resolve scope. A server SHOULD NOT list the resolve scope or a sink scope in
`scopes_supported` of its RFC 9728 or RFC 8414 metadata.

**Note.** Each sink scope is separate so that a person can leave out a sink that gives the value to a
process or a screen (section 10). The sink is a label that the client sends. The server cannot check it.

### 5.2 Authorization request

A host MUST ask for the resolve scope and the sink scopes of the sink profiles that it can honour, in one
authorization request. A host MUST NOT ask for a sink scope of a profile whose rules it does not meet. A
host MAY add `openid`.

An authorization server MUST accept only a request whose scope set is the resolve scope, plus zero or more
sink scopes that its discovery object names, plus optionally `openid`. It MUST answer every other request
that names the resolve scope or a sink scope with `invalid_scope`. In particular, these requests get
`invalid_scope`:

- the resolve scope together with any scope that is not a sink scope and not `openid`, for example an
  agent scope;
- a sink scope without the resolve scope.

The authorization server MUST issue no token for such a request.

### 5.3 Token response

If a token response names a scope set without the resolve scope, the host MUST NOT use the token. If a
token response has no `scope` parameter, the granted scope is the requested scope (RFC 6749 section 5.1),
and the host MAY use the token. A host MUST use a token for a sink profile only if the granted scope set
holds every scope of that profile in `sinks`.

A refresh MUST keep the granted scope set. An authorization server MUST NOT add a scope at a refresh. A
host that needs a sink scope that its token does not hold MUST start a new authorization (section 10).

### 5.4 Missing sink scope

If a resolver token holds the resolve scope but not the sink scope that the requested `sink_type` needs,
the resolve endpoint MUST answer `403 insufficient_scope`. It MUST answer before it looks up any
reference. It MUST return no value, and it MUST NOT write a resolve audit event (section 15). The
answer MUST carry:

- a `WWW-Authenticate` header with the `Bearer` scheme, `error="insufficient_scope"`, a `scope`
  attribute with the whole scope set that the sink profile needs, and an `error_description` attribute
  (RFC 6750 section 3);
- a JSON body with `error`, `scope` (the same scope set) and `error_description` (the same text);
- `Cache-Control: no-store`.

The `error_description` MUST be a fixed text of the server that tells the person to sign in again and
allow the sink on the consent page. It MUST NOT contain protected data (SPEC-DRAFT.md, section 8).

```http
HTTP/1.1 403 Forbidden
WWW-Authenticate: Bearer error="insufficient_scope",
  scope="sensitive-references.resolve sensitive-references.resolve.display",
  error_description="This sign-in does not allow real values on your screen. Sign in again and allow the screen on the consent page."
Cache-Control: no-store
Content-Type: application/json

{"error": "insufficient_scope",
 "error_description": "This sign-in does not allow real values on your screen. Sign in again and allow the screen on the consent page.",
 "scope": "sensitive-references.resolve sensitive-references.resolve.display"}
```

(The header is folded here for the page width. It is one line on the wire.)

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

A host MUST judge an IPv4-mapped address (`::ffff:0:0/96`) by its embedded IPv4 address only, because a
connection to it goes to that IPv4 address. For an IPv4-compatible (`::/96` without `::` and `::1`), NAT64
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
opens it. The fetch policy need not cover the MCP URL, which the operator gives. A host MAY apply it to
the MCP URL as well.

### 7.3 Checked address

For each request of this policy that the host sends with its own HTTP client, the host MUST connect to an
address that it checked. It MUST NOT resolve the host name again for the connection. If the check gave
more than one address, the host MAY try them in turn. If the HTTP client of the host cannot be told which
address to connect to, the host MUST NOT send the request.

For TLS, the host MUST verify the certificate for the host of the URL (RFC 9110 section 4.3.4, RFC 9525),
also when the connection goes to a checked address.

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

If the RFC 9728 metadata lists exactly one authorization server, the host uses it. If the metadata lists
no authorization server, or more than one, the host MUST NOT select one automatically. The host MAY use an
authorization server that an operator configures explicitly. If the metadata lists authorization servers,
a configured authorization server MUST be one of them. Without such a configuration, the host MUST NOT
resolve.

### 9.2 Loopback redirect URIs

If every sink profile that a server offers puts the value on the computer of the host (`local-file-1`,
`process-1` and `display-1` do), the authorization server MUST issue a resolver authorization code only to a
loopback IP redirect URI (RFC 8252 section 7.3).

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

### 10.1 A decision at every authorization request

An authorization server MUST get an explicit decision of the user on a consent page for every
authorization request with the resolve scope. A stored approval MUST NOT replace this decision. A second
authorization request of the same client, with a live approval, also gets the consent page and no code
until the user decides.

**Note.** A refresh (RFC 6749 section 6) is not an authorization request. It needs no consent page
(section 11).

### 10.2 What the consent page names

The consent page MUST name:

1. the account of the user that the code will be issued for, with an action to use another account;
2. the client, by the name from its registration;
3. the host and the port of the loopback redirect URI of this request;
4. the time of the request;
5. the protected resource (its `resource` value);
6. one line for each sink scope that the request asks for. Each line says in plain words what the sink
   does with a value. A request without a sink scope shows no such line.

The action to use another account MUST end the browser session of the current account and return to the
same authorization request, with the same scope set. The other account MUST then get its own consent page.
The action MUST carry the same single-use nonce and `Origin` check as the consent post.

The client name comes from the client. The page SHOULD say that the user approves only a sign-in that the
user started in this program.

### 10.3 The stored approval

The authorization server MUST store the approval bound to the tuple of subject, client, resource and
granted scope set. A token carries only the scopes of the approval of its authorization. For a sink scope
that the token does not hold, another resource or a broader scope, the host MUST start a new authorization
and the user MUST decide again (section 5.3).

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

### 10.4 Revocation per device

A *device* is the pair of a principal and a resolver client. An authorization server MUST let the user
list the devices of the user and revoke one of them. It MUST let an administrator of the deployment do the
same for the devices of another user. It MUST NOT let a user who is not an administrator list or revoke a
device of another user.

A revocation of a device MUST stop every access token, every refresh token and every unused authorization
code that the device holds, and MUST withdraw the approval of the device. A revocation MUST NOT stop a
token of another principal, also when that principal uses the same client.

A credential that the authorization server issued before the revocation MUST NOT work after it, also
after a new approval of the same device. An authorization server can meet this rule with a counter per
device (an *epoch*): every code, token and device record carries the epoch of its issue and works only
while that epoch is current. The revocation raises the epoch before it stops the tokens. The write of a
new credential checks the epoch in the same atomic step. If the authorization server cannot read the epoch,
it MUST refuse the credential.

After a revocation, the device can authorize again. The new authorization needs a new decision of the user
(section 10.1).

## 11. Token lifetime, cache and renewal

A server MUST enforce the expiry of a resolver access token. A server SHOULD issue resolver access tokens
with a lifetime of one hour or less. A server MUST rotate a resolver refresh token on each use. A server
MUST bind a refresh token to the client that received it.

A host that keeps a resolver token MUST store it so that no other operating-system user can read it. On a
POSIX system, the file MUST have owner-only permissions (mode 0600 or stricter). The file MUST NOT have an
access control list entry that grants access to another user. On another system, the host MUST use an
equivalent store that is bound to the user, for example the credential store of the operating system.

A host MUST key a cached token by the triple of resource, authorization server and scope.

A refresh MUST keep the scope set of the refreshed token (section 5.3). A refresh needs no consent page.

After a 401 answer from the resolve endpoint, a host MAY get one new token and try once again. After a
second 401 answer, the host MUST stop and MUST NOT write the sink.

### 11.1 Recovery

1. **Refused refresh.** If the authorization server refuses a refresh token, the host MUST delete that
   refresh token from its cache and MUST NOT send it again. The host MAY then start a new interactive
   authorization. If interaction is off, the host MUST stop and MUST NOT write the sink.
2. **Lost token cache.** If the cache is absent, the host has no resolver token. It MAY start a new
   interactive authorization. If interaction is off, the host MUST stop and MUST NOT write the sink.
3. **Cache that others can read.** The host MUST NOT use a token from a cache that breaks section 11. The
   host MUST NOT change the permissions of such a cache by itself, and MUST stop.
4. **Cache that the host cannot parse.** The host MUST NOT use any entry of it. It continues as for a lost
   cache.
5. **Ended approval.** After an approval is withdrawn or expires, the authorization server refuses the
   refresh and the resolve endpoint answers 401 (section 10). The host recovers as in item 1. A new
   authorization needs a new approval of the user.
6. **Lost rotated refresh token.** If the host stops after the server rotated a refresh token and before
   the host stored the new one, the host continues as for a refused refresh. The user authorizes again.

In every case of this section, a host MUST NOT write the sink with values from an earlier, failed attempt.

**Provisional (OQ-5).** This profile version does not require sender-constrained tokens. A server and a
host MAY use DPoP (RFC 9449). Short access-token lifetimes and refresh rotation bound to the client limit
the risk of a stolen token.

### 11.2 Account hint

A token response and a refresh response MAY carry `account_hint`: a string that lets a host show the person
which account its token belongs to. The hint MUST NOT contain the whole account name. If the account is an
email address with a local part of n characters, the hint MUST hold at most the first min(3, floor(n/2))
characters of the local part, then an ellipsis (U+2026), then the whole domain. For `alice@example.com`
(n=5) the hint is `al…@example.com` or shorter. A server that sends the hint in the token response MUST also
send it in the refresh response.

A host MUST NOT use the hint for a decision of this profile. A host MUST NOT give it to the model.

**Note.** References are per principal, that is per account (section 12.2). If a person signs in to the
resolver with one account and to the MCP server with another, every reference is `unknown`. The hint lets
the host tell the person which account the resolver token belongs to.

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
- A resolve request MUST carry `sink_type`: the value that `sinks` names for the sink profile. The values
  of this version are `local_file` (`local-file-1`), `process` (`process-1`) and `display` (`display-1`).
  A server MUST refuse a `sink_type` that is not exactly one that it offers, with `403 ineligible_sink`.
- A sink profile can restrict `destination` and the number of references further (for example
  DISPLAY-PROFILE.md, section 3). A server MUST answer a request that breaks such a restriction with
  `400 invalid_request`.
- A resolve request MUST carry `destination`: a JSON string of 1 to 4096 characters without control
  characters (U+0000 to U+001F and U+007F). A server MUST answer a request without a valid `destination`
  with `400 invalid_request`.
- A server MUST use `destination` for audit only. A server MUST NOT return `destination` in an answer.

**Provisional (OQ-6).** A host SHOULD send a destination label, not an absolute path. A host MAY send a
keyed one-way hash of the path, as lower-case hexadecimal.

### 12.2 Authorization of each request

For each request, the server MUST check all of these conditions:

1. The audience or resource of the resolver token is the protected resource.
2. The resolver token has the resolve scope, every sink scope that the `sink_type` needs (section 5.4),
   and an active approval (section 10). The server checks the scopes before it looks up a reference.
3. The subject of the resolver token is the owner of every reference in the request (SPEC-DRAFT.md,
   section 2).
4. Every reference was issued by this server, did not expire, and was not revoked.
5. The request is within the limits of the server.

If one condition fails for one reference, the server MUST return no value for the whole request. If
condition 3 fails, the reason for that reference is `unknown` (SPEC-DRAFT.md, section 5.5), also when the
reference is revoked or expired.

References are per principal (account). A reference that the issuer issued to principal A MUST NOT resolve
for principal B, also when A and B are two accounts of one person, and also when B holds a valid resolver
token and the reference is current. A server SHOULD look up a reference only in the records of the subject
of the resolver token, so that a record of another principal is never read.

**Note.** A record that several people may see needs a reference for each principal.

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
`reasons` object that maps a reason to a count. A `403 insufficient_scope` answer also carries `scope` and
`error_description` (section 5.4). The answer MUST NOT contain protected data (SPEC-DRAFT.md, section 8).
The endpoint MUST use these codes:

| Status | `error` | Meaning |
|---|---|---|
| 400 | `invalid_request` | The body is malformed or empty, has no valid destination, or breaks a restriction of the sink profile. |
| 401 | `invalid_token` | The token is absent, unknown or expired, is for another resource, or its approval ended or was revoked. |
| 403 | `insufficient_scope` | The token lacks the resolve scope or the sink scope of the `sink_type`. The answer names the whole scope set that the request needs. |
| 403 | `ineligible_sink` | The server does not offer the `sink_type`. |
| 403 | `not_enabled` | The server does not allow resolution for this principal. |
| 409 | `unresolvable` | At least one reference does not resolve. `reasons` counts `malformed`, `unknown`, `revoked` and `expired`. |
| 413 | `too_many_references` | The request exceeds the effective limit. |
| 429 | `quota_exceeded` | The principal exceeded a rate or a quota. |
| 503 | `audit_unavailable` | The server could not write the audit event of the release (section 15). No value left the server. |

A 401 answer MUST carry a `WWW-Authenticate` header with the `Bearer` scheme (RFC 6750 section 3). A 403
`insufficient_scope` answer MUST carry it as section 5.4 says. Every other failure answer SHOULD carry
`Cache-Control: no-store`.

After a `503 audit_unavailable` answer, the host MUST NOT write the sink. It MAY send the request again
later.

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

A server MUST record one audit event for each resolve request that releases values. No value leaves the
server without its audit event: the server MUST write the event before it sends the values. If the server
cannot write the event, it MUST answer `503 audit_unavailable` and MUST NOT send a value.

The event MUST NOT contain a value, a reference in canonical form, a destination in another form than the
sink profile permits, or a credential. The event SHOULD name the subject, the client, the sink profile and
the number of values. A sink profile can say what the event keeps of `destination` (for example
PROCESS-PROFILE.md, section 6).

A server MAY limit the number of values per principal and period. It answers with `429 quota_exceeded`
after the limit. Every released value counts toward the limit, in every sink profile.

**Open (OQ-18).** The minimum content of the audit event beyond this section and the rate limits are not
decided. Recovery beyond section 11.1 is not decided.

## 16. Not in this profile

- Sender-constrained tokens as a requirement (section 11).
- Token introspection.
- Server-to-server redemption and cross-server delegation.
- A resolve endpoint on another origin (section 6).
- An issuer-side sink (SPEC-DRAFT.md, section 6.4).

## 17. Evidence

**Note.** Three implementations implement parts of this profile: the reference server, the reference host
in `prototype/` and a second host, a coding-agent plugin ([IMPLEMENTATION-EVIDENCE.md](IMPLEMENTATION-EVIDENCE.md)
names them). None implements the whole profile.
[protocol-package/PROFILE-oauth-resolver-1.md](protocol-package/PROFILE-oauth-resolver-1.md) maps each rule
to its evidence. See [IMPLEMENTATION-EVIDENCE.md](IMPLEMENTATION-EVIDENCE.md).
