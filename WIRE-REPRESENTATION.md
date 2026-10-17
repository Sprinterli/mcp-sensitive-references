# Wire representation

Concept 0.5 prefers one canonical opaque text token in ordinary MCP text and string-valued
`structuredContent` fields:

```text
⟦sref:email:01JCK7KF9X4Y3M4N6Q6YB2D8P0⟧
```

The token contains a fixed marker, an advisory kind, and an opaque identifier. It must not contain
plaintext, an authoritative resolver URL, or a subject identifier. The kind is advisory.

Text preserves existing string schemas and survives text, JSON, CSV, document, and tool-argument flows.
Version 1 does not require a new MCP `ContentBlock` type. It does not rely on `_meta` as a secrecy boundary.

The host derives the issuer from authenticated transport context. It stores the issuer outside model-visible
text. A token-looking string has no authority until a supporting host observes it in a negotiated,
authenticated MCP result. A model can copy a known token, but cannot manufacture its provenance.

If the same token text has more than one trusted issuer, the host must mark it ambiguous and must not
resolve it. A host that loses provenance after restart must fail closed or receive a new trusted observation.

Masked display text can accompany a token, but must never determine identity, issuer, or authorization.
