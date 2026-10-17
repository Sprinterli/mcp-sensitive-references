# Prototype completion audit

This audit covers the requested isolated Sensitive References prototype, not a production deployment or SEP.

| Requested outcome | Current evidence |
|---|---|
| Customer-list result has reference-only email/phone strings | `demo/server.py`; SDK structured-output test |
| Host records trusted provenance | `ProvenanceStore`; forged/unobserved and negotiation tests |
| Copied observed token can be materialized | protected file sink test |
| Forged/unobserved token fails closed | `test_unobserved_forged_token_fails_closed` |
| Issuer ambiguity fails closed | `test_ambiguous_issuer_fails_closed` |
| Protected local file gets plaintext while model-facing content remains a token | `test_valid_observed_reference_resolves_to_protected_file_only` |
| Resolver interface is profile-neutral | `Resolver` protocol; in-memory and HTTP implementations |
| Batch is all-or-nothing | sink, resolver, HTTP adapter tests |
| Unknown, revoked, expired, and stale-remapping hazards fail closed | immutable random IDs plus lifecycle tests |
| Possession is insufficient | resolver-authorization test |
| OAuth Resolver Profile is viable with an external authorization server | Keycloak OIDC and Authorization Code + PKCE probes |
| Focused tests and exact run instructions | 23 tests; `README.md` |
| Design, research, conformance, and discussion artifacts | `DESIGN-NOTES.md`, `RESEARCH-LOG.md`, `CONFORMANCE.md`, `POC-FINDINGS.md`, `COMMUNITY-DISCUSSION-POC-ADDENDUM.md` |

## Deliberately not completed

- Official extension identifier, SEP, or community submission.
- Production maisecrets or AI Gateway changes.
- Production token storage, policy engine, filesystem sandbox, DLP/NER, database, delegation, or cross-server redemption.

These are either explicit original non-goals or require community/owner decisions beyond a local feasibility prototype.
