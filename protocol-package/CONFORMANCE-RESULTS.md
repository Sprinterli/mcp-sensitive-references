# Conformance results

**Status: evidence record, experimental.** This file is not a standards conformance claim. It maps each
requirement to the evidence that exists for it on 2026-10-25.

## Test run

Command, run in the repository at commit `fe87dad` (branch `m4-local-file-sink`), with MCP Python SDK
2.3.0 and Python 3.14:

```bash
cd prototype && PYTHONPATH=src:demo:. python -m unittest discover -s tests
```

Result: **71 tests ran. 70 passed. 1 error.** The error is `test_mcp_sdk_demo`: the module does not import,
because `demo/mcp_sdk_server.py` imports `mcp.server.fastmcp`, and SDK 2.x renamed FastMCP to
`MCPServer`. The test `test_sdk_tool_preserves_structured_string_fields_without_plaintext` needs SDK 1.x.
It did not run.

| Test module | Tests | Result |
|---|---|---|
| `test_mcp_host_resolve.py` | 35 | 35 passed. Two of them run the host against a real MCP SDK 2.x server. |
| `test_mcp_host.py` | 13 | 13 passed |
| `test_sensitive_references.py` | 13 | 13 passed |
| `test_oidc_and_resolve_http.py` | 4 | 4 passed |
| `test_oauth_profile.py` | 2 | 2 passed |
| `test_reference_grammar.py` | 2 | 2 passed |
| `test_settings_schema.py` | 1 | 1 passed |
| `test_mcp_sdk_demo.py` | 1 | import error (needs SDK 1.x) |

The reference server tests were not run for this package. This package read 25 test functions in the
resolver consent module and counted 26 test functions in the module for negotiated canonical references,
at revision `e5268633f`. Several functions are parametrized, so the number of test cases is larger. The
exact number of cases is **not verified**. After the second server review, the implementer reported 58 passing
test cases in the consent module at revision `b6a46eb81`; this package did not run them.

## End-to-end runs

The implementer measured these facts on 2026-10-25 with synthetic data. This package did not repeat the
runs. It records them as reported.

**Local, over HTTP, test host against the reference server:**

| Run | Fact |
|---|---|
| E1, first run | One consent page. The file held the synthetic value once and no reference. The model-visible content kept the reference. Zero sentinel values in model-visible content. |
| E2, second run | The host used the cached token. Zero consent pages. |
| E3, forged reference | A forged reference in the template produced no file. |
| E7, second round at `b6a46eb81`, resolve endpoint from discovery | Seven scenarios. The first run, a cached run and a run after a new consent materialize as in E1. A forged reference and another user's reference in the template: the host refuses before any resolve request, no file. A withdrawn consent: one resolve request, `unauthorized`, no file. A revocation between the tool call and the write: one resolve request, `unresolvable`, no file. |

**Production, synthetic data:**

| Run | Fact |
|---|---|
| E4 | Negotiated sessions got canonical tokens and zero sentinel values. |
| E5 | Legacy sessions got no references. |
| E6 | Malformed references were refused. |

The plan of the reference server records a run of the test host against a local copy of the server
pipeline in M3 (plan section 6, M3, "Evidence"): declared and switched on gave canonical tokens and zero
sentinel hits; `--legacy` gave zero canonical tokens; switched off gave no advertisement. That run is
**not verified** by this package.

## Matrix

Legend: **S** server-side evidence (reference server test, read, not re-run). **H** host-side evidence
(prototype test, run). **E** end-to-end evidence (E1 to E6 above). "—" means no evidence of that kind.
"Not verified" means no evidence at all.

### Core (concept 0.5)

| Requirement | S | H | E |
|---|---|---|---|
| A token holds no plaintext. Equal values get unrelated ids. | Plan section 6, M3, "Evidence" (module for negotiated canonical references). Test names not checked one by one. | `test_reference_contains_no_plaintext_and_equal_values_get_unrelated_ids` | E1 (file held no reference; model content kept it) |
| The canonical grammar rejects malformed and lookalike text. | Same as above | `test_canonical_vector_is_valid`, `test_short_id_trailing_text_and_lookalike_brackets_are_not_tokens` | E6 |
| Only a negotiated session gets canonical tokens. | Plan section 6, M3, "Negotiation" | `test_without_negotiation_no_provenance_is_recorded_and_a_token_fails`, `test_unsupported_capabilities_do_not_create_trusted_provenance` | E4, E5 |
| Only negotiated, authenticated results create provenance. | Not applicable | `test_a_negotiated_result_with_canonical_tokens_passes_and_records_provenance`, `test_unobserved_forged_token_fails_closed` | E3 |
| An ambiguous issuer fails closed. | Not applicable | `test_ambiguous_issuer_fails_closed`, `test_a_token_seen_from_two_issuers_is_not_trusted`, `test_an_ambiguous_reference_is_not_sent` | — |
| Unknown, revoked and expired references fail closed. | `test_a_batch_with_one_reference_that_does_not_resolve_returns_no_value` (unknown, revoked); `test_a_replayed_mapping_body_does_not_resolve_a_revoked_reference` | `test_unknown_and_revoked_references_fail_closed`, `test_expired_reference_fails_closed`, `test_a_revoked_reference_in_a_batch_writes_nothing` | E6 (malformed only) |
| Possession of a reference is not authorization. | `test_an_agent_token_is_refused_at_the_resolve_endpoint` | `test_possession_without_resolver_authorization_fails` | — |
| No plaintext in model-visible results. | Plan section 6, M1 (ten paths) | `test_a_sentinel_value_in_the_result_fails_and_is_not_reported`, `test_a_sentinel_outside_the_text_blocks_fails_too` | E1, E4 |
| The sink materializes a whole batch or nothing. | `test_a_batch_with_one_reference_that_does_not_resolve_returns_no_value` | `test_batch_is_all_or_nothing`, `test_a_partially_invalid_batch_writes_nothing` | E3 |
| Provenance survives a host restart. | Not applicable | Not verified. The prototype keeps provenance in memory (`HOST-INTEGRATION.md`). | — |

### `oauth-resolver-1`

| Requirement | S | H | E |
|---|---|---|---|
| Discovery object in RFC 9728 metadata (SC-02) | `test_discovery_publishes_the_endpoint_and_the_profiles_while_on`, `test_every_protected_resource_document_carries_the_discovery_block_while_on` | `test_the_endpoint_and_scope_come_from_discovery` | Not verified. E1 does not say whether the host used discovery or a configured endpoint. |
| Resolve scope not in `scopes_supported` (SC-03) | `test_the_resolve_scope_stays_out_of_scopes_supported` | — | — |
| Mixed scopes get neither (SC-03) | `test_a_request_that_mixes_the_resolve_scope_with_agent_scopes_gets_neither` | `test_a_token_without_the_resolve_scope_is_refused` | — |
| Issuer = RFC 9728 `resource` (SC-01) | Not verified (P16: the server deviates from RFC 9728 section 3.3) | `test_metadata_for_another_resource_is_refused`, `test_a_configured_parent_resource_is_the_issuer` | Not verified |
| Discovered endpoint on the resource origin; no redirects (SC-04) | — | `test_a_discovered_cross_origin_endpoint_is_refused`, `test_a_redirect_from_the_resolve_endpoint_is_not_followed` | — |
| Separate client, Authorization Code + PKCE S256, `resource` | `test_an_unregistered_client_gets_no_resolver_code`. PKCE S256 enforcement: not yet tested. | `test_interactive_authorization_materializes_and_reports_no_secret` | E1 |
| `state` and RFC 9207 `iss` checks (SC-08) | — | `test_a_callback_with_another_state_is_refused`, `test_a_callback_from_another_issuer_is_refused` | — |
| Separate token class (SC-05) | `test_the_resolver_token_is_its_own_class_and_short_lived`, `test_a_resolver_token_is_refused_where_an_agent_token_is_expected`, `test_an_agent_token_is_refused_at_the_resolve_endpoint`, `test_a_resolver_token_never_reaches_the_agent_suffix_lookup` | `test_the_agent_token_is_never_sent` | — |
| One-time consent per user and client (SC-06) | `test_the_first_authorization_shows_a_consent_page_and_issues_no_code`, `test_consent_is_asked_once_per_client_then_codes_follow_without_interaction` | — | E1, E2 |
| Consent cannot be forged (SC-06) | `test_consent_cannot_be_given_without_the_users_own_answer_on_the_page`, `test_a_consent_post_without_an_origin_header_grants_nothing` | — | — |
| Consent bounds refresh and access (SC-06) | `test_a_withdrawn_or_expired_consent_stops_refresh_and_the_live_token` | — | — |
| Refresh rotation bound to the client (SC-07) | `test_refresh_rotates_and_the_old_refresh_token_is_dead`, `test_a_refresh_token_works_only_for_its_own_client` | `test_an_expired_token_is_refreshed_and_rotated` | — |
| Token cache 0600, one renewal after 401 (SC-07) | — | `test_a_cache_file_that_others_can_read_is_refused`, `test_an_expired_token_is_refreshed_once_then_the_run_fails` | E2 |
| Access token expiry enforced | `test_an_expired_resolver_token_resolves_nothing` | — | — |
| Whole-batch resolution (SC-09) | `test_a_batch_with_one_reference_that_does_not_resolve_returns_no_value` | `test_a_partially_invalid_batch_writes_nothing`, `test_an_incomplete_or_extra_batch_writes_nothing` | — |
| Batch limit 1 to 100 (SC-09) | `test_a_request_outside_the_profile_is_refused` (`too_many`, `empty`) | `test_more_than_100_references_go_in_batches_of_100` | — |
| Ineligible sink refused (SC-10) | `test_a_request_outside_the_profile_is_refused` (`sink`) | — | — |
| Error codes without values (SC-11) | `test_a_batch_with_one_reference_that_does_not_resolve_returns_no_value`, `test_removing_a_principal_from_the_allowlist_stops_a_live_token` | `test_a_revoked_reference_in_a_batch_writes_nothing` | — |
| Daily quota, 429 | `test_the_daily_quota_refuses_the_batch_that_crosses_it` | — | — |
| Resolve audit without values | Not yet tested | — | — |
| Sender-constrained tokens | Not implemented | Not implemented | — |

### `local-file-1`

| Requirement | S | H | E |
|---|---|---|---|
| Both profiles negotiated before any resolve | Not applicable | `test_without_the_negotiated_profiles_nothing_is_sent`, `test_without_advertised_profiles_the_host_does_not_resolve` | — |
| Only observed references with one trusted issuer | Not applicable | `test_an_unobserved_or_forged_reference_is_not_sent`, `test_a_reference_from_another_issuer_is_not_sent` | E3 |
| Content from host configuration | Not applicable | `test_the_template_is_configuration` | E3 |
| File holds values, no reference | Not applicable | `test_interactive_authorization_materializes_and_reports_no_secret` | E1 |
| Model-facing content keeps the reference | Not applicable | `test_interactive_authorization_materializes_and_reports_no_secret`, `test_valid_observed_reference_resolves_to_protected_file_only` | E1 |
| Failure leaves the destination unchanged | — | `test_an_unreachable_resolve_endpoint_writes_nothing` and the helper `assert_nothing_written` | E3 |
| File mode without group and other bits | Not applicable | `test_interactive_authorization_materializes_and_reports_no_secret` | — |
| Report holds no secret | Not applicable | `assert_report_clean`, `test_the_host_materializes_an_observed_reference` | E1 |
| Destination is a label, not a path (SC-10, proposed) | Not implemented | Not implemented | — |

## Gaps that this matrix shows

- No server test checks that the MCP URL and the RFC 9728 `resource` agree (P16).
- No test covers PKCE S256 enforcement at the server, the audit event, the 30-second expiry
  margin of the host, or the duplicate removal of the host.
- No end-to-end run used a second, independent server or a second, independent host.
- `test_mcp_sdk_demo` does not run with SDK 2.x.
