# Host integration requirements

This extension requires a supporting host. A server cannot create trusted provenance through text alone.

## Minimum capability

The host needs to:

1. Negotiate the extension with an MCP server.
2. Obtain authenticated server identity from the MCP connection.
3. Inspect canonical tokens in supported tool-result strings.
4. Store `(token, issuer, first_observed, optional metadata)` outside model text.
5. Inspect input to an eligible protected sink before execution.
6. Resolve only known, unambiguous tokens through a non-model resolver.
7. Return reference-only content through the ordinary model-facing result path.
8. Fail closed if provenance, authorization, or sink isolation is unavailable.

The host need not rewrite arbitrary model output. It only needs the authenticated-result observation point
and the protected-sink input point. The model can copy a known reference through intermediate text because
the host looks up its exact token in trusted state.

## Restart and ambiguity

The prototype stores provenance in memory. It loses that state on restart and then fails closed. A production
host needs integrity-protected persistence or a fresh trusted observation. If one token maps to two issuers,
the host must not choose an issuer automatically.

## Existing evidence

maisecrets has pre-action and post-result hooks from Client-Vault work. MCPGate has server-side
classification and OAuth/resource-server experience. Neither product currently implements this neutral host
contract. The standard must describe capabilities, not product-specific hook names.
