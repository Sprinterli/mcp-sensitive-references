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
| Real external-AS/JWKS/HTTP resolver path works | `demo/keycloak_oidc_probe.py` against local Keycloak |
| Authorization Code + PKCE token supports subject-bound resolution | `demo/keycloak_pkce_probe.py` against local Keycloak |

## Remaining before a standards proposal

- Agree the official extension identifier and precise extension-capability schema.
- Define resolver endpoint discovery and the durable resolver-token store.
- Run an interactive Authorization Code + PKCE flow with a persistent resolver client and the final resolve scope.
- Specify production audit, rate limits, output echo handling, and local sink policy.
- Obtain an official MCP SDK reference implementation after community feedback.
