# Community discussion draft

## Sensitive References: referencable but not visible

MCP servers can expose customer records, business identifiers, health data, secrets, and other sensitive
values. An agent can need to preserve, route, format, or use those values without needing their plaintext.

Today, a server can return plaintext or redact it. Plaintext enters model context. Redaction can prevent a
requested artifact or action. We are exploring an optional MCP extension called Sensitive References.

```text
email = ⟦sref:email:01JCK7KF9X4Y3M4N6Q6YB2D8P0⟧
```

The host records that a negotiated, authenticated MCP server issued this token. The model can copy it through
its work. Possession of the token is not authorization. Later, a separately authorized non-model resolver
can materialize the value into an eligible protected sink, such as a local file. The ordinary model-facing
result remains reference-only.

This work does not standardize sensitive-data classification. It separates a small core from resolver and
host-integration profiles. It does not require a new `ContentBlock` type. It uses ordinary string fields and
does not rely on `_meta` as a secrecy boundary.

The included prototype demonstrates the canonical text form, host-held issuer provenance, fail-closed
handling for forged, wrong-issuer, ambiguous, unknown, revoked, and expired references, protected local-file
materialization, and all-or-nothing batch behavior. A Keycloak experiment validates a separate OAuth resolver
client as a viable resolver-profile candidate. It does not prove interoperability across MCP hosts or
authorization servers.

We have not found a first-class MCP mechanism that combines server-issued opaque references, host-trusted
issuer provenance, and out-of-model authorized materialization. We welcome prior art and corrections.

Questions for review:

1. Can MCP hosts retain authenticated provenance for opaque references across model turns?
2. What host integration point is appropriate for protected sinks?
3. Is a separate narrow OAuth resolver client a reasonable profile candidate?
4. Where should resolver endpoint discovery live?
5. Is arbitrary cross-server redemption necessary for v1, or should it remain deferred?
6. Does this fit an MCP extension, another extension category, or a future core primitive?

This is pre-SEP design work. It is not an MCP standard or an accepted SEP.
