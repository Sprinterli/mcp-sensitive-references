# Status

**Status: pre-SEP design exploration.**

Sensitive References is a possible optional MCP extension. It has a small Python feasibility prototype
and focused tests. It is not an MCP standard, an accepted SEP, or a product specification.

The design remains open for community review. The largest unresolved risk is host support for durable,
authenticated `(token, issuer)` provenance and protected-sink interception.

The OAuth resolver experiment validates one profile candidate with Keycloak. It does not establish a
portable standard profile or interoperability with every host or authorization server.
