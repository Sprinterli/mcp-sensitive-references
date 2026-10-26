# SEP readiness

**Status: honest checklist, 2026-10-25.** This file lists what a Specification Enhancement Proposal (SEP)
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
| Resolver profile text | Partial | [PROFILE-oauth-resolver-1.md](PROFILE-oauth-resolver-1.md) states it as implemented. SC-01 to SC-11 are proposals, not accepted text. |
| Sink profile text | Partial | [PROFILE-local-file-1.md](PROFILE-local-file-1.md). The destination field is open (OQ-6). |
| Error codes | Partial | SC-11 and SC-12 propose them. The reference server and the fake server of the host tests use the SC-11 codes (commit `dd7afe2`). No accepted text. |
| Issuer identity | Partial | SC-01 proposes RFC 9728 `resource`. The reference server deviates from RFC 9728 section 3.3 (P16). |
| Security considerations | Partial | `SECURITY-MODEL.md` and [THREAT-MODEL.md](THREAT-MODEL.md). No external security review of the protocol text. |
| Privacy considerations (destination, audit) | Partial | TM-7 and SC-10. No accepted rule. |
| Backward compatibility | Done | SC-16: only negotiated sessions get canonical tokens. Production run E5: legacy sessions got no references. |
| Open questions resolved | Missing | [OPEN-QUESTIONS.md](OPEN-QUESTIONS.md) has eleven open items. OQ-1 (two issuers) and OQ-3 (issuer-side sink) need a community decision. |

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
| One host implementation | Done | `prototype/demo/mcp_host.py`, 35 resolve tests and 13 host tests passed on 2026-10-25. |
| End-to-end run of host and server | Done | E1 to E3 (local), E4 to E6 (production, synthetic). See [CONFORMANCE-RESULTS.md](CONFORMANCE-RESULTS.md#end-to-end-runs). |
| A second independent server | Missing | No other server implements the extension. |
| A second independent host | Missing | No general-purpose MCP host supports the extension. A plugin host cannot (P11, SC-19). |
| A public server implementation | Missing | The reference server source is not public. A reviewer cannot read it. |
| Interoperability with a second authorization server | Partial | The prototype Keycloak probes validate JWT/JWKS and Authorization Code + PKCE (`RESOLVER-PROFILE.md`). They did not run the full `oauth-resolver-1` flow with consent and refresh. |
| An official MCP SDK implementation | Missing | `prototype/CONFORMANCE.md` "Remaining before a standards proposal". |
| Conformance test suite usable by others | Partial | The host tests run offline against a fake server. No suite exists that tests an arbitrary server. |
| Durable host provenance | Missing | OQ-7. The prototype keeps provenance in memory. |

## Process and review

| Item | State | Evidence or gap |
|---|---|---|
| Community discussion | Partial | `COMMUNITY-DISCUSSION.md` is a draft. This package does not show that it was posted or what the answers were. **Not verified.** |
| Community review of the profiles | Missing | No external review of SC-01 to SC-19. |
| Independent security review of the implementations | Partial | The reference server passed one external review round on M4a (plan section 6, "Review round 1": NO-SHIP, no BLOCKER, four findings fixed). A second round is not recorded in the sources. |
| Sponsor in the MCP project | **Not verified** | The sources do not mention one. |
| Vendor-neutral text | Partial | This package is vendor-neutral. The concept files `HOST-INTEGRATION.md`, `IMPLEMENTATION-EVIDENCE.md` and `README.md` name products. |
| Prototype tests green | Partial | 70 of 71 passed. `test_mcp_sdk_demo` needs MCP SDK 1.x and does not import under 2.x. |

## Summary

The core semantics and one pair of implementations are ready for discussion. A SEP is **not ready** for
submission. The blocking items are: an official extension identifier, a second independent implementation
(server or host), community review of the proposed changes, a decision on OQ-1 and OQ-3, and the
registration of the discovery field or a decision on another location.
