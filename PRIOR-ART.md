# Prior art and adjacent mechanisms

## Client secret references

[maisecrets](https://github.com/Mcpgate-de/maisecrets) and similar client-side secret-reference systems can
avoid displaying a stored secret. Sensitive References focus on issuer-held values and authenticated issuer
provenance in an MCP workflow.

## Context redaction and message transformation

[MCP Python SDK interceptor API](https://py.sdk.modelcontextprotocol.io/advanced/middleware/) can observe,
transform, or refuse MCP messages. Redaction can prevent plaintext from reaching a model. This proposal adds
a reference that a later protected sink can materialize after separate authorization.

## Elicitation and private input

[MCP elicitation](https://modelcontextprotocol.io/specification/2025-06-18/client/elicitation) can collect user input
through a client flow. It addresses a different direction: user-to-host input rather than a server-held
value returned by an MCP server.

## OAuth and sender constraint

[MCP authorization](https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization) and
[OAuth DPoP](https://www.rfc-editor.org/rfc/rfc9449) provide authorization and sender-constraint tools.
This proposal does not replace them. A resolver profile can use them.

## DLP, NER, and tokenization

Classification and tokenization systems can decide which values need protection. Sensitive References do
not define detection or classification. They define the later reference and authorized materialization path.
