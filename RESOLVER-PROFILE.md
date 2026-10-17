# Resolver profile candidates

The core does not define one resolver protocol. A profile defines endpoint discovery, authorization,
stable subject identity, lifecycle errors, batching, audit, limits, and recovery.

## OAuth Resolver Profile candidate

A separate OAuth resolver client can request authorization for the same protected resource. It can use a
narrow resolve-specific privilege and Authorization Code plus PKCE. The resource server validates the
token audience, the resolve privilege, token validity, and a stable subject that matches every requested
reference.

The Keycloak prototype validates this as a viable resolver-profile candidate. Keycloak acted as an
authorization server. A separate local HTTP resolver surface verified Keycloak JWTs through JWKS, then
enforced audience, scope, and subject checks. The probes used temporary Keycloak objects and removed them.

This does not prove interoperability with other authorization servers, a deployed MCP resource server,
or final endpoint discovery. It does not decide the profile. The ordinary MCP agent token must not resolve
plaintext unless it has a separate explicit resolve grant.

## Subject identity

The resolver must authenticate as a stable principal. A profile should use `sub` by default or declare an
equivalent stable subject claim. It must not infer identity from display names, token text, or model input.

## Deferred profile work

Endpoint discovery, scope naming, consent, durable resolver credentials, sender constraint such as DPoP,
audit, rate limits, and revocation recovery remain open.
