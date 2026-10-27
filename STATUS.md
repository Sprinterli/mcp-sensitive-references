# Status

**Status: Concept 0.6 draft (not an MCP standard, not an accepted SEP).**

Sensitive References is a possible optional MCP extension. Concept 0.6 is one normative text: a core and
two profiles. It replaces the combination of Concept 0.5 and the proposed changes SC-01 to SC-20, with one exception:
SC-18 (the issuer-side sink) is not integrated and stays open as OQ-3, with an interim floor.

Two implementations exist: the reference server MCPGate (source not public) and the reference host in
[prototype/](prototype/). One run of the two without a deviation option succeeded on
2026-10-27 (E12, one operator run of each step). Concept 0.6 makes no claim of full conformance.

The largest open risks are:

- host support for durable, authenticated provenance and for protected-sink interception;
- the conflict of the discovery rules with the root fallback of the MCP authorization specification
  (OQ-13);
- provisional decisions that no community review confirmed (OQ-1, OQ-2, OQ-4 to OQ-11, OQ-13 to OQ-16);
- the issuer-side sink, which Concept 0.6 does not define (OQ-3).

A SEP is not ready. [protocol-package/SEP-READINESS.md](protocol-package/SEP-READINESS.md) lists the
blocking items.
