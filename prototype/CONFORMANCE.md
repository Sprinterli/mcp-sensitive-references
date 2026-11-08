# PoC conformance matrix

This matrix records prototype evidence only. It is not a standards conformance claim.

| Property | Evidence |
|---|---|
| Token has no protected plaintext; equal values get unrelated IDs | `test_reference_contains_no_plaintext_and_equal_values_get_unrelated_ids` |
| Canonical grammar rejects malformed/lookalike text | `test_reference_grammar.py` |
| Ordinary string schemas survive an MCP SDK tool call | `test_sdk_tool_preserves_structured_string_fields_without_plaintext` |
| Unsupported peers cannot enable provenance; profiles require a common version | capability negotiation tests |
| Only negotiated trusted results gain issuer provenance | `test_unobserved_forged_token_fails_closed` and `ProvenanceStore.observe_mcp_result` |
| Ambiguous issuer identity fails closed | `test_ambiguous_issuer_fails_closed` |
| Unknown, wrong-issuer, revoked, and expired references fail closed | `test_wrong_issuer_does_not_resolve`, `test_unknown_and_revoked_references_fail_closed`, `test_expired_reference_fails_closed` |
| Reference possession is not resolver authorization | `test_possession_without_resolver_authorization_fails` |
| Batch materialization is all-or-nothing | `test_batch_is_all_or_nothing`; HTTP adapter rejects incomplete mappings |
| Local file gets plaintext while model-facing result retains token | `test_valid_observed_reference_resolves_to_protected_file_only` |
| Known downstream plaintext echoes can be returned as the original token | `test_downstream_echo_redaction_uses_only_values_resolved_in_this_operation` |
| OAuth claims bind resolver to resource, subject, scope, and expiry | `test_oauth_profile.py` |
| PKCE is S256, state-checked, and resource-bound | `test_oidc_and_resolve_http.py`; `keycloak_pkce_probe.py` |
| Resource endpoint rejects an invalid mixed batch without plaintext response | `test_resolve_endpoint_is_subject_bound_and_has_no_partial_success` |
| A host checks negotiation, provenance and canonical form on real MCP results | `demo/mcp_host.py`; checks in `tests/test_mcp_host.py` |
| A host that declared nothing sees no canonical token | `demo/mcp_host.py --legacy`; `test_without_negotiation_no_provenance_is_recorded_and_a_token_fails` |
| A host materializes only with both profiles negotiated | `test_without_the_negotiated_profiles_nothing_is_sent`; `test_without_advertised_profiles_the_host_does_not_resolve` (real MCP SDK 2.x server) |
| A host gets a resolver token by DCR, Authorization Code + PKCE S256, `resource`, resolve scope only, loopback redirect | `test_interactive_authorization_materializes_and_reports_no_secret`; `test_the_host_materializes_an_observed_reference` (end to end) |
| The callback `state` and `iss` and the granted scope are checked | `test_a_callback_with_another_state_is_refused`, `test_a_callback_from_another_issuer_is_refused`, `test_a_token_without_the_resolve_scope_is_refused` |
| The resolver token is cached with mode 0600, refreshed with rotation, renewed once after a 401 | `test_a_cached_token_is_used_without_a_new_authorization`, `test_an_expired_token_is_refreshed_and_rotated`, `test_an_expired_token_is_refreshed_once_then_the_run_fails`, `test_a_cache_file_that_others_can_read_is_refused` |
| The agent token never reaches the resolve endpoint | `test_the_agent_token_is_never_sent` |
| No token, an invalid token, another user, a revoked or unknown reference, or an incomplete or extra batch writes nothing | `test_without_a_token_and_without_interaction_nothing_is_written`, `test_an_invalid_token_writes_nothing`, `test_a_reference_of_another_user_writes_nothing`, `test_a_revoked_reference_in_a_batch_writes_nothing`, `test_a_partially_invalid_batch_writes_nothing`, `test_an_incomplete_or_extra_batch_writes_nothing` |
| An ambiguous, unobserved, forged, or other-issuer reference is not sent | `test_an_ambiguous_reference_is_not_sent`, `test_an_unobserved_or_forged_reference_is_not_sent`, `test_a_reference_from_another_issuer_is_not_sent` |
| Metadata for another resource, a cross-origin discovered endpoint, an insecure endpoint, and a redirect are refused | `test_metadata_for_another_resource_is_refused`, `test_a_discovered_cross_origin_endpoint_is_refused`, `test_an_insecure_resolve_endpoint_is_refused`, `test_a_redirect_from_the_resolve_endpoint_is_not_followed` |
| The materialization report holds no reference, value or credential | `assert_report_clean` in `tests/test_mcp_host_resolve.py` |
| Real external-AS/JWKS/HTTP resolver path works | `demo/keycloak_oidc_probe.py` against local Keycloak |
| Authorization Code + PKCE token supports subject-bound resolution | `demo/keycloak_pkce_probe.py` against local Keycloak |

## Concept 0.7

The prototype implements the rules of Concept 0.7 below. The issuer is `src/sensitive_references/issuer_server.py`
(demo level: in memory, fixture accounts, no identity provider). The host is `demo/mcp_host.py` with
`resolver_client.py`, `process_sink.py` and `display_sink.py`. The tests are `tests/test_issuer_server.py` (issuer)
and `tests/test_concept_07_host.py` (host); round 10 of `tests/tools/mutation_probe.py` disables each guard once.

| Rule (Concept 0.7) | Evidence |
|---|---|
| Discovery names `sinks` with the scope set of each sink profile, `process_scope` and `display_scope`; the prototype publishes `process-1` only (RESOLVER-PROFILE.md, section 4) | `test_discovery_names_each_sink_with_its_scope_set_and_the_two_sink_scopes`, `test_a_server_without_a_sink_names_no_scope_for_it` |
| The host refuses an object without valid `sinks`, with a sink scope that `sinks` does not name, or with a bad `max_references` | `test_an_object_without_sinks_or_with_a_bad_member_is_refused`, `test_a_sink_scope_member_must_be_the_scope_that_sinks_names`, `test_max_references_must_be_an_integer_of_100_or_more`, `test_a_negotiated_sink_without_a_valid_sinks_member_stops_the_host` |
| The host takes the scope set from `sinks` and asks for the scopes of every sink of the run in one authorization | `test_the_host_takes_the_scope_set_from_sinks`, `test_one_authorization_serves_a_file_a_command_and_the_screen`, `test_a_file_only_run_asks_for_the_resolve_scope_only_and_cannot_reach_a_command`, `test_the_host_fills_a_file_runs_a_command_and_reveals_on_a_click_with_one_consent` (real MCP SDK 2.x server) |
| Scope combinations: the resolve scope plus offered sink scopes plus `openid`, else `invalid_scope` and no code (section 5.2) | `ScopeTests` in `test_issuer_server.py` |
| A missing sink scope: `403 insufficient_scope` before any lookup, no value, no audit event; header and body name the scope set and an `error_description` (section 5.4) | `test_a_file_only_token_gets_insufficient_scope_before_any_lookup_without_a_value_or_an_audit_event`, `test_a_display_token_does_not_resolve_into_a_command_but_into_a_file`; host side: `test_a_token_without_the_sink_scope_is_not_sent` |
| A refresh keeps the granted set and adds no scope (section 5.3) | `test_a_refresh_keeps_the_granted_set`, `test_a_refresh_adds_no_scope`, `test_a_refresh_token_rotates_and_is_bound_to_its_client` |
| Consent at every authorization request; the page names the account with "Use another account", the client, the loopback host and port, the time, the resource and one line per sink scope (section 10) | `ConsentTests` in `test_issuer_server.py`; `test_each_authorization_shows_the_consent_page_again`, `test_use_another_account_on_the_page_signs_in_the_other_account` |
| References per person; another account gets `409 unresolvable` with the reason `unknown` (section 12.2) | `test_a_reference_of_another_person_is_unresolvable_with_the_reason_unknown`, `test_a_reference_of_another_account_is_unknown_and_nothing_is_written` |
| `account_hint` in token and refresh answers (section 11.2) | `test_the_account_hint_keeps_at_most_three_and_at_most_half_of_the_local_part_and_the_whole_domain`, `test_token_and_refresh_answers_carry_the_hint_and_not_the_address` |
| No value without its audit event; `503 audit_unavailable` (section 15) | `test_no_value_leaves_without_its_audit_event`, `test_the_audit_store_down_releases_no_value` |
| Revocation per device by the person or an administrator; an epoch per principal and client (section 10.4) | `DeviceTests` in `test_issuer_server.py` |
| `process-1`: destination is the program name; resolve only when the command reads; a failed resolve stops the command; output masked before the model, also on failure paths (PROCESS-PROFILE.md) | `ProcessSinkTests` in `test_concept_07_host.py` (POSIX) |
| `display-1`: one reference per request to `screen`, only on an explicit action, never into the transcript; copy only after a second action (DISPLAY-PROFILE.md) | `DisplaySinkTests` in `test_concept_07_host.py`; `test_a_display_request_needs_the_screen_and_exactly_one_reference` |

Demo level: `process-1` masks clear text, percent-encoding and base64 only, and runs on POSIX only; there is no
sandbox. `display-1` draws on the terminal. The issuer has no persistence and no identity provider.

## Remaining before a standards proposal

- Agree the official extension identifier and precise extension-capability schema.
- Define resolver endpoint discovery and the durable resolver-token store (`M4-FINDINGS.md` F1, F2, F6).
- Define consent, the destination field, error codes, and batch limits (`M4-FINDINGS.md` F5, F7, F8, F9).
- Run an interactive Authorization Code + PKCE flow with a persistent resolver client and the final resolve scope.
- Specify production audit, rate limits, output echo handling, and local sink policy.
- Obtain an official MCP SDK reference implementation after community feedback.
