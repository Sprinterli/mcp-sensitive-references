# Sensitive References: Concept 0.5 draft

## Scope

This draft defines core semantics for a possible optional MCP extension. A profile defines resolver
authorization and eligible sinks. Classification of sensitive data remains outside this draft.

## Reference semantics

An issuer may replace a sensitive plaintext value with a Sensitive Reference. A reference identifies a
server-held value generation. It is not a bearer credential. The issuer must evaluate resolution
authorization separately from reference possession.

An issuer must not silently reuse an identifier for another value generation. Unknown, revoked, expired,
stale, ambiguous, or unauthorized references must fail without returning unrelated plaintext.

## Host semantics

A supporting host gains trusted provenance only when all conditions apply:

1. The server and host negotiated Sensitive References support.
2. The host received the token in an authenticated MCP result from that server.
3. The token matches the canonical grammar.
4. The host records `(token, authenticated issuer, first_observed, optional metadata)` outside model text.

Token-shaped text from a model, prompt, file, repository, web page, or unsupported server is ordinary
text unless it exactly matches a prior trusted observation. A token cannot select its issuer.

If a token maps to no issuer, or more than one issuer, a host must fail closed. If a host loses its
trusted provenance store, it must fail closed or obtain a new trusted observation. It must not infer
provenance from token content.

## Resolution and sinks

Resolution must use a negotiated or explicitly configured resolver profile. The resolver must authenticate
as a stable principal. The resolver and issuer must not infer that principal from display text or
model-provided fields.

Resolution plaintext must not return through an ordinary model-visible MCP result. A sink profile defines
the eligible destination and its output boundary. A `local-file-1` profile must resolve all references
before it replaces its destination. If one batch member fails, it must not partially materialize output.

## Resolver profile boundary

A resolver profile defines discovery, authentication, authorization, subject binding, endpoint behavior,
lifecycle errors, audit, limits, and recovery. The ordinary MCP agent token must not automatically grant
plaintext resolution rights.

A separate OAuth resolver client against the same protected resource, with a narrow resolve privilege
and Authorization Code plus PKCE, is validated as a viable resolver-profile candidate. It remains
provisional. The core does not require the MCP resource server to observe the ordinary agent token flow.

## Non-goals

This draft does not define a universal plaintext secret, server-to-server redemption, cross-server
delegation, generic output redaction, or a universal local execution sandbox.
