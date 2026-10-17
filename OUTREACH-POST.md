# Sensitive References for MCP: initial discussion post

We are exploring Sensitive References, a pre-SEP design for values that an MCP server holds but a model does
not need to read.

Today, an agent can need a customer email, an API key, or another sensitive value in a later action. Common
patterns return plaintext, redact it, or transform context. We are testing a fourth option:

```text
email = ⟦sref:email:01JCK7KF9X4Y3M4N6Q6YB2D8P0⟧
```

The model can carry and route the opaque reference. A separately authorized non-model resolver can later
materialize the plaintext into an eligible protected sink. Reference possession alone does not authorize
resolution.

The proposal, prototype, and evidence are here:

https://github.com/Sprinterli/mcp-sensitive-references

We would value feedback on three questions:

1. Is host-held `(token, issuer)` provenance realistic for MCP hosts?
2. Which host integration point is suitable for protected sinks?
3. Is a separate OAuth resolver client a sensible profile approach?

This is design exploration, not a standard or an accepted SEP.
