# Sensitive References protocol package (milestone M6)

**Status: experimental, pre-SEP.** This package is not an MCP standard, not an accepted Specification
Enhancement Proposal (SEP), and not a product specification.

## What this package is

This package collects the protocol results of two implementations of concept 0.5:

- **The reference server.** An MCP server that issues Sensitive References, implements the
  `oauth-resolver-1` profile and accepts the `local-file-1` sink. Its source is not public.
- **The test host.** The independent MCP host in this repository, `prototype/demo/mcp_host.py`. It negotiates
  the extension, records issuer provenance, gets its own resolver token and writes a local file.

The package does not change concept 0.5. The concept files in the repository root stay as they are. Each
proposal in this folder is a **proposed change**. A reader must not treat a proposal as concept text.

## Files

| File | Content |
|---|---|
| [SPEC-CHANGES.md](SPEC-CHANGES.md) | Each proposed change to concept 0.5, with the problem, the evidence, proposed normative text and the compatibility impact. |
| [PROFILE-oauth-resolver-1.md](PROFILE-oauth-resolver-1.md) | The OAuth resolver profile as implemented and tested. Each rule names its test or says "not yet tested". |
| [PROFILE-local-file-1.md](PROFILE-local-file-1.md) | The local-file sink profile as the test host implements it. |
| [CONFORMANCE-RESULTS.md](CONFORMANCE-RESULTS.md) | A matrix: requirement, server-side evidence, host-side evidence, end-to-end evidence. |
| [THREAT-MODEL.md](THREAT-MODEL.md) | The delta to [SECURITY-MODEL.md](../SECURITY-MODEL.md) that the two profiles cause. |
| [IMPLEMENTATION-GUIDE.md](IMPLEMENTATION-GUIDE.md) | Do and do-not lists for a server implementer and for a host implementer. |
| [OPEN-QUESTIONS.md](OPEN-QUESTIONS.md) | The questions that stay open, each with options and a recommendation. |
| [SEP-READINESS.md](SEP-READINESS.md) | A checklist of what a SEP needs, and the state of each item. |

The files relate as follows. SPEC-CHANGES.md is the main proposal. The two profile files give the full
rule set of the profiles that SPEC-CHANGES.md refers to. CONFORMANCE-RESULTS.md shows the evidence for
each rule. THREAT-MODEL.md and IMPLEMENTATION-GUIDE.md derive from the same findings. OPEN-QUESTIONS.md
and SEP-READINESS.md list what this package does not decide.

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
| Concept 0.5 and the prototype | this repository, branch `m4-local-file-sink`, commit `fe87dad` |
| The test host and its tests | the same commit, `prototype/demo/mcp_host.py`, `prototype/tests/` |
| The reference server plan, sections 4 to 8 | reference server revision `e5268633f` (not public) |
| The reference server tests that this package cites | the same revision: the test module for resolver consent (25 test functions) and the test module for negotiated canonical references (26 test functions) |

This package did not run the reference server tests. It read their names and assertions at the revision
above. A row that cites a reference server test is "read, not re-run".

The prototype test suite last ran on 2026-10-26 at commit `dd7afe2` (branch `m7-consolidation`) with
Python 3.14.8 and MCP Python SDK 2.3.0: 71 tests passed. SDK 1.x was not tested (see
[CONFORMANCE-RESULTS.md](CONFORMANCE-RESULTS.md#test-run)).

## Naming in this package

- The extension identifier in the examples is `org.example/sensitive-references`. The reference server
  uses a provisional reverse-DNS identifier of its own. No official identifier exists (SPEC-CHANGES.md,
  SC-15).
- Example hosts are `example.com` and `example.org`.
- All values in the tests and in the end-to-end runs are synthetic.
