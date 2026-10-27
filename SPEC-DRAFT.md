# Sensitive References: Concept 0.6 draft

**Status: Concept 0.6 draft. Not an MCP standard and not an accepted SEP.**

This file defines the core semantics of an optional MCP extension. Four documents form the normative core:

| Document | Content |
|---|---|
| SPEC-DRAFT.md (this file) | Terms, roles, negotiation, issuer rules, host rules, resolution rules, protected data |
| [WIRE-REPRESENTATION.md](WIRE-REPRESENTATION.md) | The canonical form of a reference, the settings object, the refusal result |
| [HOST-INTEGRATION.md](HOST-INTEGRATION.md) | The issuer identity, the provenance store, the observation point and the sink input point |
| [SECURITY-MODEL.md](SECURITY-MODEL.md) | Trust boundaries, required controls, threats and limits |

Two profiles build on the core. Each profile is complete in its own file:

- [RESOLVER-PROFILE.md](RESOLVER-PROFILE.md): the resolver profile `oauth-resolver-1`.
- [LOCAL-FILE-PROFILE.md](LOCAL-FILE-PROFILE.md): the sink profile `local-file-1`.

Evidence, history and rationale are not part of the normative text. They are in
[IMPLEMENTATION-EVIDENCE.md](IMPLEMENTATION-EVIDENCE.md) and in [protocol-package/](protocol-package/).

## 1. Conventions

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD", "SHOULD NOT", "RECOMMENDED",
"NOT RECOMMENDED", "MAY", and "OPTIONAL" in the normative documents are to be interpreted as described in
BCP 14 (RFC 2119, RFC 8174) when, and only when, they appear in all capitals, as shown here.

A paragraph that starts with **Provisional (OQ-n)** states a provisional v1 design decision. The
implementations follow it. The community did not confirm it. [OPEN-QUESTIONS.md](OPEN-QUESTIONS.md) lists
the options for each such decision.

A paragraph that starts with **Note** is not normative.

## 2. Terms

- **Sensitive value.** A plaintext value that a server classifies as sensitive. Classification is out of
  scope.
- **Sensitive Reference (reference).** An opaque string that a server issues in place of a sensitive
  value. Its wire form is the canonical form of [WIRE-REPRESENTATION.md](WIRE-REPRESENTATION.md).
- **Reference-shaped text.** Text that matches the canonical form. Such text has no authority by itself.
- **Issuer.** The MCP server that issued a reference. It holds the sensitive value.
- **Issuer identity.** The string that names an issuer in host state ([HOST-INTEGRATION.md](HOST-INTEGRATION.md#2-issuer-identity)).
- **Value generation.** One binding of a reference identifier to one sensitive value.
- **Supporting host.** A host that meets every rule of [HOST-INTEGRATION.md](HOST-INTEGRATION.md).
- **Observation.** A record of a reference that a supporting host saw in an authenticated MCP result. It
  holds `(reference, issuer identity, first_observed, optional metadata)`.
- **Trusted provenance.** The set of observations that a supporting host holds outside model-visible text.
- **Resolver.** A non-model component that asks the issuer for the sensitive value of a reference.
- **Resolution.** The release of a sensitive value by the issuer to a resolver.
- **Sink.** A destination that receives sensitive values outside model-visible content, for example a
  local file.
- **Resolver profile.** A document that defines how a resolver discovers, authenticates and calls the
  issuer.
- **Sink profile.** A document that defines one class of sink and its output boundary.
- **Agent token.** The credential that the MCP client uses for MCP requests.
- **Resolver token.** The credential that a resolver uses for resolution, as a resolver profile defines it.
- **Model-visible content.** Any content that the host can give to a model: tool results, error texts,
  reports and logs that the model can read.

This document uses "reference" only for a Sensitive Reference. It uses "access token", "refresh token",
"agent token" and "resolver token" only for credentials.

## 3. Overview

**Note.** The flow has five steps:

1. A negotiated supporting MCP server puts a reference in place of a sensitive value in a tool result.
2. The host records an observation outside model text.
3. The model can copy, sort, format and route the reference. Reference-shaped text gains no provenance.
4. A protected sink asks a separately authorized resolver to resolve the observed references.
5. The sink sends plaintext only to the eligible destination. The model-facing result keeps the references.

The short goal is: **referencable but not visible**.

## 4. Negotiation

A client and a server enable this extension only through the `extensions` map of the MCP client
capabilities and server capabilities. The settings object is in
[WIRE-REPRESENTATION.md](WIRE-REPRESENTATION.md#3-extension-settings).

This extension applies only to an MCP protocol version that has an `extensions` map in the client
capabilities and the server capabilities. A server MUST NOT emit a reference to a client on another
protocol version. A server MUST NOT emit a reference in a session in which the client did not declare the
extension with a version that the server supports.

Reference-shaped text never negotiates support.

The MCP project assigned no extension identifier. Until it does, implementations SHOULD accept the
identifier from configuration. A SEP MUST name one identifier. Examples use
`org.example/sensitive-references`.

**Provisional (OQ-9).** Implementations ask the MCP project for an identifier before a SEP. A server MAY
advertise a provisional identifier and the official identifier together for one release.

## 5. Issuer rules

### 5.1 Issuance

An issuer MAY put a reference in place of a sensitive string value. An issuer MUST create the identifier
of a reference at random. An issuer MUST NOT derive the identifier from the plaintext. Equal plaintext
values MUST NOT give a predictable relation between their identifiers.

An issuer MUST NOT bind an identifier to another value generation. An issuer MUST NOT silently reuse an
identifier after revocation or expiry.

### 5.2 Possession is not authorization

A reference is not a bearer credential. Possession of a reference MUST NOT authorize its resolution. An
issuer MUST evaluate resolution authorization separately from reference possession. The ordinary agent
token MUST NOT automatically grant plaintext resolution rights.

### 5.3 Lifetime

An issuer MUST state the lifetime rule of its references in its documentation. After a reference expires,
a resolution of it MUST fail. While the issuer keeps the record of an expired reference, the reason MUST
be `expired`. After the issuer discards that record, the reason MAY be `unknown`.

**Provisional (OQ-11).** The core sets no fixed minimum lifetime. Each issuer documents its own lifetime.

### 5.4 Integrity of the issuer registry

An issuer MUST protect each stored reference binding with a message authentication code or an
authenticated-encryption tag. The issuer MUST compute it over the record and its principal, with a key
that it does not store with the records. An issuer MUST verify the record before each resolution. If the
verification fails, the issuer MUST treat the reference as unknown, MUST NOT resolve it, and MUST NOT
return any part of the record. A record copied from another principal therefore does not resolve.

A revocation MUST survive a replay of an older record of the same principal.

### 5.5 Failure

An unknown, revoked, expired, stale, ambiguous or unauthorized reference MUST fail. The failure MUST NOT
return plaintext. The failure MUST NOT return protected data (section 8).

### 5.6 Server text

A negotiated server MUST NOT emit text in a tool result that contains the marker `⟦sref:` at any
position, except inside a reference that the server issued. A server MUST describe references in words in
its own notices, examples and instructions.

### 5.7 A refused reference inside a tool call

A tool call can carry a reference as an argument. If a negotiated server refuses the call because a
reference does not resolve, the server MUST return a tool result with `isError: true`. The result MUST NOT
contain protected data (section 8). The result SHOULD have `structuredContent`. If it has it, the object
MUST follow [WIRE-REPRESENTATION.md, section 5](WIRE-REPRESENTATION.md#5-refusal-result).

**Note.** This rule tells the host that the server sent nothing upstream. It does not define when a
server may resolve a reference into its own outbound calls. That question is open (section 6.3).

## 6. Host and resolution rules

### 6.1 Trusted provenance

A host gains trusted provenance for a reference only if all these conditions are true:

1. The host and the server negotiated this extension (section 4).
2. The host received the reference in an authenticated MCP result from that server.
3. The reference matches the canonical form exactly.
4. The host records the observation outside model text.

Reference-shaped text from a model, a prompt, a file, a repository, a web page or an unsupported server is
ordinary text. It gains provenance only if it exactly matches a prior trusted observation. A reference
cannot select its issuer.

If a reference has no trusted issuer, or more than one trusted issuer, a host MUST fail closed. If a host
loses trusted provenance, or cannot show that a stored observation is intact, it MUST fail closed or get a
new trusted observation. A host MUST NOT infer provenance from the content of a reference.

[HOST-INTEGRATION.md](HOST-INTEGRATION.md) gives the complete host rules.

### 6.2 Hosts that cannot verify negotiation

A host that cannot verify the negotiated capabilities of a session and the issuer identity of a result is
not a supporting host. Such a host MUST NOT declare the extension. A host MUST NOT resolve a reference that
it did not observe in a negotiated, authenticated result. This applies also when the reference occurs in a
file that the host reads.

### 6.3 Resolution

Resolution MUST use a resolver profile that the host and the server negotiated, or that an operator
configured explicitly. The resolver MUST authenticate as a stable principal. The resolver and the issuer
MUST NOT infer that principal from display text, from reference text or from model-provided fields.

The issuer MUST authorize each resolution request. The decision MUST NOT depend on possession of the
reference. The issuer MUST refuse the whole request if one reference fails.

Resolved plaintext MUST NOT return through an ordinary model-visible MCP result. A sink profile defines the
eligible destination and its output boundary.

**Open (OQ-3).** An issuer can resolve its own references into its own outbound calls, under the agent
token. This version does not define such an "issuer-side sink". It does not decide whether the
agent-token rule of section 5.2 forbids it. [OPEN-QUESTIONS.md](OPEN-QUESTIONS.md#oq-3-the-issuer-side-sink-and-the-agent-token-rule-sc-18)
lists the options and the proposed checks.

### 6.4 Batches

A sink profile MUST state that the sink resolves every reference of one write before it changes the
destination. If one reference fails, the sink MUST NOT write partial output.

## 7. Profiles

A profile identifier is a string of 1 to 64 characters from `[a-z0-9-]` that starts with a letter or a
digit. Version 1 defines two profiles:

| Identifier | Kind | Document |
|---|---|---|
| `oauth-resolver-1` | resolver profile | [RESOLVER-PROFILE.md](RESOLVER-PROFILE.md) |
| `local-file-1` | sink profile | [LOCAL-FILE-PROFILE.md](LOCAL-FILE-PROFILE.md) |

A host MUST NOT resolve unless the negotiated intersection holds a resolver profile and a sink profile
that the host supports. A resolver profile MUST define discovery, authentication, authorization, subject
binding, endpoint behaviour, lifecycle errors, limits and recovery. A sink profile MUST define the
destination, the content, the batch rule and the output boundary.

No registry exists for profile identifiers.

## 8. Protected data

The issuer rules, the host rules and the profiles use one definition. Protected data is each of these
representations:

1. the complete plaintext value of a reference;
2. a contiguous part of 8 or more characters of that value;
3. a complete reference in canonical form;
4. the random identifier of a reference, or a contiguous part of 8 or more characters of it;
5. the destination of a sink write;
6. a credential: an access token, a refresh token, an authorization code, a PKCE verifier or a client
   secret.

An answer that must not contain protected data MUST NOT contain an item in any of these encodings: the
string itself (UTF-8), a JSON string escape, percent-encoding (RFC 3986), base64 or base64url (RFC 4648,
with or without padding), and hexadecimal in lower or upper case. For items 2 and 4 (a part), only the
string itself and the JSON string escape apply. The rule applies to member names and to strings, also as a
part of a longer string. The comparison is exact. It ignores case only for hexadecimal.

These members are not protected data, also if their text matches an item above: an `error` code, the names
and the counts of `reasons`, an `error_code`, an HTTP status, and the `client_id` of a public client.

**Note.** A server should also not put a hash, a MAC or another value computed from protected data into an
answer. This is security guidance, not a conformance rule, because a validator can find such a value only
if it knows the function.

## 9. Non-goals

This version does not define:

- sensitive-data classification, DLP or NER;
- a universal plaintext secret or a universal local execution sandbox;
- server-to-server redemption or cross-server delegation;
- generic output redaction or generic filesystem policy;
- a new MCP `ContentBlock` type;
- `_meta` as a secrecy boundary;
- an issuer-side sink (section 6.3);
- an issuer identity for a transport other than HTTP ([HOST-INTEGRATION.md](HOST-INTEGRATION.md#2-issuer-identity)).
