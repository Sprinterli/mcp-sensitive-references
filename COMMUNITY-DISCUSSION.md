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

Concept 0.6 is one normative text: a small core (semantics, wire representation, host integration,
security model) and two profiles. The resolver profile `oauth-resolver-1` uses a separate OAuth client with
a narrow resolve scope, RFC 9728 metadata and explicit consent. The sink profile `local-file-1` writes one
local file, all or nothing. The extension does not need a new `ContentBlock` type. It uses ordinary string
fields and does not use `_meta` as a secrecy boundary.

Two implementations exist: a reference server (MCPGate, source not public) and an independent reference
host in the repository. They do not yet interoperate in a conformant run: the server challenge names the
metadata of its base URL, and the host, without its non-conformant option `--resource`, stops there (E11). Several decisions are provisional and
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

This is Concept 0.6 draft work. It is not an MCP standard and not an accepted SEP.
