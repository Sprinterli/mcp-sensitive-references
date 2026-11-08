# Sensitive References protocol package (milestone M6)

**Status: experimental, pre-SEP.** This package is not an MCP standard, not an accepted Specification
Enhancement Proposal (SEP), and not a product specification.

**Concept 0.7.** The normative text is in the repository root. This package keeps the history of the
proposals (SPEC-CHANGES.md, SC-01 to SC-26) and the evidence for each rule. The conformance gap of E11
(P16) ended with a server fix on 2026-10-27; run E12 ran without a deviation option
([IMPLEMENTATION-EVIDENCE.md](../IMPLEMENTATION-EVIDENCE.md)).

## What this package is

This package collects the protocol results of three implementations:

- **The reference server.** An MCP server that issues Sensitive References, implements the
  `oauth-resolver-1` profile and accepts the sink profiles `local-file-1`, `process-1` (under another
  identifier, see PROFILE-process-1.md) and `display-1`. Its source is not public.
- **The test host.** The independent MCP host in this repository, `prototype/demo/mcp_host.py`. It negotiates
  the extension, records issuer provenance, gets its own resolver token and writes a local file.
- **The second host.** A public coding-agent plugin. It resolves references into files, commands and the
  screen of the person. It declares no extension (PROFILE-process-1.md, PR1).

The proposals in SPEC-CHANGES.md are the history of the normative text. The normative text of Concept 0.7
is in the repository root.

## Files

| File | Content |
|---|---|
| [SPEC-CHANGES.md](SPEC-CHANGES.md) | Each proposed change to concept 0.5, with the problem, the evidence, proposed normative text and the compatibility impact. |
| [PROFILE-oauth-resolver-1.md](PROFILE-oauth-resolver-1.md) | The proposed OAuth resolver profile with implementation evidence. Each rule names its test or says "not yet tested", "not verified" or "not conformant". |
| [PROFILE-local-file-1.md](PROFILE-local-file-1.md) | The local-file sink profile with the evidence of the test host, the reference server and the second host. |
| [PROFILE-process-1.md](PROFILE-process-1.md) | The process sink profile with the evidence of the reference server and the second host. |
| [PROFILE-display-1.md](PROFILE-display-1.md) | The display sink profile with the evidence of the reference server and the second host. |
| [CONFORMANCE-RESULTS.md](CONFORMANCE-RESULTS.md) | A matrix: requirement, server-side evidence, host-side evidence, end-to-end evidence. |
| [THREAT-MODEL.md](THREAT-MODEL.md) | The delta to [SECURITY-MODEL.md](../SECURITY-MODEL.md) that the two profiles cause. |
| [IMPLEMENTATION-GUIDE.md](IMPLEMENTATION-GUIDE.md) | Do and do-not lists for a server implementer and for a host implementer. |
| [OPEN-QUESTIONS.md](OPEN-QUESTIONS.md) | The questions that stay open, each with options and a provisional v1 design decision. |
| [SEP-READINESS.md](SEP-READINESS.md) | A checklist of what a SEP needs, and the state of each item. |

The files relate as follows. SPEC-CHANGES.md is the main proposal. The two profile files give the full
rule set of the profiles that SPEC-CHANGES.md refers to. CONFORMANCE-RESULTS.md shows the evidence for
each rule. THREAT-MODEL.md and IMPLEMENTATION-GUIDE.md derive from the same findings. OPEN-QUESTIONS.md
and SEP-READINESS.md list what this package does not decide.

## Changes in this revision

This revision records Concept 0.7. The normative text of each change is in the repository root.

- **SC-21** (new): a sink profile can require its own scope. The discovery object names the scope set of
  each sink profile in `sinks`, and the field name `sensitive_references` is fixed. A missing sink scope
  gives `403 insufficient_scope` before any lookup. SC-03 gets a "Concept 0.7" paragraph.
- **SC-22** and **SC-23** (new): the sink profiles `process-1` and `display-1`, each with its own evidence
  file.
- **SC-06** gets a "Concept 0.7" paragraph: a consent page at every authorization request, with the
  account, the client, the loopback host and port, the time and one line per sink scope.
- **SC-24** (new): references per person, and the account hint. **SC-25** (new): no value without its
  audit event. **SC-26** (new): revocation per device.
- **PROFILE-oauth-resolver-1.md** gets the evidence of revision R3 (rows A3, A7, C1, C2, C5, C7, C9, T13
  to T15, R5, R10, R11, R15, R16, and section 5a, V1 to V7).
- **THREAT-MODEL.md** updates TM-1 and TM-4 and adds TM-14 (process) and TM-15 (display).
- **CONFORMANCE-RESULTS.md** gets the section "Concept 0.7" and run E13.
- **IMPLEMENTATION-GUIDE.md** gets server items 16 to 21 and host items 13 to 16.

## Finding identifiers

This package cites two finding lists:

- **F1 to F13** are in [prototype/M4-FINDINGS.md](../prototype/M4-FINDINGS.md). The test host found them.
- **P1 to P16** are in the implementation plan of the reference server, section 7. That plan is not
  public. SPEC-CHANGES.md repeats the content of each P finding that it uses, so that a reader does not
  need the plan.

The reference server also uses milestone names M0 to M4 from its plan. M0 is registry integrity, M1 is the
echo guard, M2 is revocation, M3 is the canonical token behind negotiation, and M4 is `oauth-resolver-1`
with `local-file-1`. This package is milestone M6.

## Sources and versions

| Source | Version |
|---|---|
| Concept 0.5 (the root files) | this repository. Unchanged on this branch. |
| The test host, the prototype and their tests | this repository, branch `m7-consolidation`, the tested commit `6cdd658` (`prototype/demo/mcp_host.py`, `prototype/src/`, `prototype/tests/`); for Concept 0.7, branch `concept-0.7`, commit `65f17e5` |
| The reference server plan, sections 4 to 8 | reference server revision R1 (not public) |
| The reference server tests that this package cites | revision R1: the test module for resolver consent (25 test functions) and the test module for negotiated canonical references (26 test functions). Rows marked "(R2)" cite tests of revision R2, rows marked "(R3)" tests of revision R3. |
| The second host | release 0.9.1 of a public coding-agent plugin ([IMPLEMENTATION-EVIDENCE.md](../IMPLEMENTATION-EVIDENCE.md) names it), commit `4f9fd34` of its main branch |

**Evidence labels R1 and R2.** The reference server is not public, so its revision identifiers do not
help a reader. This package uses two neutral labels instead. **R1** is the revision of the plan and the
tests that this package read first. **R2** is the later revision after the second server review. At R2
the implementer ran end-to-end round E7 and reported 58 passing test cases in the consent module. The
profile rows A8, C7, C9, C10, R9, R12, R13 and R14 cite tests of R2. **R3** is the revision of Concept 0.7:
the server versions 2.0.3824 and 2.0.3826 of 2026-11-08. This package read its tests at the release tag
of 2.0.3826 and did not run them.

This package did not run the reference server tests. It read their names and assertions at the revision
above. A row that cites a reference server test is "read, not re-run".

**Commit hashes.** Each commit hash in this package (for example the tested commit) refers to
the published history of the branch `m7-consolidation`. That branch is published as it is, without a
squash, so the hashes stay valid.

The prototype test suite last ran on 2026-11-08 at commit `65f17e5` (branch `concept-0.7`, the prototype
of Concept 0.7) with Python 3.14.8 and MCP Python SDK 2.3.0: 212 tests passed. The run before it, on
2026-10-27 at commit `6cdd658` (branch `m7-consolidation`), passed 133 tests. SDK 1.x was not tested (see
[CONFORMANCE-RESULTS.md](CONFORMANCE-RESULTS.md#test-run)).

## Naming in this package

- The extension identifier in the examples is `org.example/sensitive-references`. The reference server
  uses a provisional reverse-DNS identifier of its own. No official identifier exists (SPEC-CHANGES.md,
  SC-15).
- Example hosts are `example.com` and `example.org`.
- All values in the tests and in the end-to-end runs are synthetic.
