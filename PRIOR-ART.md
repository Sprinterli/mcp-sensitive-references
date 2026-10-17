# Prior art and adjacent mechanisms

## Client secret references

Secret managers and client-side secret references can avoid displaying a stored secret. Sensitive References
focus on issuer-held values and authenticated issuer provenance in an MCP workflow.

## Context redaction and middleware

Redaction can prevent plaintext from reaching a model. This proposal adds a reference that a later protected
sink can materialize after separate authorization.

## Elicitation and private input

Private-input flows can collect values without placing them in ordinary model content. They address a
different direction: user-to-host input rather than a server-held value returned by an MCP server.

## OAuth and sender constraint

OAuth scopes, audience checks, PKCE, and sender-constrained tokens such as DPoP can protect resolver
authorization. This proposal does not replace them. A resolver profile can use them.

## DLP, NER, and tokenization

Classification and tokenization systems can decide which values need protection. Sensitive References do
not define detection or classification. They define the later reference and authorized materialization path.
