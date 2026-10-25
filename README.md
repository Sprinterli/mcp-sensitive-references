# Sensitive References for MCP

> **Status: pre-SEP design exploration.**
>
> This repository explores a possible MCP extension for opaque references to server-held sensitive data.
> It is not an MCP standard, not an accepted SEP, and is not affiliated with the Model Context Protocol project.

An MCP server can know a customer email, an API key, a health identifier, or another sensitive value.
An agent can need that value in a later action without needing to read it.

Sensitive References explore another option:

```text
email = ⟦sref:email:01JCK7KF9X4Y3M4N6Q6YB2D8P0⟧
```

The model can carry, sort, format, and route the reference. An authorized non-model resolver can
materialize the plaintext into an eligible sink when an action requires it. The short goal is:
**referencable but not visible**.

## Problem

Today, a server often exposes plaintext when an agent must later use a value. Redaction can also make
the required file, document, or action impossible. This work explores an MCP extension that separates
reference from plaintext and reference possession from resolution authority.

## Definition

A Sensitive Reference is an opaque identifier issued by an MCP server in place of a sensitive plaintext
value. It lets an agent refer to that value without receiving its plaintext. An authorized non-model
component associated with the issuer can later resolve it.

A Sensitive Reference is not an authorization grant. Possession alone must not authorize resolution.

## Core security property

For a supporting host, resolver profile, and eligible sink, sensitive data remains referencable and
actionable without requiring plaintext in model context.

## Architecture

1. A negotiated supporting MCP server replaces a sensitive string with a canonical text reference.
2. The host records trusted observation state: `(token, authenticated issuer, first_observed, optional metadata)`.
3. The model may copy the token. Token-shaped text gains no provenance by itself.
4. A protected sink asks a separately authorized non-model resolver to materialize known references.
5. The sink returns reference-only content to the model and sends plaintext only to the eligible destination.

The token contains no authoritative issuer, resolver URL, subject, or plaintext. If one token has trusted
observations from multiple issuers, resolution fails closed. If the host loses provenance after restart,
it fails closed or obtains a new trusted observation.

See [SPEC-DRAFT.md](SPEC-DRAFT.md), [WIRE-REPRESENTATION.md](WIRE-REPRESENTATION.md), and
[HOST-INTEGRATION.md](HOST-INTEGRATION.md).

## Prototype evidence

The included [prototype](prototype/) demonstrates canonical text references in ordinary string schemas,
trusted issuer provenance, rejection of forged, wrong-issuer, ambiguous, unknown, revoked, expired,
and unauthorized references, and all-or-nothing local-file materialization. Model-facing results remain
reference-only. Equal plaintext values receive unrelated opaque IDs.

The prototype also includes local Keycloak probes for JWT/JWKS verification and Authorization Code plus
PKCE. These probes validate a separate OAuth resolver client as a viable resolver-profile candidate.
They do not decide a final resolver profile or prove portability across authorization servers.

Run the prototype:

```bash
cd prototype
python3 -m pip install -e '.[mcp-demo,resolver-http-demo]'
PYTHONPATH=src:. python3 -m unittest discover -s tests -v
```

## Protocol package (experimental)

[protocol-package/](protocol-package/) collects proposed changes to concept 0.5, the tested resolver and
local-file profiles, conformance results, and a SEP readiness checklist. It does not change concept 0.5.

## Out of scope

This proposal does not define sensitive-data classification, DLP, NER, user interfaces, databases,
generic filesystem policy, cross-server redemption, delegation, or a new MCP `ContentBlock` type.
It does not rely on `_meta` as a secrecy boundary.

## Open design questions

- How should a host persist trusted provenance across restart?
- Which host integration point should protect local sinks?
- Where should resolver endpoint discovery live?
- Is a separate narrow OAuth resolver client the best interoperable profile?
- What sender constraint, audit, and recovery rules should a profile require?
- Should cross-server redemption remain deferred for v1?

See [OPEN-QUESTIONS.md](OPEN-QUESTIONS.md).

## Implementation evidence

The design is informed by production implementation experience in
[maisecrets](https://github.com/Mcpgate-de/maisecrets) and MCPGate, but this repository separates the
protocol design from those implementations. Client-Vault is historical implementation and security
evidence, not a competing protocol. See [IMPLEMENTATION-EVIDENCE.md](IMPLEMENTATION-EVIDENCE.md) and
[PRIOR-ART.md](PRIOR-ART.md).

## Community discussion

[COMMUNITY-DISCUSSION.md](COMMUNITY-DISCUSSION.md) is a ready-to-post discussion draft. Feedback about
host provenance, protected sinks, resolver profiles, and extension fit is welcome.

## Disclaimer

This repository is independent pre-SEP design work. It does not imply endorsement by Anthropic, OpenAI,
MCP maintainers, or an MCP working group.

## License

[Apache-2.0](LICENSE)
