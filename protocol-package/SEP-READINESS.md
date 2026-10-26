# SEP readiness

**Status: experimental, honest checklist, 2026-10-26.** This file lists what a Specification Enhancement Proposal (SEP)
for Sensitive References needs, and the state of each item.

The sources of this package do not include the MCP SEP process document. The list below is the set of
items that a reviewer can expect. The exact process requirements (for example a sponsor, or a reference
implementation before the final state) are **not verified** against that document. Before submission,
read the current SEP guidelines of the MCP project and update this list.

Legend: **Done**, **Partial**, **Missing**.

## Specification text

| Item | State | Evidence or gap |
|---|---|---|
| Motivation and problem statement | Done | `README.md` "Problem", `SECURITY-MODEL.md` "Objective" |
| Core semantics (reference, provenance, fail closed) | Done | `SPEC-DRAFT.md`, `WIRE-REPRESENTATION.md` |
| Token grammar with test vectors | Done | `prototype/EXTENSION-PROFILE-DRAFT.md` "Test vectors"; `test_reference_grammar.py` |
| Settings schema | Partial | `prototype/schema/sensitive-references-settings.schema.json`. It has no field for limits (SC-09). |
| Resolver profile text | Partial | [PROFILE-oauth-resolver-1.md](PROFILE-oauth-resolver-1.md) states it as a proposed profile with implementation evidence. SC-01 to SC-11 and SC-20 are proposals, not accepted text. |
| Sink profile text | Partial | [PROFILE-local-file-1.md](PROFILE-local-file-1.md). The destination field is open (OQ-6). |
| Error codes | Partial | SC-11 and SC-12 propose them. SC-12 defines a schema for `structuredContent`; no test checks it. The reference server and the fake server of the host tests use the SC-11 codes. No accepted text. |
| Issuer identity | Partial | SC-01 proposes the RFC 9728 `resource` value, identical to the MCP URL (RFC 9728 section 3.3). The reference server is not conformant to SC-01 (known deviation P16). The test host interoperates with it only through a non-conformant operator option. |
| Alignment with the MCP authorization specification | Missing | SC-01 differs from the MCP specification 2025-11-25: for resolution it does not accept the well-known document at the origin root for an MCP URL with a path, because RFC 9728 section 3.3 makes that document unusable for the MCP URL. The SEP must resolve this conflict with the MCP project. The SEP must also confirm the reading of the RFC 9728 section 3.1 rule for a trailing slash (SC-01). |
| Resolve endpoint on another origin | Missing | SC-04 refuses an endpoint on another origin than the resource, also a configured one. A deployment that needs another origin needs a separately authenticated binding of the endpoint and a token with the endpoint as its audience. No text defines it. |
| Security considerations | Partial | `SECURITY-MODEL.md` and [THREAT-MODEL.md](THREAT-MODEL.md). No external security review of the protocol text. |
| Privacy considerations (destination, audit) | Partial | TM-7 and SC-10. No accepted rule. |
| Backward compatibility | Done | SC-16: only negotiated sessions get canonical tokens. Production run E5: legacy sessions got no references. |
| Open questions resolved | Partial | [OPEN-QUESTIONS.md](OPEN-QUESTIONS.md) records a provisional v1 design decision for each of the eleven items. No item has a community decision. OQ-1 (two issuers) and OQ-3 (issuer-side sink) need one most. |

## Identifiers and registrations

| Item | State | Evidence or gap |
|---|---|---|
| Official extension identifier | Missing | A provisional reverse-DNS identifier is in use. Examples use `org.example/sensitive-references` (SC-15, P7). |
| Profile identifiers `oauth-resolver-1`, `local-file-1` | Partial | Both implementations use them. No registry exists. |
| Wire value of `sink_type` | Partial | `local_file` in both implementations. Not in concept 0.5 (SC-10). |
| Metadata field `sensitive_references` | Missing | Not registered in the IANA "OAuth Protected Resource Metadata" registry (SC-02). |
| Resolve scope name | Partial | `sensitive-references.resolve` in both implementations. "Deployment-defined" in the profile draft (SC-03). |

## Implementations and interoperability

| Item | State | Evidence or gap |
|---|---|---|
| One server implementation | Done | The reference server, milestones M0 to M4 (plan section 6). Its source is not public. |
| One host implementation | Done | `prototype/demo/mcp_host.py`, 76 resolve tests and 13 host tests passed on 2026-10-26 at commit `fd7a9f2`. |
| End-to-end run of host and server | Partial | E1 to E3 and E7 (local), E4 to E6 (production, synthetic). E8 to E10: materialization in production on 2026-10-26, observed in one operator run, not independently reproduced, and only with the non-conformant option `--resource` (deviation P16). No conformant run succeeded: in E11 the conformant host stops at the challenge of the reference server, which names the metadata of the base URL. See [CONFORMANCE-RESULTS.md](CONFORMANCE-RESULTS.md#end-to-end-runs). |
| A second independent server | Missing | No other server implements the extension. |
| A second independent host | Missing | No general-purpose MCP host supports the extension. A plugin host cannot (P11, SC-19). |
| A public server implementation | Missing | The reference server source is not public. A reviewer cannot read it. |
| Interoperability with a second authorization server | Partial | The prototype Keycloak probes validate JWT/JWKS and Authorization Code + PKCE (`RESOLVER-PROFILE.md`). They did not run the full `oauth-resolver-1` flow with consent and refresh. |
| An official MCP SDK implementation | Missing | `prototype/CONFORMANCE.md` "Remaining before a standards proposal". |
| Conformance test suite usable by others | Partial | The host tests run offline against a fake server. No suite exists that tests an arbitrary server. |
| Durable host provenance | Partial | OQ-7, provisional v1 design decision: a host MAY persist provenance, and loss of trustworthy provenance MUST fail closed. The prototype keeps provenance in memory, which conforms. No integrity mechanism for a durable store is defined or implemented. |

## Process and review

| Item | State | Evidence or gap |
|---|---|---|
| Community discussion | Partial | `COMMUNITY-DISCUSSION.md` is a draft. This package does not show that it was posted or what the answers were. **Not verified.** |
| Community review of the profiles | Missing | No external review of SC-01 to SC-20. |
| Independent security review of the implementations | Partial | The reference server had one external review round on M4a (plan section 6, "Review round 1"). Its verdict was NO-SHIP with no BLOCKER, and the implementer fixed four findings. The implementer reported a second review round, after which revision R2 exists (CONFORMANCE-RESULTS.md). This package has no verdict of that round. |
| Sponsor in the MCP project | **Not verified** | The sources do not mention one. |
| Vendor-neutral text | Partial | The normative text of this package (SPEC-CHANGES.md and the rules of the two profiles) names no product. The evidence names two: Keycloak, only for the prototype probes (PROFILE-oauth-resolver-1.md section 8 and the row above), and Google Chrome, only as the tested browser of lessons L-a and L-b in IMPLEMENTATION-GUIDE.md. The concept files `HOST-INTEGRATION.md`, `IMPLEMENTATION-EVIDENCE.md` and `README.md` name products. |
| Prototype tests green | Done | 100 of 100 passed on 2026-10-26 with Python 3.14.8 and MCP SDK 2.3.0 at the tested commit (pytest: 100 passed, 71 subtests passed; unittest: 100 OK). MCP SDK 1.x was not tested. |

## Summary

The core semantics and one pair of implementations are ready for discussion. A SEP is **not ready** for
submission. The blocking items are: an official extension identifier, a second independent implementation
(server or host), community review of the proposed changes, community confirmation of the provisional v1
design decisions (in particular OQ-1 and OQ-3), the conformance of the reference server to SC-01, and the
registration of the discovery field or a decision on another location (OQ-8).
