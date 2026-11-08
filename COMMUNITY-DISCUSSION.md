# Community discussion draft

## Sensitive References: referencable but not visible

MCP servers can expose customer records, business identifiers, health data, secrets and other sensitive
values. An agent can need to keep, route, format or use those values without the need to read them.

Today, common patterns return plaintext, redact the value, or transform context before the model sees it.
Plaintext enters model context, or the redaction prevents a requested file or action. We describe an
optional MCP extension called Sensitive References.

```text
email = ⟦sref:email:01JCK7KF9X4Y3M4N6Q6YB2D8P0⟧
```

The host records that a negotiated, authenticated MCP server issued this reference. The model can copy it
through its work. Possession of the reference is not authorization. Later, a separately authorized
non-model resolver can put the value into an eligible protected sink, such as a local file. The ordinary
model-facing result keeps the reference.

Concept 0.7 is one normative text: a small core (semantics, wire representation, host integration,
security model) and four profiles. The resolver profile `oauth-resolver-1` uses a separate OAuth client
with a narrow resolve scope, RFC 9728 metadata and a consent page at every authorization request. Three
sink profiles put a value into one local file (`local-file-1`), into a command that the host runs
(`process-1`), or onto the screen of the person after a click (`display-1`). The process and the display
sink each need their own scope, which a person can leave out. The extension does not need a new
`ContentBlock` type. It uses ordinary string fields and does not use `_meta` as a secrecy boundary.

Three implementations exist: a reference server (source not public), an independent reference host in the
repository (`local-file-1`, and `process-1` and `display-1` at demo level), and a coding-agent plugin that
resolves into files, commands and the screen but declares no extension. Several decisions are provisional and
need review.

We did not find a first-class MCP mechanism that combines server-issued opaque references, host-trusted
issuer provenance and out-of-model authorized resolution. We welcome prior art and corrections.

Questions for review:

1. Can MCP hosts keep authenticated provenance for opaque references across model turns and restarts?
2. Is a separate narrow OAuth resolver client a reasonable profile?
3. Should the discovery object live in RFC 9728 metadata, and how should the conflict with the root
   fallback of the MCP authorization specification be resolved?
4. May an issuer resolve its own references into its own outbound calls under the agent token, or does
   that need a second grant?
5. Is cross-server redemption necessary for version 1, or should it stay deferred?
6. Does this fit an MCP extension, another extension category, or a future core primitive?

This is Concept 0.7 draft work. It is not an MCP standard and not an accepted SEP.
