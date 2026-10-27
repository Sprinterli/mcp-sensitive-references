# Design decisions

**Status: Concept 0.6 draft.** This file is not normative. It records the decisions that the normative
text applies. The decisions that remain open are in
[OPEN-QUESTIONS.md, "Remaining design decisions"](OPEN-QUESTIONS.md#remaining-design-decisions).

## Decisions kept from Concept 0.5

- The name is Sensitive References. The scope includes PII, secrets, financial, health and business data.
- Classification is upstream and out of scope.
- A reference is not a secret and has no bearer authority.
- Version 1 uses one canonical text form in ordinary string fields.
- The host derives issuer provenance from an authenticated, negotiated result.
- `_meta` is not a secrecy boundary.
- A reference identifier does not rebind to another value generation.
- Resolution happens outside ordinary model-visible results.
- Resolution authorization is separate from reference possession and from the ordinary agent token.
- Version 1 defers arbitrary cross-server redemption.
- An unsupported peer uses its existing disclosure policy. Reference-shaped text alone claims no
  protection.

## Decisions added in Concept 0.6

Each decision names its source in [protocol-package/SPEC-CHANGES.md](protocol-package/SPEC-CHANGES.md).
[CHANGELOG.md](CHANGELOG.md) lists every change.

- **Issuer identity.** Over HTTP, the issuer identity is the MCP URL as given, compared as an exact string.
  `oauth-resolver-1` requires an RFC 9728 `resource` value identical to it (SC-01).
- **Discovery.** The host gets the metadata from the challenge first, then from the path-inserted
  well-known URL, and never from the origin root. Without metadata, the host does not resolve (SC-01).
- **Fetch policy.** The host sends no request to a non-public address that a server supplied. It follows
  no redirect, uses no environment proxy and connects to the checked address (SC-01).
- **Discovery object.** The resolve endpoint and scope live in a `sensitive_references` object in the
  RFC 9728 metadata (SC-02). The location is provisional (OQ-8).
- **Scope.** The resolve scope stays out of `scopes_supported`, and mixed scopes get neither (SC-03).
- **Endpoint origin.** The resolve endpoint is on the origin of the resource (SC-04).
- **Token classes.** A resolver token and an agent token never stand in for each other (SC-05).
- **Consent.** One approval binds subject, client, resource, resolve scope and sink-profile set (SC-06).
- **Token handling.** Short access tokens, rotating refresh tokens, an owner-only cache and one renewal
  after 401 (SC-07).
- **Authorization checks.** PKCE S256, `state`, RFC 9207 `iss` and the RFC 8414 issuer (SC-08).
- **Batches.** At least 100 references per request. A host that splits a write writes nothing until every
  request succeeded (SC-09).
- **Sink context.** The wire carries `sink_type` and `destination`, never a principal (SC-10).
- **Errors.** One error format with fixed codes, and one definition of protected data (SC-11).
- **Refusal in a tool call.** `isError: true` with a fixed `structuredContent` shape (SC-12).
- **Lifetime.** The server documents the lifetime; `expired` while it keeps the record (SC-13).
- **Registry integrity.** Each binding is authenticated and bound to its principal (SC-14).
- **Identifier.** Configuration until the MCP project assigns one (SC-15).
- **Protocol versions.** References only on protocol versions with an `extensions` map (SC-16).
- **Server text.** No marker outside an issued reference (SC-17).
- **Supporting host.** A host that cannot verify negotiation does not declare the extension (SC-19).
- **Loopback redirects.** Any loopback port; `127.0.0.1` always accepted; `form-action` permits the
  loopback origin (SC-20).

## Decision not integrated

- **The issuer-side sink (SC-18)** is not part of the normative text. It can weaken the separation of
  resolution authority from the agent token. OQ-3 has no provisional decision. SPEC-DRAFT.md, section 6.4,
  sets an interim floor for any issuer-side use. See [OPEN-QUESTIONS.md, OQ-3](OPEN-QUESTIONS.md#oq-3-the-issuer-side-sink-and-the-agent-token-rule-sc-18).
