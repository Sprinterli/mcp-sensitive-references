# Prior art and adjacent mechanisms

**Status: Concept 0.6 draft.** This file is not normative.

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
This proposal does not replace them. The resolver profile `oauth-resolver-1` builds on OAuth
protected-resource metadata ([RFC 9728](https://www.rfc-editor.org/rfc/rfc9728)), resource indicators
([RFC 8707](https://www.rfc-editor.org/rfc/rfc8707)), authorization server metadata
([RFC 8414](https://www.rfc-editor.org/rfc/rfc8414)), the `iss` response parameter
([RFC 9207](https://www.rfc-editor.org/rfc/rfc9207)) and native-app loopback redirects
([RFC 8252](https://www.rfc-editor.org/rfc/rfc8252)). DPoP is optional in its first version.

## DLP, NER, and tokenization

Classification and tokenization systems can decide which values need protection. Sensitive References do
not define detection or classification. They define the later reference and authorized materialization path.
