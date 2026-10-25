# M4 findings: a host that resolves through `oauth-resolver-1` and `local-file-1`

This file records protocol gaps that the test host hit when it implemented materialization (milestone M4b).
It does not change the concept or the profile draft. Each finding names what the host does now. The host
behaviour is a prototype choice, not a proposal for normative text.

Evidence: `demo/mcp_host.py` (`--resolve-into`), `src/sensitive_references/resolver_client.py`, and
`tests/test_mcp_host_resolve.py`.

## F1. Concept 0.5 does not define how a host finds the resolve endpoint

The profile says that the resolver is "a separate OAuth client for the same protected resource". It does
not say where the resolve endpoint is.

The host accepts two sources. An explicit `--resolve-endpoint` comes first. Otherwise the host reads a
provisional `sensitive_references` object in the RFC 9728 protected-resource metadata of the MCP endpoint:

```json
{
  "resource": "https://server.example/mcp",
  "authorization_servers": ["https://as.example"],
  "sensitive_references": {
    "resolve_endpoint": "https://server.example/sensitive-references/resolve",
    "resolve_scope": "sensitive-references.resolve",
    "resolver_profiles": ["oauth-resolver-1"],
    "sink_profiles": ["local-file-1"]
  }
}
```

The field name is not registered and is not in the concept. The extension settings object is not a
possible location today: `schema/sensitive-references-settings.schema.json` sets
`additionalProperties: false`. Also, the agent token authenticates the settings, not the resource metadata.
A standard needs one location and one field name.

## F2. The host cannot learn which scope is the resolve scope

The profile calls the scope "deployment-defined". RFC 9728 `scopes_supported` lists scopes but does not
say which scope gives resolve rights. The host uses `--resolve-scope`, then the provisional
`resolve_scope` field, then the prototype default `sensitive-references.resolve`. A host that guesses the
wrong scope gets a token that the resolve endpoint refuses. The host asks for the resolve scope only. If the
token response names other scopes and not the resolve scope, the host refuses the token
(`scope_not_granted`).

## F3. The issuer identity and the resource identifier must be the same string

The host records the issuer as the MCP URL without credentials, query and fragment. RFC 9728 section 3.3
requires that the `resource` value in the metadata is identical to the URL that the client used. The host
applies this exact comparison. Thus `https://server.example/mcp/` and `https://server.example/mcp` are two
issuers, and the host refuses the metadata (`wrong_issuer`). The profile says "authenticated
issuer/protected-resource identity" but does not define the comparison or the normalization.

## F4. The profile does not bind the resolve endpoint to an origin

The resolver token has the protected resource as its audience. A resolve endpoint on another origin thus
receives a token for the resource. The host accepts a discovered endpoint only on the origin of the
resource (`cross_origin_endpoint`). An explicit `--resolve-endpoint` is operator configuration, and the host
accepts it on any `https` origin. The host also accepts loopback `http` for tests. The host never follows a
redirect from the resolve endpoint or the token endpoint, because a redirect can carry the `Authorization`
header to another origin. The profile does not state these rules.

## F5. Consent semantics are not defined

The reference server shows a one-time consent page for a resolver client. The profile does not say what the
user agrees to: all references of the subject, one destination, one sink type, or a time period. The
profile also does not say whether a new client needs new consent.

This matters for the host. The loopback redirect URI holds a port that the host selects for each
authorization. Thus the host registers a new client (RFC 7591) for each interactive authorization. RFC 8252
section 7.3 asks the authorization server to accept any loopback port, but dynamic registration stores a
redirect URI with a port. If consent is per client, the user sees the consent page each time that the host
authorizes again. A standard should say whether consent attaches to the client, the subject, or the pair.

## F6. Token cache lifetime and storage are host choices

The profile does not say how long a host keeps a resolver token. The host does this:

- It keeps the token only with `--resolver-token-cache PATH`. The file has mode 0600. If other users can
  read the file, the host refuses it and does not repair it.
- The cache key is the triple (resource, authorization server, scope).
- An access token counts as expired 30 seconds before `expires_in` ends. A token without `expires_in` stays
  in use until the resolve endpoint answers 401.
- Refresh tokens rotate. The host replaces the old refresh token with the new one. If the host stops after
  the server rotated the token and before the host wrote the cache, the refresh token is lost, and the user
  must authorize again.
- After a 401, the host gets one new token (refresh, else interactive authorization) and tries once again.
  After a second 401, the run fails and the host removes the access token from the cache.

The profile does not define this retry rule. It also does not ask for sender-constrained tokens (DPoP or
mTLS). The host does not use them.

## F7. All-or-nothing applies to one request, not to one materialization

The server contract accepts 1 to 100 references in one request. The profile does not state a limit. The
host splits a larger set into batches of 100. The host writes nothing until every batch succeeds. But if
batch 2 fails, the server already released the values of batch 1 to the host. The file stays unchanged, and
the host discards the values, but the server audit shows a release. A standard should say if a sink may
split a batch, or give a limit in the settings.

The host also removes duplicate references before it sends a batch. The profile does not say if a
duplicate is valid.

## F8. The destination goes to the server

The profile says that the resolver receives "the sink type, destination, and authenticated principal".
The host sends the absolute local path. This tells the server the layout of the local file system, for
example a user name in a home directory. The profile does not say if the destination is a path, a label,
or a hash. A standard should define this and say what the server may do with it (audit only, or policy).

## F9. Error answers have no defined format

The server contract gives one JSON error `{"error": "<code>", "reasons": {...}}` with status
401, 403, 409, 413 or 429. The profile only says that a failure returns no plaintext values. The host
reports only the code. It accepts a code of at most 64 characters from `[A-Za-z0-9_.-]`, and it reports
`error` for any other code. The host never reports a server message. The host treats only 401 as a reason
to get a new token. A standard should list the codes and say which status means "authorize again".

## F10. The authorization response needs an issuer check

RFC 9207 adds an `iss` parameter to the authorization response, which prevents an authorization server
mix-up. The profile does not mention it. The host compares `iss` with the authorization server issuer when
the parameter is present or when the server advertises
`authorization_response_iss_parameter_supported`. The host also checks `state`, requires PKCE S256 when the
server lists `code_challenge_methods_supported`, and requires that the authorization server metadata names
its own issuer (RFC 8414 section 3.3).

## F11. Several authorization servers

RFC 9728 allows a list of authorization servers. The profile does not say which one issues resolver
tokens. If the list has more than one entry, the host refuses to select one and requires
`--authorization-server`.

## F12. The issuer identity is the protected resource, not the URL that was called

The host records the issuer of a reference and later resolves it only at that issuer. By default the host
uses the MCP URL. A server may publish its RFC 9728 metadata for a parent resource, for example its origin,
so that one authorization covers several endpoints. The `resource` value then differs from the MCP URL, and
the host cannot tell from the profile which value is the issuer. The host takes the issuer from
`--resource` and refuses to run when the MCP URL does not lie under it. The concept should define the
issuer as the RFC 9728 `resource` value.

## F13. Where a host learns the resolve scope

RFC 8414 and RFC 9728 list scopes in `scopes_supported`. Many MCP clients request every scope listed there. A
server that lists the resolve scope there makes those clients request it together with their agent scopes,
and the profile requires that such a mixed request gets neither. The tested server therefore names the
scope only in its discovery object, and the host reads it from there (`--resolve-scope` overrides). The
concept should name the place.
