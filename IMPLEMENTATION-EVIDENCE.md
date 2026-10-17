# Implementation evidence

The prototype is evidence for limited mechanics. It is not an interoperability implementation or a standard.

## Demonstrated by executable tests

- Canonical text references work as ordinary string values.
- Host-held issuer provenance rejects forged and unobserved tokens.
- Wrong issuer and ambiguous issuer bindings fail closed.
- Unknown, revoked, and expired references fail closed.
- Resolver authorization is separate from reference possession.
- Equal plaintext values receive unrelated opaque identifiers.
- Resolution batches are all-or-nothing.
- A protected local file receives plaintext while the model-facing result retains references.
- Keycloak JWT/JWKS and Authorization Code plus PKCE probes validate one OAuth profile candidate.

## Not demonstrated

The prototype does not prove MCP-host interoperability, final extension settings, resolver discovery,
durable provenance across restart, final resolver authorization, portability across authorization servers,
or cross-server delegation.

## Implementation references

[maisecrets](https://github.com/Mcpgate-de/maisecrets) and MCPGate informed the design through prior
implementation experience. They are not the protocol, nor are their product mechanics proposed as core
requirements. Client-Vault provides historical evidence for out-of-model resolution, first-sighting and
origin binding, stale-reference protection, fail-closed behavior, and separate resolver authorization.
