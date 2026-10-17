# Design notes

## What worked

The canonical text token preserves ordinary string fields in `structuredContent` and text content. A host can discover those tokens recursively in an MCP-shaped result, retain issuer provenance outside model-visible text, and later recognize copied tokens in model output. The protected file sink resolves values before an atomic replace and returns only the original reference-bearing content as its model-facing result.

The prototype uses a random opaque ID per issuance. It never remaps an ID, so old, unknown, expired, or revoked references cannot silently select another value. The same plaintext issued twice receives unrelated references.

The draft token vectors are executable tests: short IDs, trailing text, and confusable fullwidth brackets are rejected as canonical identities.

## What was awkward

The host needs an interception point for both authenticated MCP results and every eligible local write. The protocol token itself cannot provide that. Multi-issuer files also require the host to group tokens by trusted issuer before resolution. Ambiguity is rare with random IDs but must be an explicit error path.

## Assumptions

- The host has already authenticated the MCP server and knows whether the extension was negotiated.
- The demo's `ResolverAuthorization` is an in-memory stand-in for an OAuth Resolver Profile. It is deliberately separate from token parsing and the ordinary MCP client token.
- The local file sink is eligible by its client-integration policy. The prototype does not attempt generic path, command, or output-redaction policy.
- Atomicity here means the resolver returns no partial batch and the destination is replaced only after all resolution succeeds. It cannot roll back an already completed filesystem replacement after an OS-level crash.

## MCP compatibility

The design aligns with the current extensions framework: extensions use reverse-DNS identifiers and explicit capability negotiation. `CallToolResult` supports `content` plus `structuredContent`; string-valued `structuredContent` therefore carries the token without schema-shape changes. Current content blocks are not a generic custom union, so a new content-block type is unnecessary for this experiment. `_meta` was not used for secrecy.

MCP OAuth treats the MCP server as a protected resource/resource server and supports a separate authorization server through Protected Resource Metadata. That supports the design's separate resolver OAuth client, but the endpoint-discovery location and resolve-specific scope name remain profile work.

## Security observations

- A parsed token is only text until the host records a trusted negotiated observation.
- Issuer is selected exclusively from host state. A token never carries a resolver URL or subject.
- An unobserved token, an ambiguous token, an unknown token, a revoked token, a wrong issuer, and a missing resolver grant all fail before any file change.
- The resolver validates the complete batch before returning a mapping. The sink only writes after all issuer batches resolve.
- Resolver discovery is host-bound: the HTTP adapter chooses an endpoint from issuer configuration, never from a token field or model content.
- The prototype does not solve plaintext echoes from arbitrary downstream programs. A client integration profile needs output redaction and context-safe command substitution rules.
- The prototype now includes a narrow output guard for values resolved in the current operation. It does not inspect arbitrary output or claim generic DLP coverage.

## Evidence and contradictions

No material contradiction was found. The handoff retains an earlier statement that a semantic object is the protocol concept; its explicit 0.4 update and `WIRE-REPRESENTATION.md` make canonical text the preferred v1 wire form. This prototype follows the newer, explicitly preferred v1 decision while leaving a richer semantic object for a later revision.

The inspected maisecrets hooks demonstrate practical pre-action and post-result integration points and a strict model-output boundary. The inspected AI Gateway code demonstrates existing PII-sanitization and OAuth/resource-server components. Neither contained a current Client-Vault resolver endpoint, minted-reference registry, or a behavior that conflicts with this design.

## Recommended next revision

1. Publish exact token grammar and test vectors, including Unicode normalization behavior and duplicate-token handling.
2. Specify the host extension capability fields and the exact authenticated-result hook that grants provenance.
3. Define an OAuth Resolver Profile with discovery placement, a resource-bound resolve scope, audience validation, and resolver-token storage requirements. The PoC now has PKCE request and state-checked code-exchange construction, OIDC discovery against the local Keycloak realm, a non-model protected resolve endpoint, and an isolated Keycloak-issued JWT/JWKS/issuer-bound HTTP end-to-end resolve probe. `keycloak_pkce_probe.py` exercises the browser-equivalent Authorization Code + PKCE route with temporary realm objects; production-grade resolver-token storage remains a profile/client concern.

The local Keycloak 26 container marks login-session cookies `Secure` despite serving HTTP. The headless PKCE probe relaxes that flag only in its in-memory test client after the authorization response. It validates the authorization-code exchange and the subject-bound protected resolve request, but is not a substitute for HTTPS browser testing.

The test realm also emits lightweight access tokens without `sub` for a minimal public client. The PoC correctly rejects that token shape. Its temporary PKCE client adds an explicit user-model `sub` mapper solely to verify the end-to-end subject-binding path. An official Resolver Profile should require a stable subject claim and reject subjectless tokens, while leaving issuer-specific mapper configuration to deployment guidance.
4. Define a small protected-sink profile for local files, including failure reporting, safe path policy, and output echo/redaction expectations.
5. Add an official SDK reference implementation before an Extensions Track SEP, after community discussion.

## Proven by this prototype

The following claims are limited to the executable Python prototype, its focused unit tests, its local
FastMCP probe, and its local Keycloak probes. They are not claims about all MCP hosts or deployments.

- A canonical text reference can occupy an ordinary JSON string field and a FastMCP structured-output
  schema without the protected email or phone appearing in the model-facing result.
- A host-held `(token, issuer)` observation can prevent a model-invented or otherwise unobserved token
  from resolving. The token itself does not select an issuer.
- Unknown, wrong-issuer, revoked, expired, and multi-issuer-ambiguous references can fail closed.
- An immutable opaque ID prevents this prototype from silently remapping an old reference to another
  value; issuing the same plaintext twice produces unrelated IDs.
- The resolver abstraction can require authorization state separate from reference possession.
- Batch resolution can be all-or-nothing, and the protected file sink does not replace its destination
  until all batches have returned complete mappings.
- A local file sink can receive plaintext while its model-facing result retains the original
  reference-bearing content.
- A separate OAuth resolver client is technically viable as a resolver-profile candidate. The local
  Keycloak probes exercised OIDC discovery, S256 PKCE and state validation, JWT/JWKS signature
  verification, audience, scope, stable subject matching, and an issuer-bound HTTP resolve endpoint.

### What the Keycloak probes specifically proved

Keycloak 26 ran as the authorization server. A separate local FastAPI resolver endpoint acted as the
resource-server test surface and validated Keycloak-issued JWTs through Keycloak JWKS. The two were
separate processes with separate roles; this was not a test of an actual AI Gateway MCP endpoint.

The probes created temporary clients, scopes, mappers, and users, then deleted them. The resolver
accepted only a token whose audience matched the configured protected-resource identifier, whose scope
contained the temporary resolve scope, and whose `sub` matched the principal that owns the issued
reference. The PKCE probe used a public resolver client, authorization code, S256 challenge, callback
state checking, and a temporary subject mapper. It had to relax Keycloak's Secure-cookie handling only
inside its in-memory HTTP test client because the local container used HTTP; that is not a deployment
configuration to copy.

The ordinary MCP agent token was not supplied to either resolver probe and was not granted the resolve
scope. The implementation therefore demonstrates separation by construction, but it does not directly
test rejection of every possible ordinary agent token. A standard profile must require that ordinary
agent tokens lack resolve privilege unless separately and explicitly authorized.

These tests need at least one additional external authorization server before claiming portable OAuth
interoperability. They also leave discovery, consent, durable credential storage, sender constraint,
token revocation propagation, and an actual deployed MCP resource server to a profile specification
and deployment validation.

## Still provisional / not proven by this prototype

- A separate OAuth resolver client using the same protected resource, a narrow privilege, and
  Authorization Code plus PKCE is **validated as a viable resolver profile candidate**. It is not
  decided as the standardized resolver profile.
- Whether every relevant MCP host can retain trusted reference provenance across its result and action
  pipelines is unproven.
- The exact integration hooks exposed by Claude Code, Codex, and other hosts are unproven.
- The final extension identifier, negotiation settings, token grammar, and wire-schema details remain
  draft choices.
- Resolver endpoint discovery remains unresolved between Protected Resource Metadata and negotiated
  extension settings.
- Cross-session provenance persistence and its integrity, lifecycle, and privacy rules are not
  implemented; the prototype's in-memory provenance is lost on restart.
- Production-grade reference revocation, resolver-token revocation, sender constraint, audit, rate
  limiting, consent/recovery, and secret storage are not implemented.
- Cross-server delegation remains deferred and untested.
- Model isolation after an eligible sink invokes arbitrary downstream software is not proven; the
  narrow output guard only covers known values resolved in the current operation.

## Host provenance: minimum requirement and integration boundary

### Minimum neutral-host capability

A supporting host needs an issuer identity derived from an authenticated, extension-negotiated MCP
connection and a protected local store keyed by canonical token text. After decoding a `tools/call`
result, it records at least `(token, authenticated_issuer, first_observed)`. Before a protected sink
materializes a token, it performs an exact lookup: no record means unknown; one issuer means eligible
for resolver authorization; more than one issuer means ambiguous and fails closed. The stored issuer,
not model text, selects resolver configuration.

The prototype does not need to intercept or rewrite arbitrary model output. It observes negotiated,
authenticated tool results and inspects proposed content at a protected sink such as the local file
writer. The model may safely copy a previously observed token through ordinary intermediate text:
provenance stays in host state and exact lookup reconnects it. A copied unobserved token remains text.

After a host restart, this prototype loses its in-memory observations and consequently fails closed.
A real host must either persist an integrity-protected observation store or require a fresh trusted
observation; the persistence format and retention rules are still open. If the same token text is
observed from two issuers, the prototype raises an ambiguity error and performs no resolution.

### Existing implementation evidence

maisecrets already has targeted pre-action/post-result hook concepts and protected local-write
experience from Client-Vault. It is evidence that a coding-client integration can inspect an action
before a file/command boundary and control what returns afterward. It does not currently provide this
neutral Sensitive References observation store, negotiated-extension handling, or cross-session
provenance implementation.

AI Gateway has adjacent server-side PII sanitisation and OAuth/resource-server machinery. It is
evidence that an issuer can classify/substitute sensitive fields and enforce authorization. It does
not currently implement Sensitive References issuance, trusted host provenance, or the neutral OAuth
Resolver Profile.

The neutral standard needs an MCP host that can: negotiate the extension; expose authenticated server
identity to its extension implementation; inspect supported tool-result strings; maintain trusted
observations; intercept eligible sink input before execution; invoke a non-model resolver; prevent
plaintext from entering its ordinary model result; and fail closed when any of those guarantees are
unavailable. Product-specific hook names and generic interception of all model text are not required.
