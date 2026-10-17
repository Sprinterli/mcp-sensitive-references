# Sensitive References v1: host and resolver profile draft

This is a concrete revision target for discussion, not an MCP SEP and not a final extension identifier. It applies the design authority's canonical text-token decision without adding a custom `ContentBlock`.

## Negotiation

The eventual reverse-DNS extension identifier is deliberately left to its controlling organization. A client and server enable Sensitive References only through the current MCP `ClientCapabilities.extensions` and `ServerCapabilities.extensions` maps. A token-shaped string never negotiates support.

The standard outer shape is:

```json
{
  "extensions": {
    "<controlled-prefix>/sensitive-references": { "...extension settings...": true }
  }
}
```

The Sensitive References settings object needs to state, at minimum:

```json
{
  "versions": ["1"],
  "resolver_profiles": ["oauth-resolver-1"],
  "sink_profiles": ["local-file-1"]
}
```

The exact identifier and settings fields remain pre-SEP. The outer `extensions` map itself is current MCP schema, and clients advertise their capability map per request rather than relying on a legacy initialization handshake.

`schema/sensitive-references-settings.schema.json` is the matching draft JSON Schema and intentionally validates only this extension's settings object, not the outer MCP capability map.

## Token and host rules

The canonical v1 token is exactly `⟦sref:<kind>:<id>⟧`.

- `kind` is ASCII `[A-Za-z0-9_-]{1,32}` and advisory.
- `id` is ASCII base64url/ULID-safe `[A-Za-z0-9_-]{20,128}` and opaque.
- Hosts MUST match tokens as exact Unicode code points and MUST NOT normalize, case-fold, trim, or reconstruct a token for identity.
- A host may record an observation only from an authenticated MCP tool result after extension negotiation. It records the exact token, the authenticated issuer/protected-resource identity, and first-observed time.
- A reappearing token resolves only if its exact string has one trusted issuer. Zero issuers and multiple issuers fail closed.
- An issuer MUST bind lifecycle to its random generation-safe ID. Unknown, expired, or revoked IDs fail closed and cannot be rebound to another value.

## Candidate host hooks

1. After decoding an authenticated `tools/call` result, inspect text content and every string value in `structuredContent` for canonical tokens and record observations.
2. Before an eligible local-file write, extract exact tokens from the proposed content, resolve only trusted and unambiguous observations, and materialize only after every batch succeeds.
3. Return the original reference-bearing content to the model. The protected sink may report the destination and status, but not plaintext.
4. Apply integration-specific redaction to downstream output that could echo a materialized value.

## OAuth Resolver Profile (`oauth-resolver-1`)

The resolver is a separate OAuth client for the same protected resource. It obtains its own Authorization Code + PKCE token with a narrow, deployment-defined resolve scope (the prototype uses `sensitive-references.resolve`). The issuer/resource server validates all of the following for every batch:

1. access token audience/resource equals the issuer's protected resource;
2. token has the resolve scope;
3. authenticated subject is authorized for every reference;
4. every reference is issued, current, and non-revoked; and
5. request and audit limits pass.

Failure returns no plaintext values for the batch. The ordinary MCP agent token neither appears in this profile nor implicitly grants resolve rights.

## Local file sink profile (`local-file-1`)

The host supplies a local destination chosen under its own filesystem policy. The resolver receives a sink context containing only the sink type, destination, and authenticated principal. The prototype validates the type and then writes a fully materialized temporary file followed by an atomic replace. Command interpolation, broad filesystem policy, and generic output redaction are explicitly deferred.

## Test vectors

| Input | Expected |
|---|---|
| `⟦sref:email:AbCdEfGhIjKlMnOpQrStUvWx1234⟧` | valid token |
| `⟦sref:email:short⟧` | invalid: ID too short |
| `⟦sref:email:AbCdEfGhIjKlMnOpQrStUvWx1234⟧ ` | not an exact token identity |
| `［sref:email:AbCdEfGhIjKlMnOpQrStUvWx1234］` | invalid: lookalike brackets |
| same valid token from two authenticated issuers | ambiguous; do not resolve |
| same valid token in local file without trusted observation | ordinary text; do not resolve |
