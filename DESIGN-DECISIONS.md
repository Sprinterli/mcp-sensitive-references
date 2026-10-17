# Design decisions

## Current decisions

- The name is Sensitive References. The scope includes PII, secrets, financial, health, and business data.
- Classification is upstream and out of scope.
- A reference is not a secret and has no bearer authority.
- Version 1 uses canonical opaque text tokens in ordinary string fields.
- The host derives issuer provenance from an authenticated negotiated result.
- `_meta` is not a secrecy boundary.
- Reference identifiers must not silently rebind to another value generation.
- Resolution occurs outside ordinary model-visible results.
- Version 1 defers arbitrary cross-server redemption.
- Unsupported peers use their existing disclosure policy. Token-shaped text alone claims no protection.

## Concept 0.5 changes from 0.4

Concept 0.5 makes host provenance operational: observations require negotiated, authenticated results;
unknown and ambiguous references fail closed; and loss of provenance after restart cannot trigger guessing.
It makes all-or-nothing behavior mandatory for `local-file-1`. It states stable resolver subject identity.
It also changes the OAuth wording to “validated as a viable resolver-profile candidate.”

See the prototype [DESIGN-DELTA-0.4.md](prototype/DESIGN-DELTA-0.4.md) for evidence and rationale.
