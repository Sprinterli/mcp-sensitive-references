# Changelog

## Concept 0.7 (draft)

Concept 0.7 describes what runs in the implementations and has proven itself there. Each line names its
source: an SC entry of [protocol-package/SPEC-CHANGES.md](protocol-package/SPEC-CHANGES.md), an OQ item of
[OPEN-QUESTIONS.md](OPEN-QUESTIONS.md), or a profile file of the package. The evidence is revisions R3, R4 and R5 of
the reference server, releases 0.9.0, 0.9.1 and 0.9.4 of the second host, and run E13.

### Structure

- Two new normative sink profiles: PROCESS-PROFILE.md (`process-1`) and DISPLAY-PROFILE.md (`display-1`).
  The package gets an evidence file for each. (SC-22, SC-23)
- A third implementation, the second host, is in IMPLEMENTATION-EVIDENCE.md. (new)
- The prototype implements Concept 0.7: the reference host reads `sinks` and implements `process-1` and
  `display-1` at demo level, and a new prototype issuer implements the server rules. Tested offline only.
  (prototype/README.md, section "Concept 0.7")

### Core

- New term "sink scope". A sink profile also defines its sink scope, if any, and its limit. (SC-21)
- References are per principal (account): an issuer resolves a reference only for its owner, and a
  reference of another principal fails with `unknown`, also for two accounts of one person. Concept 0.6 let
  the issuer authorize other principals, for example for a shared record. (SC-24)
- SECURITY-MODEL.md: TM-1 names the consent at every authorization request and the revocation per device;
  TM-4 names the sink scopes; new TM-14 (process) and TM-15 (display). (SC-06, SC-21 to SC-23, SC-26)

### `oauth-resolver-1`

- The discovery object gets `sinks` (the `sink_type` and the whole scope set of each sink profile), and
  `process_scope` and `display_scope` for the two profiles that need them. The field name
  `sensitive_references` is fixed; OQ-8 is decided. (SC-21, OQ-8)
- A sink profile can require a sink scope. The host asks for the resolve scope and the sink scopes that it
  can honour, in one request. The authorization server accepts only those combinations (plus `openid`);
  every other scope next to the resolve scope, and a sink scope alone, get `invalid_scope`. This replaces
  the rule "no scope other than the resolve scope and `openid`" of Concept 0.6. (SC-21, SC-03)
- A missing sink scope gives `403 insufficient_scope` before any lookup, with no value and no audit
  event. The header and the body name the whole scope set and carry an `error_description`. (SC-21)
- A refresh keeps the granted scope set. A new sink needs a new authorization. (SC-21)
- The consent page comes at every authorization request; a stored approval no longer gives a code without
  the page. The page names the account with an action to use another account, the client, the loopback
  host and port, the time of the request and one line per sink scope. The stored approval binds subject,
  client, resource and the granted scope set. (SC-06)
- Revocation per device (principal and client), by the person and by an administrator. A credential from
  before the revocation stays dead after a new approval. (SC-26)
- An optional `account_hint` in the token answer and in the refresh answer. For an email address it holds
  at most min(3, floor(n/2)) characters of a local part of n characters (MUST). (SC-24)
- The loopback rule for authorization codes covers every sink profile that puts the value on the computer
  of the host. (SC-22, SC-23)
- `sink_type` has three values: `local_file`, `process`, `display`. A value that is not exactly one of
  them gets `403 ineligible_sink`. (SC-22, SC-23)
- Audit: a server MUST write the audit event before it sends a value, else `503 audit_unavailable`. Concept
  0.6 said SHOULD. Every released value counts in the quota. (SC-25)
- The error table gets the new meaning of `insufficient_scope` and the code `503 audit_unavailable`.
  (SC-21, SC-25)

### `local-file-1`

- The profile needs no sink scope. (SC-21)

### `process-1` (new)

- `sink_type` `process`; destination the program name, never the command line; the server audit keeps
  the last path part without white space, else `other`; the host masks the command output also on the
  failure path and resolves only when the command reads the value; a process scope. The identifier is
  `process-1`. (SC-22, OQ-21)
- The value goes through a channel that only the command reads (MUST): a named channel is owner-only, in a
  directory that only the owner can open, and gives the value once, to one reader. The limit names a
  process of the same person that opens the channel first. (SC-22, TM-14)
- The destination is advisory: the limit names wrappers, pipelines and the open word splitting. (SC-22)

### `display-1` (new)

- `sink_type` `display`, destination `screen`, one reference per request, only on a click of the person;
  never to the model, a transcript or an export; a paste is masked back; copy only on a second click; one
  audit event per reveal, counted in the quota; a display scope. (SC-23)
- No released value in a link target, a URL or markup, and no text that the model wrote as the label of
  the action that resolves or copies. The limit names a surface that the host cannot verify as local and
  the paste mask that knows only whole values in known encodings. (SC-23, TM-15)

### Non-normative files

- README.md: "Changes in this revision", the document map, three implementations, known gaps.
- IMPLEMENTATION-EVIDENCE.md: what R3 does, the second host and its limits, run E13.
- Revision R4 of the reference server (version 2.0.3830): the process profile has the identifier
  `process-1`, and the stored approval binds resource and scope set. The live discovery object, the
  profile rows and the threat model cite its tests.
- Revision R5 of the reference server (version 2.0.3837): a missing resolve scope names the whole scope
  set of the sink (R11), and the consent page has a new layout and new wording, with a test for the time
  of the request (C5, TM-1).
- Release 0.9.4 of the second host: it accepts `process-1` and reads `sinks`, and the screen labels a
  reference with the display of the server (DS21, now met). The second host evidence reads the tag
  `v0.9.4`. DS4, PR2/DS2 and the use of `account_hint` stay deviations.
- OPEN-QUESTIONS.md: OQ-8 decided; OQ-16 names the second host; new OQ-19 (safe metadata of a reference),
  OQ-20 (a "tokenize" profile) and OQ-21 (the identifier of the process profile, decided: `process-1`).
- protocol-package/: SC-21 to SC-26, amendments of SC-03 and SC-06, the R3 evidence rows, TM-14 and TM-15,
  run E13, new guide items.
- STATUS.md, DESIGN-DECISIONS.md, COMMUNITY-DISCUSSION.md and OUTREACH-POST.md follow Concept 0.7.

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
  grant". For the resolve endpoint, Concept 0.6 makes this stricter: an agent token never authorizes a
  resolve request. For issuer-side use, Concept 0.6 does not decide whether the 0.5 clause applies; that
  stays open as OQ-3, and the floor of section 6.4 applies in addition. (SC-05, OQ-3)
- An issuer reports a reference that the principal is not authorized for with the reason `unknown`.
  This holds also when that reference is revoked or expired. The `expired` reason of section 5.3 applies only
  to a reference that the principal is authorized for. Concept 0.5 had no reason for this case. (new)
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
- IMPLEMENTATION-EVIDENCE.md: the reference server, `prototype/demo/mcp_host.py` as the
  reference host, the evidence of CONFORMANCE-RESULTS.md and the known gaps. New run E12 (2026-10-27):
  after the server fix of P16, the host ran without a deviation option, with consent, cache, refresh and
  materialization. One operator run of each step.
- OPEN-QUESTIONS.md: "Remaining design decisions" with OQ-1 to OQ-18.
- DESIGN-DECISIONS.md, STATUS.md, PRIOR-ART.md, COMMUNITY-DISCUSSION.md and OUTREACH-POST.md follow
  Concept 0.6.

## Concept 0.5

Concept 0.5 is the git tag `concept-0.5`. Its changes from 0.4 are in
[prototype/DESIGN-DELTA-0.4.md](prototype/DESIGN-DELTA-0.4.md).
