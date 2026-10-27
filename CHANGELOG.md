# Changelog

## Concept 0.6 (draft)

Concept 0.6 puts the validated protocol decisions of [protocol-package/](protocol-package/) into one
normative text. Each line names its source: an SC entry of
[protocol-package/SPEC-CHANGES.md](protocol-package/SPEC-CHANGES.md), an OQ item of
[OPEN-QUESTIONS.md](OPEN-QUESTIONS.md), or a profile file of the package.

### Structure

- The normative core is SPEC-DRAFT.md, WIRE-REPRESENTATION.md, HOST-INTEGRATION.md and SECURITY-MODEL.md.
  The profiles are RESOLVER-PROFILE.md and the new LOCAL-FILE-PROFILE.md. Evidence moved to
  IMPLEMENTATION-EVIDENCE.md. (all)
- RFC 2119/8174 key words are now used only in normative text. "Provisional (OQ-n)" marks a provisional
  decision. (all)
- The terms "reference" and "token" have one meaning each: "reference" for a Sensitive Reference, "token"
  only for credentials. (all)
- The canonical grammar, the test vectors and the settings schema moved from `prototype/` into
  WIRE-REPRESENTATION.md. (profile draft of Concept 0.5)

### Core

- References apply only to MCP protocol versions with an `extensions` map. (SC-16)
- A server emits no reference in a session in which the client did not declare the extension with a
  version that the server supports. (SC-16)
- The negotiated version is the highest common version. (new; the prototype does the same)
- "Provisional" and "Open" paragraphs are normative. The mark "(not testable on the wire)" is on the
  issuer rules of SPEC-DRAFT.md, sections 5.1, 5.3 and 5.4, and on the durable-store rules of
  HOST-INTEGRATION.md, section 3. Other local-state rules, for example in the profiles, are also not
  testable on the wire but carry no mark. (new, editorial)
- New terms: "authenticated MCP result" (a `tools/call` result after TLS server authentication),
  "owner of a reference" and "issuer-side use". (new, editorial)
- An issuer creates reference identifiers at random and never from the plaintext; equal values give no
  predictable relation. This was implicit in Concept 0.5 and its prototype. (Concept 0.5 profile draft)
- The extension identifier comes from configuration until the MCP project assigns one. (SC-15, OQ-9)
- An issuer documents the lifetime of its references. The reason is `expired` while it keeps the record,
  and can be `unknown` after. (SC-13, OQ-11)
- An issuer protects each stored binding with a MAC or an AEAD tag bound to its principal. A revocation
  survives a replay. (SC-14)
- A server emits the marker `⟦sref:` only inside a reference that it issued, and describes references in
  words in its own notices, as published in SC-17. Concept 0.6 defines "in words" as a notice without the
  marker and without reference-shaped text, so that two testers give the same verdict. (SC-17)
- A refused reference in a tool call gives `isError: true` and a fixed `structuredContent` shape. (SC-12)
- One definition of protected data, with exact representations and encodings. It applies to resolve
  answers, refusal results, sink reports, and host error texts and logs; not to ordinary issuer results or
  the model-facing sink result. (SC-11, SC-12)
- The issuer failure list no longer names "stale" and "ambiguous". A replaced value generation counts as
  revoked; "ambiguous" is a host state. (editorial)
- A host that cannot verify negotiation and the issuer is not a supporting host. (SC-19)
- Over HTTP, the issuer identity is the MCP URL as given, with its query, compared as an exact string. A
  URL with user information or a fragment is no issuer identity. (SC-01)
- A host can keep durable provenance (OQ-7, provisional). Every durable store checks each observation, fails
  closed on loss, and keeps its integrity key out of reach of the model (not provisional). New threat
  TM-13. (OQ-7)
- A host records no observation from an MCP connection that followed a redirect. (new)
- No display text on the wire next to a reference. (OQ-2, provisional)
- The issuer-side sink is not defined as a conformant feature, and OQ-3 has no provisional decision. An
  interim floor applies to every issuer-side use: no authority from possession, the owner must be the
  authenticated principal, exact and current references, whole-call refusal, references back in every
  model-visible result. (SC-18 not integrated, OQ-3)
- Concept 0.5 said the agent token must not resolve plaintext "unless it has a separate explicit resolve
  grant". Concept 0.6 replaces this with the stricter rule that an agent token never authorizes a resolve
  request. (SC-05)
- An issuer identity is defined for HTTP only. A host records no observation over stdio or another
  transport. **This narrows Concept 0.5, which did not exclude stdio servers.** (new, OQ-12)
- A resolver profile again lists audit among the things it defines. (Concept 0.5)
- The non-goal "universal plaintext secret" stays in SPEC-DRAFT.md, section 9. (Concept 0.5)
- SECURITY-MODEL.md gets a threat table TM-1 to TM-13 with controls and residual risks. (package
  THREAT-MODEL.md, OQ-7)

### `oauth-resolver-1`

- The RFC 9728 `resource` value must be identical to the MCP URL. Discovery uses the challenge first,
  then the path-inserted well-known URL, never the origin root. No metadata means no resolution. (SC-01,
  OQ-13)
- Fetch policy for every URL that a server supplies: non-public addresses by the IANA registries, local
  mode only by operator option, no redirects, no environment proxy, connection to the checked address.
  (SC-01)
- A `sensitive_references` discovery object in the RFC 9728 metadata, with four required members and an
  optional `max_references`. A malformed or missing object stops the host. (SC-02, SC-09, OQ-8)
- The resolve scope is named in the discovery object, not in `scopes_supported`. Mixed scopes get
  `invalid_scope`. (SC-03)
- The resolve endpoint is on the origin of the resource, also when configured. (SC-04, OQ-14)
- Resolver tokens and agent tokens are separate classes. (SC-05)
- Consent binds subject, client, resource, resolve scope and sink-profile set, resists framing and CSRF,
  and its end stops refresh and live tokens. (SC-06)
- Access-token lifetime of one hour or less (recommended), refresh rotation bound to the client, owner-only
  token cache, one renewal after 401. (SC-07)
- PKCE S256 required in the authorization server metadata, `state`, RFC 9207 `iss`, RFC 8414 issuer, no
  automatic choice of an authorization server. (SC-08)
- Exactly one listed authorization server is used. With none or several, only an operator-configured one
  that the list contains (if the list is not empty); else no resolution. (SC-08, new detail; the reference
  host stops with zero or several unless an operator configures one)
- New section 11.1 with the minimum recovery: refused refresh, lost cache, cache that others can read,
  cache that the host cannot parse, ended approval, lost rotated refresh token. OQ-18 keeps only recovery
  beyond this minimum. (SC-07, package profile rules T11 and T12, THREAT-MODEL.md TM-8)
- Loopback redirect URIs: exact match except the port, `127.0.0.1` always accepted, `form-action` permits
  the loopback origin. (SC-20, OQ-4)
- A server can refuse `[::1]` before the consent page. (SC-20, OQ-15, provisional)
- A resolver code only to a loopback redirect URI while `local-file-1` is the only sink profile. (profile
  rule A8)
- The resolve request carries `references`, `sink_type` and `destination`, never a principal. (SC-10)
- The server never returns `destination` in any answer. SC-10 said "in an error"; Concept 0.6 extends it to
  every answer. (SC-10)
- Condition 3 of each resolve request: the issuer authorizes the subject for every reference, as in
  Concept 0.5. The policy (owner only, or shared records) belongs to the issuer. (Concept 0.5 profile draft)
- A `max_references` value that is not an integer of 100 or more makes the host refuse the discovery
  object. (SC-09, new detail)
- IPv4-mapped addresses are judged by the embedded IPv4 address only; TLS verification also on a checked
  address; the fetch policy need not cover the MCP URL, and a host may apply it there. (SC-01, published round 9)
- The profile states that the authorization server and the resource share the approval state. (new)
- The destination is a label (recommended). (SC-10, OQ-6, provisional)
- Batch limit of at least 100, `413 too_many_references`, duplicates count once. (SC-09)
- A success answer has exactly the requested keys and `Cache-Control: no-store`. (profile rules R6 and
  section 6 of the package profile)
- Fixed error codes, `WWW-Authenticate` on 401, renewal only after 401. (SC-11)
- DPoP is optional. (OQ-5, provisional)
- The subject binding does not need JWT access tokens. (OQ-10, provisional)
- The resolver profile is no longer called "validated with one authorization server". The probe evidence
  moved to IMPLEMENTATION-EVIDENCE.md. (vendor-neutral text)

### `local-file-1`

- New self-contained profile file. (package file PROFILE-local-file-1.md)
- Split batches: the sink writes nothing until every request succeeded. (SC-09)
- The wire value of `sink_type` is `local_file`. (SC-10)
- The written file has no group or other permission bits. (profile rule L12)
- The file content may come from model output or from host configuration (provisional). The host never
  takes the destination from model output. (new, OQ-16)
- The sink report may name the destination, as in Concept 0.5; it holds no value, reference or credential.
  (Concept 0.5 profile draft)
- The sink writes a temporary file, replaces the destination atomically, and leaves no temporary file with
  plaintext after a detected failure. (profile rules L10 and L11)

### Non-normative files

- README.md: status line, "Versions" section, document map, implementations, known gaps.
- IMPLEMENTATION-EVIDENCE.md: MCPGate as the reference server, `prototype/demo/mcp_host.py` as the
  reference host, the evidence of CONFORMANCE-RESULTS.md and the known gaps (E11/P16 and others).
- OPEN-QUESTIONS.md: "Remaining design decisions" with OQ-1 to OQ-18.
- DESIGN-DECISIONS.md, STATUS.md, PRIOR-ART.md, COMMUNITY-DISCUSSION.md and OUTREACH-POST.md follow
  Concept 0.6.

## Concept 0.5

Concept 0.5 is the git tag `concept-0.5`. Its changes from 0.4 are in
[prototype/DESIGN-DELTA-0.4.md](prototype/DESIGN-DELTA-0.4.md).
