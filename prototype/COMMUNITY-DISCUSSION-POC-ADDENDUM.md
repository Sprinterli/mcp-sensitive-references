# PoC addendum for the community discussion draft

This addendum updates the existing pre-SEP discussion draft with implementation evidence. It does not change the proposal's scope or claim standards status.

## Evidence now available

- A Python prototype emits canonical text references in ordinary structured string fields and an MCP SDK tool preserves that schema shape.
- Host provenance blocks forged/unobserved references and fails closed on issuer ambiguity.
- A protected local-file sink resolves only complete trusted batches and does not return plaintext in its model-facing result.
- A local Keycloak 26 deployment verified two external-AS paths:
  1. a separately authorized resolver token obtained through a client-credentials probe, then validated through JWKS at an issuer-bound HTTP resolver endpoint; and
  2. a temporary public resolver client using Authorization Code + PKCE, state validation, resource audience, resolver scope, subject binding, and the same protected endpoint.

The probes create and remove their Keycloak users, clients, scopes, and mappers. They do not modify AI Gateway application code.

## Implementation findings worth reviewer attention

- The text-token approach is sufficient for v1 interoperability when the host records issuer provenance outside model-visible content.
- Existing SDK structured-output validation requires tools to describe concrete schemas. This is compatible with string-valued references, but examples should include typed output schemas.
- Keycloak can issue lightweight access tokens without `sub` for a minimal client. The resolver correctly fails closed in that case. A profile should require a stable subject claim; issuer-specific client-mapper setup belongs in deployment guidance.
- A local HTTP-only Keycloak test container marks authentication cookies Secure. The automated test relaxes that solely in-memory; normal deployments require HTTPS and should not reproduce that behavior.

## Questions refined by the PoC

1. Should an OAuth Resolver Profile require `sub` explicitly, or permit a deployment-declared stable subject claim?
2. Should resolver-endpoint discovery be anchored in Protected Resource Metadata or the negotiated extension payload?
3. Should the first sink profile normatively require atomic file replacement and all-or-nothing response semantics?
4. What standard treatment should a host use for downstream output that might echo materialized plaintext?
