# Sensitive References protocol package (milestone M6)

**Status: experimental, pre-SEP.** This package is not an MCP standard, not an accepted Specification
Enhancement Proposal (SEP), and not a product specification.

**Known conformance gap (E11, P16).** No conformant end-to-end run of the test host against the reference
server succeeded. The challenge of the reference server names the protected-resource metadata of its base
URL, not of the MCP endpoint (deviation P16), and the conformant test host at commit `8394a02` stopped
there (E11, one operator run). The production runs E8 to E10, observed in one operator run and not
independently reproduced, succeeded only with the non-conformant option `--resource`. This package does
not claim interoperability or conformance of the reference server. See
[CONFORMANCE-RESULTS.md](CONFORMANCE-RESULTS.md#end-to-end-runs).

## What this package is

This package collects the protocol results of two implementations of concept 0.5:

- **The reference server.** An MCP server that issues Sensitive References, implements the
  `oauth-resolver-1` profile and accepts the `local-file-1` sink. Its source is not public.
- **The test host.** The independent MCP host in this repository, `prototype/demo/mcp_host.py`. It negotiates
  the extension, records issuer provenance, gets its own resolver token and writes a local file.

The package does not change concept 0.5. The concept files in the repository root stay as they are. The root `.gitignore` gets one line
(`.DS_Store`). Each proposal in this folder is a **proposed change**. A reader must not treat a proposal as concept text.

## Files

| File | Content |
|---|---|
| [SPEC-CHANGES.md](SPEC-CHANGES.md) | Each proposed change to concept 0.5, with the problem, the evidence, proposed normative text and the compatibility impact. |
| [PROFILE-oauth-resolver-1.md](PROFILE-oauth-resolver-1.md) | The proposed OAuth resolver profile with implementation evidence. Each rule names its test or says "not yet tested", "not verified" or "not conformant". |
| [PROFILE-local-file-1.md](PROFILE-local-file-1.md) | The proposed local-file sink profile with the evidence of the test host. |
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

All changes stay proposals. None of them is concept text.

- **SC-01** follows RFC 9728 section 3.3 strictly: the `resource` value is identical to the MCP URL. The
  rule that the MCP URL may lie under the resource is removed. The reference server behaviour (P16) is a
  separate, non-conformant "known deviation" in SC-01, PROFILE D5 and CONFORMANCE-RESULTS.md.
- **SC-18** requires an explicit authorization decision for issuer-side resolution. Possession of a
  reference does not authorize it. THREAT-MODEL.md gets TM-10.
- **SC-11** records that the fake server of the host tests uses the SC-11 codes. The host name
  `unauthorized` is a host failure reason, not a server code. A 401 answer carries `WWW-Authenticate`.
- **SC-20** (new) makes the loopback redirect rules normative: exact string comparison of the redirect URI
  with any port for a loopback IP redirect URI only, the literal `127.0.0.1`, and a `form-action`
  directive of the consent page, if the page has one, that permits the exact loopback origin.
- **SC-06** binds an approval to subject, client, resource, resolve scope and the sink profiles that the
  consent page names. SC-06, SC-14 and SC-18 define "resist framing and CSRF", "integrity" and "current"
  by observable outcomes.
- **SC-01, SC-02 and SC-08** in the test host: the issuer string stays as given, discovery uses only the two
  RFC 9728 mechanisms, an incomplete discovery object stops the host, and a missing `iss` is refused when
  the server advertises it. Each rule has new host tests.
- **IMPLEMENTATION-GUIDE.md** gets six lessons from a production run on 2026-10-26. Lessons L-a and L-b
  name the tested browser.
- **CONFORMANCE-RESULTS.md** records the tested configuration (Python 3.14.8, `mcp` 2.3.0, 88 tests
  passed at that time; SDK 1.x not tested) and the production runs E8 to E10. The runs are "observed (one operator
  run, not independently reproduced)" and upgrade no row to "verified".
- **Second review round.** SC-01 uses the discovery order of the MCP specification (the
  `WWW-Authenticate` challenge first) and names its conflict with the MCP root fallback. The issuer keeps
  the query of the MCP URL, and the well-known URL keeps the query and a trailing slash. Without metadata
  the host stops, unless an operator states that the server has none. SC-04 refuses a configured endpoint
  on another origin. D10 requires S256 in the authorization server metadata. SC-12 gets a schema. The
  profile titles say "proposed, with implementation evidence".
- **Fourth review round.** The fetch policy of SC-01 defines a non-public address by the IANA
  special-purpose registries, has no automatic exception for a local MCP URL, and forbids redirects and
  environment proxies for each request of the discovery and the authorization. SC-07 names the attacker
  boundary of the token cache. SC-10 requires `destination`. SC-11 defines protected data by exact
  representations and encodings. SC-12 states the `reasons` key without the `reference_` prefix. SC-20
  names its restriction of RFC 8252 section 7.3.
- **Fifth review round.** SC-01 requires that the host connects to the checked address (DNS rebinding),
  and the most specific registry entry decides. SC-20 requires only that a `form-action` directive, if
  present, permits the loopback origin; the rest is a security recommendation in lesson L-a. SC-11 moves
  derived values (a hash, a MAC) to security guidance outside the proposed text. SC-13 permits `unknown` after the
  server discards the record of an expired reference.
- **OPEN-QUESTIONS.md** labels each recommendation as a provisional v1 design decision. OQ-7 now permits
  durable host provenance, and loss of trustworthy provenance must fail closed. SEP-READINESS.md follows.

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
| The test host, the prototype and their tests | this repository, branch `m7-consolidation`, the tested commit `6cdd658` (`prototype/demo/mcp_host.py`, `prototype/src/`, `prototype/tests/`) |
| The reference server plan, sections 4 to 8 | reference server revision R1 (not public) |
| The reference server tests that this package cites | revision R1: the test module for resolver consent (25 test functions) and the test module for negotiated canonical references (26 test functions). Rows marked "(R2)" cite tests of revision R2. |

**Evidence labels R1 and R2.** The reference server is not public, so its revision identifiers do not
help a reader. This package uses two neutral labels instead. **R1** is the revision of the plan and the
tests that this package read first. **R2** is the later revision after the second server review. At R2
the implementer ran end-to-end round E7 and reported 58 passing test cases in the consent module. The
profile rows A8, C7, C9, C10, R9, R12, R13 and R14 cite tests of R2.

This package did not run the reference server tests. It read their names and assertions at the revision
above. A row that cites a reference server test is "read, not re-run".

**Commit hashes.** Each commit hash in this package (for example the tested commit) refers to
the published history of the branch `m7-consolidation`. That branch is published as it is, without a
squash, so the hashes stay valid.

The prototype test suite last ran on 2026-10-27 at commit `6cdd658` (branch `m7-consolidation`) with
Python 3.14.8 and MCP Python SDK 2.3.0: 133 tests passed. SDK 1.x was not tested (see
[CONFORMANCE-RESULTS.md](CONFORMANCE-RESULTS.md#test-run)).

## Naming in this package

- The extension identifier in the examples is `org.example/sensitive-references`. The reference server
  uses a provisional reverse-DNS identifier of its own. No official identifier exists (SPEC-CHANGES.md,
  SC-15).
- Example hosts are `example.com` and `example.org`.
- All values in the tests and in the end-to-end runs are synthetic.
