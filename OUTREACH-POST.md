# Sensitive References for MCP: discussion post

We describe Sensitive References, a design for values that an MCP server holds but a model does not need
to read.

Today, an agent can need a customer email, an API key or another sensitive value in a later action. Common
patterns return plaintext, redact it, or transform context. We test a fourth option:

```text
email = ⟦sref:email:01JCK7KF9X4Y3M4N6Q6YB2D8P0⟧
```

The model can carry and route the opaque reference. A separately authorized non-model resolver can later
put the plaintext into an eligible protected sink. Possession of a reference alone does not authorize
resolution.

Concept 0.6 is one normative text with a core and two profiles. The text, the reference host and the
evidence are here:

https://github.com/Sprinterli/mcp-sensitive-references

We would value feedback on three questions:

1. Is host-held `(reference, issuer)` provenance realistic for MCP hosts?
2. Is a separate OAuth resolver client with its own consent a sensible profile?
3. Which of the remaining design decisions in OPEN-QUESTIONS.md should change?

This is Concept 0.6 draft work, not a standard and not an accepted SEP.
