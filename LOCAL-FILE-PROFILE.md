# Sink profile `local-file-1`

**Status: Concept 0.6 draft, normative profile.** The conventions and terms of
[SPEC-DRAFT.md](SPEC-DRAFT.md#1-conventions) apply. This profile builds on the core documents. It does not
need any other document.

The sink writes plaintext values into one local file. The model-facing result keeps the references. The
model does not see the file content. The evidence for each rule is in
[protocol-package/PROFILE-local-file-1.md](protocol-package/PROFILE-local-file-1.md).

## 1. Preconditions

1. The host MUST resolve only if the negotiated intersection holds `local-file-1` and a resolver profile
   that the host supports. Version 1 defines one resolver profile, `oauth-resolver-1`.
2. If the resolver profile defines a discovery object (`oauth-resolver-1` does), the object MUST list
   `local-file-1`, and the resolver profile's rules for a missing object apply. Else the host MUST NOT
   resolve. An operator-configured endpoint does not change this rule.
3. The host MUST choose the destination under its own policy. The host MUST NOT take the destination from
   model output.

4. The content of the file MAY come from model output or from host configuration. In both cases only
   observed references resolve (section 2).

**Provisional (OQ-16).** Rule 4 permits both sources of content. A later version can restrict them. No
implementation tested content from model output.

## 2. Which references the sink resolves

1. The sink MUST resolve a reference only if the host observed it in a negotiated, authenticated result,
   and only if it has exactly one trusted issuer (HOST-INTEGRATION.md, section 3).
2. The sink MUST send a reference only to the resolve endpoint of its own issuer.
3. The sink MUST match references by exact code points. It MUST NOT normalize, case-fold, trim or rebuild
   a reference.
4. The sink SHOULD remove duplicate references before it sends a request.

Reference-shaped text without a trusted observation stays in the file as ordinary text. The host MUST NOT
send it to a resolver.

## 3. Wire values

The sink MUST send `sink_type` with the value `local_file` to the resolve endpoint. The sink MUST send a
non-empty `destination` of 1 to 4096 characters without control characters.

**Provisional (OQ-6).** The sink SHOULD send a label as `destination`, for example the file name, not an
absolute path.

## 4. Materialization

1. The sink MUST resolve every reference of the content before it changes the destination.
2. If the host splits the references into more than one resolve request, each request MUST hold at most the
   effective limit of the server. Every request MUST succeed before the sink writes.
3. The sink MUST accept an answer only if it holds exactly the references of the request, each with a
   string value.
4. If one reference or one request fails, the sink MUST leave the destination unchanged. If the file
   existed, its content stays. The sink MUST discard every resolved value of the write.
5. The sink SHOULD write a temporary file in the destination directory, flush it to storage, and then
   replace the destination atomically. The sink MUST NOT leave a temporary file with plaintext after a
   failure that it detects.
6. On a POSIX system, the written file MUST NOT have permission bits for group or others. On another
   system, the sink MUST use equivalent owner-only access.

## 5. What leaves the sink

1. The model-facing result MUST keep the references. It MUST NOT hold a resolved value.
2. The report of the sink MUST NOT contain protected data items 1 to 4 and 6 (SPEC-DRAFT.md, section 8).
   It MAY hold counts, a status, error codes and the destination.
3. If a later action echoes a value that this write resolved, the host MAY put the reference back in place
   of the value.

## 6. Not in this profile

- Command interpolation and document sinks.
- A general filesystem policy.
- Protection after the file exists. A process with the same operating-system privileges can read the file
  (SECURITY-MODEL.md, section 6).
- A destination policy at the server. The server uses `destination` for audit only.

## 7. Evidence

**Note.** The reference host implements this profile with one difference: it sends the absolute path as
`destination`, not a label. It takes the content from its own configuration, not from the model. See
[IMPLEMENTATION-EVIDENCE.md](IMPLEMENTATION-EVIDENCE.md).
