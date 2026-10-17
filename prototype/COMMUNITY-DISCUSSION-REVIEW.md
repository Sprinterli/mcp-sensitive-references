# Review of the 0.4 community discussion draft

Source reviewed: `COMMUNITY-DISCUSSION-DRAFT.md` in
`mcp-sensitive-references-concept-0.4.zip`. Labels describe the support for the claim, not a standards
decision. “Supported by MCP spec / prior art” refers to the targeted MCP schema/authorization review
and Client-Vault implementation evidence recorded in `RESEARCH-LOG.md`.

| Draft claim | Review label | Review |
|---|---|---|
| MCP records can contain sensitive fields the model need not read to route or format work. | supported by MCP spec / prior art | Client-Vault and the problem statement support the workflow motivation; it is not a general guarantee about every task. |
| Servers otherwise choose plaintext or redaction, and redaction can block requested artifacts. | supported by MCP spec / prior art | Keep as motivation, preferably “often” rather than “generally” to avoid claiming a complete taxonomy of existing mechanisms. |
| An optional extension can return `⟦sref:…⟧` in place of plaintext. | supported by prototype | The demo and FastMCP structured-output probe demonstrate the representation; extension standardisation remains pending. |
| The host records an observed token against an authenticated MCP server. | supported by prototype | Accurate for the prototype. Add that host support is required and is the principal open integration risk. |
| The model may copy a token; possession is not authorization. | supported by prototype | Exact lookup and separate resolver authorization demonstrate this for the PoC. |
| A non-model resolver can materialize into an eligible sink without an ordinary model-visible result. | supported by prototype | Demonstrated for the protected local-file sink only; qualify the claim to a supporting host/sink profile. |
| Classification is outside the protocol. | supported by MCP spec / prior art | This is a deliberate scope decision (D3), consistent with prior Client-Vault evidence, rather than a prototype result. |
| Core, resolver profile, and host integration are separable layers. | supported by MCP spec / prior art | Keep as architecture and scope; the prototype mirrors it but does not prove universal composability. |
| Existing MCP gateway plus maisecrets demonstrate the end-to-end pattern. | supported by MCP spec / prior art | Keep, but name it as Client-Vault implementation evidence rather than as Sensitive References interoperability evidence. |
| A separate OAuth client for the same protected resource with narrow authorization is the portable direction. | should be softened | Say: “A separate OAuth resolver client is validated as a viable resolver-profile candidate with Keycloak.” Do not call it the interoperable baseline yet. |
| This works when resource and authorization servers are separate. | supported by prototype | The Keycloak probes used Keycloak as AS and a separate local resolver resource-server surface. Qualify that it was one AS and not an AI Gateway deployment. |
| Text tokens in ordinary text and `structuredContent` avoid a new `ContentBlock`. | supported by prototype | FastMCP and unit tests support schema preservation; current MCP schema supports the relevant surfaces. |
| Text token plus host provenance preserves the key property. | still hypothesis | The PoC demonstrates it for one controlled host/sink. Ecosystem-wide host correctness and downstream echo containment remain unproven. |
| The extension is compatible with current MCP. | should be softened | Say it fits current extension negotiation and string-valued result surfaces. Full host interoperability, final identifier, and settings schema are open. |
| The ordinary MCP token does not grant resolution rights. | should be softened | The prototype does not use an ordinary agent token and enforces a resolve scope. The profile must require non-automatic grant; direct production-agent-token rejection remains to test. |
| Questions inviting feedback on host feasibility, resolver profile, and delegation. | supported by MCP spec / prior art | Keep. The host-provenance question should be first because it is now the largest design risk. |
| “Sensitive data remains referencable and actionable without plaintext needing to enter model context.” | should be softened | Keep as the objective, prefaced with “for supporting hosts, resolver profiles, and eligible sinks.” It is not yet an ecosystem-wide guarantee. |
| The work is pre-SEP and seeks security/implementation feedback. | supported by MCP spec / prior art | Keep unchanged; it accurately reflects the extension process and evidence level. |

## Recommended editorial changes before posting

1. Lead with the requirement for a supporting host to retain authenticated `(token, issuer)` state and
   fail closed after lost/ambiguous provenance.
2. Replace “current direction” for OAuth with “viable resolver-profile candidate validated with
   Keycloak”; preserve the question asking whether it is the right interoperable baseline.
3. Qualify “without plaintext” claims to eligible protected sinks and state that downstream output echo
   remains an integration-profile responsibility.
4. Say that current MCP provides extension negotiation and compatible result surfaces, not that MCP
   hosts already expose all required hooks.
