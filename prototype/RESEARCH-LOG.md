# Research log

| Repository/file inspected | Reason | Relevant finding |
|---|---|---|
| Concept ZIP: `HANDOFF.md` | Required entry point | v0.4 requests a small provenance and protected-sink prototype. |
| Concept ZIP: `SPEC-DRAFT.md`, `DECISION-LOG.md`, `WIRE-REPRESENTATION.md` | Core/wire authority | Canonical text token, negotiated provenance, no `_meta` secrecy, generation-safe IDs. |
| Concept ZIP: `RESOLVER-BINDING.md`, `SECURITY-MODEL.md`, `CORE-VS-PROFILES.md` | Resolver/security authority | Separate OAuth resolver client/profile; authorization, sink rules, and issuer provenance are separate concerns. |
| Concept ZIP: `CURRENT-MCP-FIT.md` | Targeted MCP claims | Extensions and ordinary string `structuredContent` are the intended initial fit. |
| Client-Vault ZIP: `SPEC.md`, `CONFORMANCE.md` | Prior implementation evidence | First-sighting, origin binding, revocation, distinct resolver authorization, and all-or-nothing batches are reusable lessons. |
| maisecrets: `CLAUDE.md`, targeted hook/protocol search | Client-side integration evidence | Existing hook architecture provides pre-action/post-result concepts; no production code was modified. |
| AI Gateway: `CLAUDE.md`, targeted MCP PII/OAuth/capability search | Server-side evidence | Existing sanitization and OAuth/resource-server machinery are adjacent; no current Sensitive References implementation was found. |
| MCP official sources: SEP-2133 release material, schema, authorization guidance | Targeted compatibility verification | Explicit extension negotiation, `CallToolResult.structuredContent`, protected-resource metadata, and external authorization servers support the assumptions. |
| MCP schema `2026-07-28/schema.ts` | Exact extension capability shape | Both client and server use `extensions: { extensionIdentifier: settingsObject }`; client capabilities are per-request. |
| Local `mcp` Python SDK 1.21.0 | SDK feasibility probe | `FastMCP` registers a tool with structured output and returns the same string-valued sensitive-reference fields. |
| AI Gateway E2E Keycloak compose stack | External-AS PoC environment | Existing Keycloak 26.7 realm starts locally and publishes OIDC discovery with S256 PKCE; the test realm has no resolve-specific scope yet. |
