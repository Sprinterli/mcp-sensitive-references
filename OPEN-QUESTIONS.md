# Open questions and remaining design decisions

**Status: Concept 0.6 draft.** This file is not normative. It lists what still needs a decision.

A **provisional v1 design decision** is the working normative design for version 1. Implementations can
differ from it; [IMPLEMENTATION-EVIDENCE.md](IMPLEMENTATION-EVIDENCE.md) records each known difference. The
normative text marks it with **Provisional (OQ-n)**. No community review confirmed it. The options stay
open. OQ-1 to OQ-11 come from [protocol-package/OPEN-QUESTIONS.md](protocol-package/OPEN-QUESTIONS.md).
OQ-12 to OQ-18 are new in Concept 0.6.

## Remaining design decisions

| Id | Decision | Provisional v1 design decision | Where the text uses it |
|---|---|---|---|
| OQ-1 | Two independent issuers | A: keep cross-server disclosure deferred | SPEC-DRAFT.md, section 9 |
| OQ-2 | Where a masked display travels | C: no display on the wire | WIRE-REPRESENTATION.md, section 4 |
| OQ-3 | The issuer-side sink and the agent-token rule (SC-18) | None in Concept 0.6. The package proposed A. An interim floor applies. | SPEC-DRAFT.md, section 6.4 |
| OQ-4 | Consent with dynamic registration and loopback ports | A: any loopback port, one client | RESOLVER-PROFILE.md, section 9.2 |
| OQ-5 | Sender-constrained resolver tokens | B: DPoP optional; short lifetime and rotation | RESOLVER-PROFILE.md, section 11 |
| OQ-6 | The destination field | B: a label | RESOLVER-PROFILE.md, section 12.1; LOCAL-FILE-PROFILE.md, section 3 |
| OQ-7 | Durable host provenance | A host can persist; loss fails closed | HOST-INTEGRATION.md, section 3 |
| OQ-8 | Location of the discovery object | A: RFC 9728 metadata | RESOLVER-PROFILE.md, section 4 |
| OQ-9 | The extension identifier | Ask the MCP project; configuration until then | SPEC-DRAFT.md, section 4 |
| OQ-10 | The subject of an opaque resolver token | B: any stable binding at the resource server | RESOLVER-PROFILE.md, section 14 |
| OQ-11 | Reference lifetime | B: the server documents it | SPEC-DRAFT.md, section 5.3 |
| OQ-12 | Issuer identity for non-HTTP transports | none | HOST-INTEGRATION.md, section 2 |
| OQ-13 | Conflict with the MCP root fallback; reading of the RFC 9728 trailing slash | Do not use the root document for resolution | RESOLVER-PROFILE.md, section 3 |
| OQ-14 | A resolve endpoint on another origin | Refuse it | RESOLVER-PROFILE.md, section 6 |
| OQ-15 | Refusal of the IPv6 loopback literal | A server can refuse `[::1]` | RESOLVER-PROFILE.md, section 9.2 |
| OQ-16 | Who authors the content of a local-file write | Both sources permitted | LOCAL-FILE-PROFILE.md, section 1 |
| OQ-17 | Non-string sensitive values | none | none |
| OQ-18 | Audit and rate-limit minimum; recovery beyond section 11.1 | none | RESOLVER-PROFILE.md, sections 11.1 and 15 |

## OQ-1. Two independent issuers

A user reads a record from server A and writes it to server B. Server B does not know the reference of
server A. The flow works only if the host resolves the reference and sends the plaintext to server B. That
is cross-server disclosure.

- Option A: keep it deferred in version 1. The host passes the reference as text.
- Option B: define a host-side sink "tool argument". It resolves before a call to another server, with a
  separate consent for each destination server.
- Option C: define server-to-server redemption.

**Provisional v1 design decision:** A. The SEP states the gap as a known limit and collects use cases for
B. B needs a destination identity that the host can show to the user. No implementation tested B.

## OQ-2. Where a masked display travels

If a display is outside the reference, a model that copies the reference and the display into a write puts
the display text next to the resolved value.

- Option A: an optional, non-authoritative display segment inside the reference.
- Option B: a rule that a resolver or a sink removes an adjacent display.
- Option C: no display on the wire. A host renders a display from metadata.

**Provisional v1 design decision:** C. Both implementations use the canonical form without a display. A
and B change the grammar or add a fragile text rule. No implementation tested A or B.

## OQ-3. The issuer-side sink and the agent-token rule (SC-18)

The reference server resolves references into its own outbound calls under the agent token. The core says
that the ordinary agent token must not automatically grant plaintext resolution rights (SPEC-DRAFT.md,
section 5.2). The core does not decide whether this rule also covers plaintext that stays inside the
issuer.

- Option A: read the rule as a rule for plaintext that leaves the issuer. Define the issuer-side sink with
  the checks below.
- Option B: read the rule strictly. An issuer-side sink then needs a second grant.

The checks of SC-18 for option A: possession of a reference does not authorize resolution. The issuer
resolves a reference only after an explicit authorization decision for that tool execution. The decision
uses the authenticated principal, the tool and the action that the issuer authorized for that principal,
and the owner of the reference. The reference must be exact and current. A failure of one reference refuses
the whole call. The issuer replaces each resolved value with its reference in every model-visible result.

**No provisional decision in Concept 0.6.** The package proposed A ([protocol-package/OPEN-QUESTIONS.md](protocol-package/OPEN-QUESTIONS.md)).

**Interim floor.** Until OQ-3 is decided, SPEC-DRAFT.md, section 6.4, requires the checks above for every
issuer-side use. The floor holds under option A and under option B. It does not make issuer-side use part
of the conformant scope of version 1.

**Why Concept 0.6 does not integrate SC-18.** Option A lets the agent token, together with the tool
authorization, release plaintext into an outbound call. In Concept 0.5, resolution authority was separate
from the agent token. Option A can therefore weaken the separation of resolution authority from ordinary
access. The required controls of SECURITY-MODEL.md must not weaken without a community decision. Also, no
reference server test shows the refusal of an authorized tool call with the reference of another principal
([protocol-package/THREAT-MODEL.md](protocol-package/THREAT-MODEL.md), TM-10).

## OQ-4. Consent with dynamic client registration and loopback ports

A host that registers a new client for each authorization causes a new consent each time, because each
loopback port gives a new redirect URI.

- Option A: the authorization server matches loopback IP redirect URIs as exact strings, except the port
  (RFC 8252 section 7.3, RFC 9700 section 2.1). The host keeps one client.
- Option B: consent per user and software identity, for example `software_id` (RFC 7591).
- Option C: accept the repeat. The token cache makes it rare.

**Provisional v1 design decision:** A. It follows an existing RFC and keeps the consent bound to one
client. No automated test covers it. One operator run observed that exact port matching breaks a host that
reuses a client with a new port.

## OQ-5. Sender-constrained resolver tokens

Neither implementation uses DPoP (RFC 9449) or mTLS. A stolen resolver token works until it expires.

- Option A: require DPoP for `oauth-resolver-1`.
- Option B: recommend DPoP, and require a short access-token lifetime and refresh rotation.

**Provisional v1 design decision:** B for the first profile version. A is a candidate for a second
version.

## OQ-6. The destination field

- Option A: an absolute path.
- Option B: a label that the host chooses, for example the file name.
- Option C: a keyed hash of the path.

**Provisional v1 design decision:** B. The server uses the field for audit only. A label is readable in an
audit and does not show the file system layout. The reference host still sends an absolute path.

## OQ-7. Durable host provenance

- Option A: an integrity-protected local store, keyed by a host secret.
- Option B: no persistence. After a restart, the host needs a new observation.

**Provisional v1 design decision:** a host can persist provenance (A). Loss of trustworthy provenance fails
closed. A host without persistence (B) conforms. The integrity mechanism and the freshness of a stored
observation stay open. A standard needs a second host implementation before it can define both.

## OQ-8. Location of the discovery object

- Option A: RFC 9728 metadata with a registered field name.
- Option B: the extension settings object.
- Option C: both.

**Provisional v1 design decision:** A. The resolver token belongs to the protected resource, not to the MCP
session. The field name `sensitive_references` is not registered in the IANA "OAuth Protected Resource
Metadata" registry. A SEP must register it or choose another location.

## OQ-9. The extension identifier

**Provisional v1 design decision:** ask the MCP project for an identifier before the SEP. Until then,
implementations take the identifier from configuration.

## OQ-10. The subject of an opaque resolver token

- Option A: require JWT access tokens with `sub`.
- Option B: require only that the resource server binds the token to a stable subject, by any means.

**Provisional v1 design decision:** B. The subject matters only to the resource server, which checks it on
every resolve request.

## OQ-11. Reference lifetime

- Option A: a fixed minimum lifetime in the profile.
- Option B: a lifetime that the server documents, and the reason `expired` after it.

**Provisional v1 design decision:** B. Workflows differ too much for one fixed value.

## OQ-12. Issuer identity for non-HTTP transports

Concept 0.6 defines the issuer identity for an MCP server over HTTP only.

- Option A: define an identity for stdio, for example from the host configuration of the server.
- Option B: do not support references over stdio in version 1.

No provisional decision. HOST-INTEGRATION.md, section 2, forbids observations for such a transport until a
later version defines the identity.

## OQ-13. Discovery conflict with the MCP authorization specification

The MCP authorization specification (version 2025-11-25) permits a fallback to the well-known URL at the
origin root. RFC 9728 section 3.3 makes the `resource` of that document the origin, not the MCP URL.

- Option A: no root fallback for resolution (Concept 0.6).
- Option B: accept a root document that names the MCP URL. This breaks RFC 9728 section 3.3.
- Option C: change the MCP specification for servers that offer this extension.

**Provisional v1 design decision:** A. A SEP must resolve the conflict with the MCP project. The reading of
the RFC 9728 section 3.1 rule for a trailing slash is also not confirmed.

## OQ-14. A resolve endpoint on another origin

- Option A: refuse it (Concept 0.6).
- Option B: define a separately authenticated binding of the endpoint to the resource, and a token with
  the endpoint as its audience.

**Provisional v1 design decision:** A.

## OQ-15. Refusal of the IPv6 loopback literal

RFC 8252 section 7.3 counts `[::1]` as a loopback IP redirect URI. In one tested browser, a consent page
policy that listed `[::1]` did not let the redirect through.

- Option A: a server can refuse `[::1]`, and a host uses `127.0.0.1` (Concept 0.6).
- Option B: a server must accept both literals.

**Provisional v1 design decision:** A. The evidence is one observation in one browser. A later version must
remove the permission when browsers deliver the redirect to `[::1]`.

## OQ-16. Who authors the content of a local-file write

- Option A: the model writes the content. Only observed references resolve.
- Option B: the host takes the content from its own configuration only.

**Provisional v1 design decision:** both sources are permitted (LOCAL-FILE-PROFILE.md, section 1). The
reference host does B. The use case of Concept 0.5 (the model routes a reference into a file) needs A. No
implementation tested A.

## OQ-17. Non-string sensitive values

Version 1 replaces string values only. A number or a structured value cannot keep its schema type as a
reference.

No provisional decision.

## OQ-18. Audit, rate limits and recovery

The minimum content of the audit event and the rate limits are not decided. RESOLVER-PROFILE.md, section
11.1, defines the minimum recovery of `oauth-resolver-1`. Recovery beyond it is not decided, for example a
grace period for a rotated refresh token that the host lost before it wrote its cache.

No provisional decision.

## Questions of Concept 0.5

| Concept 0.5 item | State in Concept 0.6 |
|---|---|
| 1. Provenance across restart | OQ-7 |
| 2. Host integration point for local sinks | Answered for local files by `local-file-1`. Command and document sinks stay open. |
| 3. Extension identifier and settings | Settings in WIRE-REPRESENTATION.md, section 3. Identifier: OQ-9. |
| 4. Resolver endpoint discovery | OQ-8 |
| 5. Stable subject claim | OQ-10 |
| 6. Authorization servers for validation | Open. See IMPLEMENTATION-EVIDENCE.md. |
| 7. Sender constraint | OQ-5 |
| 8. Audit, rate limit, consent, recovery and revocation | Consent: RESOLVER-PROFILE.md, section 10. Minimum recovery: section 11.1. The rest: OQ-18. |
| 9. Non-string sensitive values | OQ-17 |
| 10. Cross-server redemption | OQ-1 |
