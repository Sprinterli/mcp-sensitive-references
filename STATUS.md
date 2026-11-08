# Status

**Status: Concept 0.7 draft (not an MCP standard, not an accepted SEP).**

Sensitive References is a possible optional MCP extension. Concept 0.7 is one normative text: a core, the
resolver profile `oauth-resolver-1` and three sink profiles (`local-file-1`, `process-1`, `display-1`). It
describes what runs in the implementations: sink scopes, a consent page at every authorization request,
references per person, no value without its audit event, and revocation per device. SC-18 (the
issuer-side sink) is still not integrated and stays open as OQ-3, with an interim floor.

Three implementations exist: the reference server MCPGate (source not public; revision R3, versions
2.0.3824 and 2.0.3826), the reference host in [prototype/](prototype/) (`local-file-1`, `process-1` and `display-1`, with a
demo-level prototype issuer, tested offline only) and a second
host, the coding-agent plugin maisecrets (releases 0.9.0 and 0.9.1; it declares no extension). The
evidence of Concept 0.7 is the reference server tests of R3 (read, not run by this repository), the source
and the tests of the second host (read, not run), and run E13 of 2026-11-08: a display click after the
account fix, observed in one operator run and not independently reproduced. Concept 0.7 makes no claim of
full conformance.

The largest open risks are:

- host support for durable, authenticated provenance and for protected-sink interception;
- the limit of the process and the display sink: any local process of the person that holds a token with
  that scope gets the full value;
- the conflict of the discovery rules with the root fallback of the MCP authorization specification
  (OQ-13);
- provisional decisions that no community review confirmed (OQ-1, OQ-2, OQ-4 to OQ-7, OQ-9 to OQ-11, OQ-13
  to OQ-16);
- the issuer-side sink, which Concept 0.7 does not define (OQ-3).

A SEP is not ready. [protocol-package/SEP-READINESS.md](protocol-package/SEP-READINESS.md) lists the
blocking items.
