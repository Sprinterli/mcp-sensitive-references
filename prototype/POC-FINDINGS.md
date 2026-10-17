# PoC findings for a community discussion

## Confirmed

- A canonical text token works in normal MCP structured string fields and FastMCP output schemas.
- Host-held `(token, issuer)` provenance prevents model text from selecting a resolver origin.
- A protected sink can materialize a complete batch while retaining the original reference-bearing content for the model.
- A separate OAuth resolver client works with an external authorization server. The local Keycloak probe exercised discovery, Authorization Code + PKCE, state checking, JWT/JWKS verification, audience, scope, subject, and an issuer-bound resolver endpoint.
- A missing `sub` claim is safely rejectable. The Keycloak test client required an explicit mapper; a portable profile should require a stable subject claim rather than infer identity from a token, display string, or reference.

## Still needs a specification decision

1. The reverse-DNS extension identifier and its exact settings payload. The current MCP outer form is already `ClientCapabilities.extensions` / `ServerCapabilities.extensions`, keyed by extension identifier.
2. Resolver endpoint discovery location: Protected Resource Metadata versus extension capability settings.
3. Exact resolver scope spelling and whether it is standardized or deployment-defined.
4. Requirements for subject stability and sender-constrained resolver tokens.
5. Durable resolver-token storage, consent/recovery UX, audit/rate limits, and output-echo handling.
6. The normative local-file sink policy: allowed destinations, atomicity limits, and safe error reporting.

## Recommendation

Take the current core plus an OAuth Resolver Profile and `local-file-1` sink profile to a community discussion. Do not propose a new `ContentBlock`, `_meta` secrecy, server-to-server redemption, or automatic use with unsupported clients.
