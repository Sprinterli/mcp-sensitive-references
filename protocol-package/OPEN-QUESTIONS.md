# Open questions after M6

**Status: experimental.** These questions stay open after the reference server and the test host. Each
question lists options and one recommendation. A recommendation is not a decision. The questions of
[../OPEN-QUESTIONS.md](../OPEN-QUESTIONS.md) stay valid. This file names the item there that a question
continues.

## OQ-1. Two independent issuers (P2)

A user reads a record from server A and writes it to server B. Server B does not know the reference of
server A. The flow works only if the host resolves the reference and sends the plaintext to server B. That
is cross-server disclosure, which concept 0.5 defers (`SPEC-DRAFT.md`, "Non-goals"). The plan of the
reference server says that users expect this flow (P2). Continues concept item 10.

- Option A: keep it deferred in version 1. The host passes the reference as text.
- Option B: define a host-side sink "tool argument" that resolves before a call to another server, with a
  separate consent per destination server.
- Option C: define server-to-server redemption.

**Recommendation:** A for version 1. State the gap in the SEP as a known limit, and collect use cases for B.
B needs a destination identity that the host can show to the user, and no implementation tested it.

## OQ-2. Where the masked display travels (P3)

Concept 0.5 lets a masked display "accompany" a token (`WIRE-REPRESENTATION.md`). If the display is outside
the brackets, a model that copies the token and the display into a write puts the display text next to
the resolved value.

- Option A: an optional, non-authoritative display segment inside the token.
- Option B: a rule that a resolver or a sink removes an adjacent display.
- Option C: no display on the wire. A host renders a display from metadata.

**Recommendation:** C. Both implementations use the canonical form without a display (plan section 6, M3).
A and B change the grammar or add a fragile text rule. Neither implementation tested A or B.

## OQ-3. The issuer-side sink and the agent-token rule (P1)

The reference server resolves references into its own outbound calls under the agent token (SC-18).
Concept 0.5 says that the agent token "must not automatically grant plaintext resolution rights".

- Option A: read the rule as a rule for plaintext that leaves the issuer. Define the issuer-side sink.
- Option B: read the rule strictly. An issuer-side sink then needs a second grant.

**Recommendation:** A, with the checks of SC-18. Plaintext in this case goes from the issuer to its own
connector and never to the host or the model. B adds a grant without a security gain inside one principal
(plan section 3).

## OQ-4. Consent and dynamic client registration with loopback ports (F5)

The host registers a new client for each interactive authorization, because each loopback port gives a new
redirect URI. RFC 8252 section 7.3 asks the authorization server to accept any loopback port, but dynamic
registration stores a URI with a port. Consent per user and client then repeats on each new
authorization.

- Option A: the authorization server matches loopback redirect URIs without the port (RFC 8252 section 7.3).
  The host keeps one client.
- Option B: consent per user and software identity (for example `software_id` in RFC 7591).
- Option C: accept the repeat. The token cache makes it rare (E2: zero consent pages with a cached token).

**Recommendation:** A. It follows an existing RFC and keeps the consent bound to one client. Not tested by
either implementation.

## OQ-5. Sender-constrained resolver tokens (F6)

Neither implementation uses DPoP (RFC 9449) or mTLS. A stolen resolver token works until it expires.
Continues concept item 7.

- Option A: require DPoP for `oauth-resolver-1`.
- Option B: recommend DPoP, require a short access-token lifetime and refresh rotation.

**Recommendation:** B for the first profile version, A as a candidate for a second version. A stolen
refresh token is the larger risk, and rotation with client binding limits it (TM-8).

## OQ-6. The destination field (F8)

- Option A: an absolute path (today).
- Option B: a label that the host chooses, for example the file name.
- Option C: a keyed hash of the path.

**Recommendation:** B. The server uses the field for audit only. A label is readable in an audit and does
not show the file system layout. C hides more but makes the audit useless to a person.

## OQ-7. Durable host provenance

The test host keeps provenance in memory and loses it on restart (`HOST-INTEGRATION.md`). The reference
server is not a host and does not answer this question. Continues concept item 1.

- Option A: an integrity-protected local store, keyed by a host secret.
- Option B: no persistence. After a restart the host needs a new observation.

**Recommendation:** B for version 1, because it fails closed and needs no new mechanism. A needs a second
host implementation before a standard can define it.

## OQ-8. Location of the discovery object

SC-02 proposes the RFC 9728 metadata. Continues concept item 4.

- Option A: RFC 9728 metadata with a registered field name.
- Option B: the extension settings object.
- Option C: both.

**Recommendation:** A. The resolver token belongs to the protected resource, not to the MCP session. The
settings object is authenticated by the agent token and has `additionalProperties: false` today (F1).

## OQ-9. The extension identifier (P7)

Continues concept item 3. **Recommendation:** ask the MCP project for an identifier before the SEP. Until
then, implementations take the identifier from configuration (SC-15).

## OQ-10. The subject of an opaque resolver token

`RESOLVER-PROFILE.md` asks for `sub` or an equivalent stable claim. The reference server uses an opaque
token with a server-side record, so no claim is visible to anyone but the server. Continues concept item 5.

- Option A: require JWT access tokens with `sub`.
- Option B: require only that the resource server binds the token to a stable subject, by any means.

**Recommendation:** B. The subject matters only to the resource server, which checks it on every resolve.

## OQ-11. Reference lifetime (P5)

- Option A: a fixed minimum lifetime in the profile.
- Option B: a lifetime that the server documents, and the reason `expired` after it (SC-13).

**Recommendation:** B. Workflows differ too much for one fixed value.
