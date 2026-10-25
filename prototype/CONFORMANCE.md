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

## Remaining before a standards proposal

- Agree the official extension identifier and precise extension-capability schema.
- Define resolver endpoint discovery and the durable resolver-token store (`M4-FINDINGS.md` F1, F2, F6).
- Define consent, the destination field, error codes, and batch limits (`M4-FINDINGS.md` F5, F7, F8, F9).
- Run an interactive Authorization Code + PKCE flow with a persistent resolver client and the final resolve scope.
- Specify production audit, rate limits, output echo handling, and local sink policy.
- Obtain an official MCP SDK reference implementation after community feedback.
