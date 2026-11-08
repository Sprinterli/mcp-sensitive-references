# Conformance results

**Status: evidence record, experimental.** This file is not a standards conformance claim. It maps each
requirement to the evidence that exists for it on 2026-10-27, and adds the evidence of Concept 0.7 of
2026-11-08 (section "Concept 0.7"). Run E12 of 2026-10-27 is recorded in
[IMPLEMENTATION-EVIDENCE.md](../IMPLEMENTATION-EVIDENCE.md). The reference server is MCPGate, and the second
host is maisecrets ([README.md](README.md#implementations)).

## Test run

**Concept 0.7 test run (2026-11-08).** Python 3.14.8 on macOS, MCP Python SDK (`mcp`) 2.3.0,
`PYTHONPATH=src`, repository commit `65f17e5` (branch `concept-0.7`). At this commit the prototype
implements Concept 0.7 (`prototype/README.md`, section "Concept 0.7"):

```bash
cd prototype && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m pytest -q -p no:cacheprovider
# 212 passed, 393 subtests passed
cd prototype && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m unittest discover -s tests
# Ran 212 tests, OK
```

The 79 new tests are `test_issuer_server.py` (38, the prototype issuer) and `test_concept_07_host.py` (41,
the host: discovery with `sinks`, the scope choice, `process-1`, `display-1`, and end-to-end runs against
the prototype issuer, one of them through `mcp_host.main` and a real MCP SDK 2.x server). The other 133
tests are the tests of the run below; `FakeServer` of `test_mcp_host_resolve.py` now publishes `sinks`.
The commits after `65f17e5` change only documentation and, in commit `85f99b3`, two mutation texts of the
probe (no code and no test).

**Supported, tested configuration (2026-10-27).** Python 3.14.8, MCP Python SDK (`mcp`) 2.3.0,
`PYTHONPATH=src`, repository commit `6cdd658` (branch `m7-consolidation`). This is "the tested
commit" of the whole package. The commits after it change only documentation
(`protocol-package/` and `prototype/README.md`), no code and no test.
Commands and results:

```bash
cd prototype && PYTHONPATH=src python -m pytest -q -p no:cacheprovider
# 133 passed, 310 subtests passed
cd prototype && PYTHONPATH=src python -m unittest discover -s tests
# Ran 133 tests, OK
```

`demo/mcp_sdk_server.py` imports `MCPServer` (SDK 2.x) and falls back to `FastMCP` (SDK 1.x). Its test reads
both result shapes. **SDK 1.x was not tested in this run.** Only SDK 2.3.0 is a tested configuration.

| Test module | Tests | Result |
|---|---|---|
| `test_mcp_host_resolve.py` | 97 | 97 passed. Five of them run the host against a real MCP SDK 2.x server. |
| `test_mcp_host.py` | 13 | 13 passed |
| `test_sensitive_references.py` | 13 | 13 passed |
| `test_oidc_and_resolve_http.py` | 4 | 4 passed |
| `test_oauth_profile.py` | 2 | 2 passed |
| `test_reference_grammar.py` | 2 | 2 passed |
| `test_settings_schema.py` | 1 | 1 passed |
| `test_mcp_sdk_demo.py` | 1 | 1 passed (SDK 2.x path) |

**Earlier runs, for the record.** On 2026-10-25, at commit `fe87dad` (branch `m4-local-file-sink`) with
SDK 2.3.0, 70 of 71 tests passed. `test_mcp_sdk_demo` did not import, because the module imported
`mcp.server.fastmcp` only. Commit `dd7afe2` fixed this, and on 2026-10-26 71 of 71 tests passed at that
commit. Commit `89f6881` added 17 host tests (SC-01, SC-02, SC-08): 88 passed, 51 subtests passed. The
commit `8394a02` added 12 host tests after the second review round (SC-01 discovery order and URL
construction, fail closed without metadata, SC-04 for a configured endpoint, D10): 100 passed, 71
subtests passed. The commit `fd7a9f2` added 12 host tests after the third review round (the fetch
policy D11, a stop without the discovery object, the labels of a non-conformant run, a challenge URL
without a document, the RFC 8414 well-known URL): 112 passed, 124 subtests passed. The tested commit above
adds 10 host tests after the fourth review round (the fetch policy without an automatic local exception,
the address cases, no redirect and no proxy for each client, the default configuration) and removes one
(the old local exception): 121 passed, 164 subtests passed, at commit `c5e1eba`. The commits after it add
4 host tests after the fifth review round (the connection to the checked address, a request without a
checked address, the TLS server name, the most specific registry entry) and, after the sixth round, one
test of the TLS context of the real opener and, after the seventh round, three tests with a real TLS server
and a test CA: 129 passed, 175 subtests passed, at commit `00dce0b`. The tested commit above adds 3
host tests after the eighth round (each checked address in turn, a server on `::1` only; the timeout of
each connection attempt; three IANA entries that the Python tables do not follow): 132 passed, 181
subtests passed, at commit `ee7da0a`. The tested commit above adds 1 host test after the ninth round
(every entry of a dated copy of the IANA registries, with the Dummy IPv6 Prefix 100:0:0:1::/64):
133 passed, 310 subtests passed.

**Mutation check of Concept 0.7 (2026-11-08).** Round 10 of `prototype/tests/tools/mutation_probe.py`
(`MUTATIONS_07`) disables each guard of the Concept 0.7 rules once and runs the test module of that
guard: 30 guards of the prototype issuer (`test_issuer_server.py`) and 30 guards of the host
(`test_concept_07_host.py`). 60 of 60 failed at least one test. A first run left 5 mutants alive (a
nonce that is not single-use, two `sinks` checks, the `sinks` member of a negotiated profile, one session
for a run). Four tests were made stronger. The fifth mutant changed nothing that a test can observe (the run
still used its first session), so it was replaced by a mutant that gives each sink a new session. The
second run killed all 60. The whole probe ran on 2026-11-08: 114 mutants (54 of rounds 2 to 9 and 60 of round 10). The first run
killed 112 and reported 2 round-3 mutants as stale, because the text of `materialize` changed; commit
`85f99b3` moved them to the current text, and both were then killed. Result: 114 of 114.

**Mutation check.** `prototype/tests/tools/mutation_probe.py` copies `prototype/` into a directory
outside the repository, disables one guard per run, and runs `test_mcp_host_resolve.py` there. It does not
write into the repository. At the tested commit it ran 54 mutants: the 13 guards of the second round and
12 guards of the third round on the current text, 18 guards of the fourth round, 4 guards of the
fifth round (the pinning mutants, written again for the code of the eighth round), 1 guard each of the
sixth and seventh rounds, 4 guards of the eighth round and 1 guard of the ninth round. 54 of 54 failed at least one test (2026-10-27, with the configuration above). The fourth round removed two
mutants of the third round (the local exception and the RFC 4193 range), because the code that they
changed no longer exists; the round-4 mutants test the replacement. One guard has no mutant: the host passes the policy that
it made at connection to `materialize`. A new policy gives the same result in the tests, because no
test changes DNS between the connection and `materialize`. **Not verified by a test.** The module docstring of `test_mcp_host_resolve.py` names each guard and the
test that failed. The earlier figure of the second round (13 of 13, from a script outside the repository)
is reported; the repository script repeats those mutations on the current text.

The reference server tests were not run for this package. This package read 25 test functions in the
resolver consent module and counted 26 test functions in the module for negotiated canonical references,
at revision R1. Several functions are parametrized, so the number of test cases is larger. The exact
number of cases is **not verified**. After the second server review, the implementer reported 58 passing
test cases in the consent module at revision R2; this package did not run them. R1 and R2 are labels for
non-public revisions ([README.md](README.md#sources-and-versions)).

## End-to-end runs

The implementer measured these facts on 2026-10-25 with synthetic data. This package did not repeat the
runs. It records them as reported.

**Local, over HTTP, test host against the reference server:**

| Run | Fact |
|---|---|
| E1, first run | One consent page. The file held the synthetic value once and no reference. The model-visible content kept the reference. Zero sentinel values in model-visible content. |
| E2, second run | The host used the cached token. Zero consent pages. |
| E3, forged reference | A forged reference in the template produced no file. |
| E7, second round at revision R2, resolve endpoint from discovery | Seven scenarios. The first run, a cached run and a run after a new consent materialize as in E1. A forged reference and another user's reference in the template: the host refuses before any resolve request, no file. A withdrawn consent: one resolve request, `unauthorized`, no file. A revocation between the tool call and the write: one resolve request, `unresolvable`, no file. |

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

## Production runs of 2026-10-26

**Status: observed (one operator run, not independently reproduced).** The operator ran the test host
against the reference server in production with synthetic data, on 2026-10-26. This package did not
repeat the runs. These observations are separate from "verified by tests in this repository". They do not
upgrade any row of the matrix to "verified".

| Run | Host options | Fact |
|---|---|---|
| E8, run 1 | interactive | Interactive consent on the consent page. The host materialized the file. Zero sentinel values in model-visible content. |
| E9, run 2 | `--no-interactive` | The token came from the cache. The host materialized the file. Zero sentinel values in model-visible content. |
| E10, run 3 | after the access token expired | The host renewed the token through the refresh token, without a consent page. The host materialized the file. Zero sentinel values in model-visible content. |

All three runs used the host option `--resource` with the base URL of the reference server, because the
reference server publishes that base URL as its `resource` (P16). Under SC-01 a host MUST NOT use such
metadata. So E8 to E10 show the profile flow under the known deviation of the reference server. They are
no evidence that the server or the host conforms to SC-01.

E11 (observed on 2026-10-26, one operator run, not independently reproduced). The test host at commit
`8394a02` (before the third review round), without `--resource`, against the same server: the host read the metadata that the
`resource_metadata` parameter of the 401 answer names. That document has the base URL as `resource`. The
host stopped with `wrong_issuer` and resolved nothing. This is the fail-closed result that SC-01 requires.
It also shows that the reference server does not yet do step 2 of the known deviation note in SC-01.

The same runs gave six lessons for implementers. They are in
[IMPLEMENTATION-GUIDE.md](IMPLEMENTATION-GUIDE.md#lessons-from-a-production-run-2026-10-26). SPEC-CHANGES.md,
SC-20 makes three of them normative.

## Matrix

Legend: **S** server-side evidence (reference server test, read, not re-run). **H** host-side evidence
(prototype test, run). **E** end-to-end evidence (E1 to E7 as reported, E8 to E10 observed in one operator
run). "—" means no evidence of that kind. "Not verified" means no evidence at all. A cell that cites E8 to
E10 only says "observed": it is not a verification.

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
| No plaintext in model-visible results. | Plan section 6, M1 (ten paths) | `test_a_sentinel_value_in_the_result_fails_and_is_not_reported`, `test_a_sentinel_outside_the_text_blocks_fails_too` | E1, E4; observed: E8, E9, E10 |
| The sink materializes a whole batch or nothing. | `test_a_batch_with_one_reference_that_does_not_resolve_returns_no_value` | `test_batch_is_all_or_nothing`, `test_a_partially_invalid_batch_writes_nothing` | E3 |
| Provenance survives a host restart. | Not applicable | Not verified. The prototype keeps provenance in memory (`HOST-INTEGRATION.md`). | — |

### `oauth-resolver-1`

| Requirement | S | H | E |
|---|---|---|---|
| Discovery object in RFC 9728 metadata (SC-02) | `test_discovery_publishes_the_endpoint_and_the_profiles_while_on`, `test_every_protected_resource_document_carries_the_discovery_block_while_on` | `test_the_endpoint_and_scope_come_from_discovery`; end to end with a real MCP SDK server: `test_the_host_materializes_an_observed_reference` | Not verified. E1 does not say whether the host used discovery or a configured endpoint. |
| An incomplete discovery object stops the host (SC-02) | Not applicable | `test_a_discovery_object_without_a_mandatory_member_is_refused`, `test_a_discovery_object_with_a_malformed_member_is_refused`, `test_a_discovery_object_without_the_negotiated_profiles_is_refused`, `test_a_configured_endpoint_does_not_excuse_a_bad_discovery_object` | — |
| Metadata without the discovery object stops the host; configuration mode only after an operator statement, and labelled (SC-02) | Not applicable | `test_metadata_without_a_discovery_object_stops_the_host`, `test_without_a_discovery_object_configuration_mode_needs_the_option_and_is_not_conformant`, `test_a_conformant_run_has_no_deviation`, `test_a_configured_parent_resource_is_the_issuer` (P16 label) | — |
| Discovery only through the two RFC 9728 mechanisms, the challenge first (SC-01) | Not applicable | `test_metadata_named_in_the_www_authenticate_challenge_is_used`, `test_the_challenge_comes_before_the_well_known_url`, `test_a_parent_resource_gets_no_challenge_probe_of_the_mcp_url`, `test_challenge_metadata_for_another_resource_is_refused`, `test_an_insecure_challenge_metadata_url_is_refused`, `test_root_metadata_is_not_a_fallback_for_a_resource_with_a_path` | — |
| The well-known URL and the issuer keep the query and a trailing slash (SC-01) | Not applicable | `test_the_well_known_url_follows_rfc_9728_section_3_1`, `test_a_resource_with_a_query_or_a_trailing_slash_keeps_it`, `test_the_issuer_string_is_kept_as_given`, `test_a_url_with_user_information_or_a_fragment_is_no_issuer`, `test_a_resource_with_a_fragment_is_refused` | — |
| No metadata or unreachable metadata: no resolution without an operator statement (SC-01) | Not applicable | `test_without_metadata_the_host_stops_unless_the_operator_says_there_is_none`, `test_unreachable_metadata_fails_closed`, `test_a_challenge_url_without_a_document_is_not_a_server_without_metadata` | — |
| Fetch policy: no request to a non-public target (SC-01, D11, RFC 9728 section 7.7) | Not applicable | `FetchPolicyTests` (14 tests): loopback, private, IPv6 unique-local, link-local, mixed and unresolvable targets at the challenge, the authorization server, its endpoints and the resolve endpoint; the address cases of the definition with IPv4-mapped, IPv4-compatible, NAT64 and 6to4 addresses; local mode only with the operator option, not with mixed DNS records, only for the MCP origin and configured origins, never for 169.254.169.254, and with the DNS answer kept from the connection. `test_the_default_configuration_has_no_local_mode`, `test_without_the_local_option_a_loopback_server_gets_no_request`, `test_the_most_specific_registry_entry_decides`, `test_the_registry_entries_that_the_python_tables_do_not_follow`, `test_every_entry_of_the_iana_registries` (all 51 entries of the IANA registry snapshot of 2026-10-27). DNS rebinding: `test_the_request_connects_to_the_checked_address`, `test_a_request_without_a_checked_address_is_refused`, `test_the_tls_server_name_is_the_host_name_of_the_url`, `test_the_real_opener_verifies_certificates_and_host_names`, `PinnedTlsTests` (3 tests, real TLS with a test CA). The browser path is not pinned (TM-11). | — |
| No redirect and no environment proxy for each request of the discovery and the authorization (SC-01, SC-04) | Not applicable | `NoRedirectNoProxyTests`: `test_no_client_follows_a_redirect` (real loopback servers, 302 for metadata, challenge, authorization server metadata, registration, token and resolve endpoint), `test_no_client_uses_a_proxy_from_the_environment`; `test_a_redirect_from_the_resolve_endpoint_is_not_followed` | — |
| Resolve scope not in `scopes_supported` (SC-03) | `test_the_resolve_scope_stays_out_of_scopes_supported` | — | — |
| Mixed scopes get neither (SC-03) | `test_a_request_that_mixes_the_resolve_scope_with_agent_scopes_gets_neither` | `test_a_token_without_the_resolve_scope_is_refused` | — |
| Issuer = RFC 9728 `resource`, identical to the MCP URL (SC-01) | **Not conformant** (known deviation P16, see below) | Default path, exact string: `test_metadata_for_another_resource_is_refused`, `test_a_near_miss_of_the_issuer_is_refused` (trailing slash, parent path, host case, explicit port 443, scheme case, percent-encoding), `test_an_issuer_with_upper_case_is_not_lowered_to_match`, `test_identical_metadata_is_accepted` (also an upper-case issuer with identical metadata), `test_the_issuer_string_is_kept_as_given` | Not verified |
| Resolve endpoint, discovered or configured, on the resource origin; no redirects (SC-04) | — | `test_a_discovered_cross_origin_endpoint_is_refused`, `test_a_configured_cross_origin_endpoint_is_refused`, `test_a_redirect_from_the_resolve_endpoint_is_not_followed` | — |
| Authorization server metadata: exact `issuer` and S256 listed (D10) | Not applicable | `test_authorization_server_metadata_for_another_issuer_is_refused`, `test_authorization_server_metadata_without_s256_is_refused`; the RFC 8414 well-known URL without a terminating slash: `test_rfc_8414_removes_a_terminating_slash_of_the_issuer` | — |
| Separate client, Authorization Code + PKCE S256, `resource` | `test_an_unregistered_client_gets_no_resolver_code`. PKCE S256 enforcement: not yet tested. | `test_interactive_authorization_materializes_and_reports_no_secret` | E1; observed: E8 |
| `state` and RFC 9207 `iss` checks (SC-08) | — | `test_a_callback_with_another_state_is_refused`, `test_a_callback_from_another_issuer_is_refused`, `test_a_callback_without_iss_is_refused_when_the_server_advertises_iss`, `test_a_callback_without_iss_is_accepted_when_the_server_does_not_advertise_iss`, `test_a_wrong_iss_is_refused_also_when_the_server_does_not_advertise_iss` | — |
| Separate token class (SC-05) | `test_the_resolver_token_is_its_own_class_and_short_lived`, `test_a_resolver_token_is_refused_where_an_agent_token_is_expected`, `test_an_agent_token_is_refused_at_the_resolve_endpoint`, `test_a_resolver_token_never_reaches_the_agent_suffix_lookup` | `test_the_agent_token_is_never_sent` | — |
| A consent page at every authorization request (SC-06, Concept 0.7) | `test_the_first_authorization_shows_a_consent_page_and_issues_no_code`; (R3) `test_consent_is_asked_on_every_authorization_with_the_same_neutral_text`, `test_a_second_authorization_with_a_live_consent_returns_the_page_and_no_code` | — | E1; observed: E8 (one consent). E2, E9 and E10 started no authorization request (cache and refresh). |
| Consent cannot be forged (SC-06) | `test_consent_cannot_be_given_without_the_users_own_answer_on_the_page`, `test_a_consent_post_without_an_origin_header_grants_nothing` | — | — |
| The page names the account with a switch, the client, the loopback host and port, and each sink scope (SC-06, Concept 0.7) | (R3) see "Concept 0.7" below | Not applicable | — |
| The stored approval is bound to resource and scope set; the page names the time and the resource (SC-06) | Not verified | Not applicable | — |
| Consent bounds refresh and access (SC-06) | `test_a_withdrawn_or_expired_consent_stops_refresh_and_the_live_token` | — | — |
| Refresh rotation bound to the client (SC-07) | `test_refresh_rotates_and_the_old_refresh_token_is_dead`, `test_a_refresh_token_works_only_for_its_own_client` | `test_an_expired_token_is_refreshed_and_rotated` | Observed: E10 (renewal through refresh; rotation not observed) |
| Token cache 0600, one renewal after 401 (SC-07) | — | `test_a_cache_file_that_others_can_read_is_refused`, `test_an_expired_token_is_refreshed_once_then_the_run_fails` | E2; observed: E9 (token from the cache) |
| Access token expiry enforced | `test_an_expired_resolver_token_resolves_nothing` | — | — |
| Whole-batch resolution (SC-09) | `test_a_batch_with_one_reference_that_does_not_resolve_returns_no_value` | `test_a_partially_invalid_batch_writes_nothing`, `test_an_incomplete_or_extra_batch_writes_nothing` | — |
| Batch limit 1 to the effective limit, 100 without `max_references` (SC-09) | `test_a_request_outside_the_profile_is_refused` (`too_many`, `empty`) | `test_more_than_100_references_go_in_batches_of_100` | — |
| Ineligible sink refused (SC-10) | `test_a_request_outside_the_profile_is_refused` (`sink`) | — | — |
| `structuredContent` schema of a refused tool call (SC-12) | Not verified | Not implemented (the host does not check the schema) | — |
| Error codes without values (SC-11) | `test_a_batch_with_one_reference_that_does_not_resolve_returns_no_value`, `test_removing_a_principal_from_the_allowlist_stops_a_live_token` | The fake server uses the SC-11 codes for 400, 401, 409 and 413. `test_a_revoked_reference_in_a_batch_writes_nothing`, `test_a_reference_of_another_user_writes_nothing` (`unresolvable`; the fake server sends the reason `unknown`, the host does not report reasons, and the test does not assert it), `test_an_invalid_token_writes_nothing` (`401 invalid_token`; the host reports its own reason `unauthorized`). The fake server does not play 403 or 429. | — |
| Daily quota, 429 | `test_the_daily_quota_refuses_the_batch_that_crosses_it` (R2) | — | — |
| Resolve audit without values | Not yet tested | — | — |
| `WWW-Authenticate` on a 401 of the resolve endpoint (SC-11) | Not verified | Not applicable (the fake server does not send it) | — |
| Sender-constrained tokens | Not implemented | Not implemented | — |

### `local-file-1`

| Requirement | S | H | E |
|---|---|---|---|
| Both profiles negotiated before any resolve | Not applicable | `test_without_the_negotiated_profiles_nothing_is_sent`, `test_without_advertised_profiles_the_host_does_not_resolve` | — |
| Only observed references with one trusted issuer | Not applicable | `test_an_unobserved_or_forged_reference_is_not_sent`, `test_a_reference_from_another_issuer_is_not_sent` | E3 |
| Content from host configuration | Not applicable | `test_the_template_is_configuration` | E3 |
| File holds values, no reference | Not applicable | `test_interactive_authorization_materializes_and_reports_no_secret` | E1; observed: E8, E9, E10 (materialized) |
| Model-facing content keeps the reference | Not applicable | `test_interactive_authorization_materializes_and_reports_no_secret`, `test_valid_observed_reference_resolves_to_protected_file_only` | E1 |
| Failure leaves the destination unchanged | — | `test_an_unreachable_resolve_endpoint_writes_nothing` and the helper `assert_nothing_written` | E3 |
| File mode without group and other bits | Not applicable | `test_interactive_authorization_materializes_and_reports_no_secret` | — |
| Report holds no secret | Not applicable | `assert_report_clean`, `test_the_host_materializes_an_observed_reference` | E1 |
| Destination is a label, not a path (SC-10, proposed) | Not implemented | Not implemented | — |

## Concept 0.7

**Server tests of revision R3.** This package read the names and the assertions of the reference server
tests below at revision R3 ([README.md](README.md#sources-and-versions)). It did not run them. The pipeline
of the release tag of R3 does not run the unit tests, so this package has no run record of them. A cell
marked "(R4)" cites a test of revision R4, read at the release tag of 2.0.3830 and not run.

**Second host.** The second host is the coding-agent plugin that IMPLEMENTATION-EVIDENCE.md names, at
release 0.9.1. This package read its source and its test names. It did not run its tests.

| Requirement | S (R3) | Second host | E | Prototype (offline, 2026-11-08) |
|---|---|---|---|---|
| A sink scope per sink profile; `sinks` in discovery (SC-21) | `test_discovery_and_server_settings_name_exactly_the_three_sinks`, `test_discovery_and_server_settings_list_both_sinks_with_their_scopes`, `test_discovery_and_server_settings_list_the_display_sink_with_its_scopes` | Reads `process_scope` and `display_scope`, not `sinks` | — | Issuer: `test_discovery_names_each_sink_with_its_scope_set_and_the_two_sink_scopes`. Host: `test_an_object_without_sinks_or_with_a_bad_member_is_refused`, `test_the_host_takes_the_scope_set_from_sinks` |
| Resolve scope plus sink scopes in one request; a sink scope alone or with agent scopes is `invalid_scope` (SC-21) | `test_the_process_scope_alone_or_with_agent_scopes_is_refused`, `test_the_display_scope_alone_or_with_agent_scopes_is_refused`, `test_a_request_that_mixes_the_resolve_scope_with_agent_scopes_gets_neither` | `test_the_process_scope_is_asked_for_on_top_where_command_output_is_masked` | — | `ScopeTests`; host: `test_one_authorization_serves_a_file_a_command_and_the_screen` |
| A missing sink scope: `403 insufficient_scope` before any lookup, no value, no audit row; header and body name the scope set and an `error_description` (SC-21) | `test_a_token_without_the_display_scope_gets_insufficient_scope_before_any_lookup`, `test_a_file_only_token_gets_insufficient_scope_for_a_process_without_a_value_or_a_row` | `test_a_login_without_the_display_scope_names_the_reason`, `test_a_login_without_commands_names_the_reason_and_runs_nothing` | — | `test_a_file_only_token_gets_insufficient_scope_before_any_lookup_without_a_value_or_an_audit_event` |
| A refresh keeps the granted set (SC-21) | `test_the_process_scope_survives_a_refresh_and_a_file_grant_stays_file_only`, `test_the_display_scope_survives_a_refresh` | — | — | `test_a_refresh_keeps_the_granted_set`, `test_a_refresh_adds_no_scope` |
| `process-1` (SC-22) | PROFILE-process-1.md, PR2 to PR20; the identifier: (R4) `test_discovery_names_the_process_sink_process_1_and_not_the_former_name`, `test_a_process_resolve_is_audited_as_process_1` | PROFILE-process-1.md. Release 0.9.1 asks for the identifier of R3 | Not recorded | Demo level, POSIX: `ProcessSinkTests` |
| `display-1` (SC-23) | PROFILE-display-1.md, DS2 to DS21 | PROFILE-display-1.md | Observed: E13 | Demo level, terminal: `DisplaySinkTests` |
| The consent page names the account, offers a switch, names the client and the loopback host and port, and each sink scope (SC-06) | `test_the_consent_page_names_the_signed_in_account_and_no_other`, `test_the_consent_page_offers_to_use_another_account_through_a_same_origin_form`, `test_use_another_account_signs_out_and_returns_to_the_same_authorize_request`, `test_the_switch_keeps_the_scopes_the_page_asked_for`, `test_the_other_account_gets_its_own_consent_page_for_the_same_request`, `test_a_second_authorization_with_a_live_consent_returns_the_page_and_no_code` | Not applicable | — | `ConsentTests` |
| References per principal (account); another account gets `unknown` (SC-24) | `test_a_reference_of_another_account_writes_a_refusal_line_with_counts_and_hashes_only` | Not applicable | Observed: E13 | `test_a_reference_of_another_person_is_unresolvable_with_the_reason_unknown` |
| `account_hint` in token and refresh answers (SC-24) | `test_the_account_hint_keeps_a_few_first_characters_and_the_whole_domain`, `test_the_token_answer_carries_the_masked_account_and_not_the_address`, `test_the_refresh_answer_carries_the_masked_account_too` | Not implemented | — | `test_token_and_refresh_answers_carry_the_hint_and_not_the_address` |
| No value without its audit row; `503 audit_unavailable` (SC-25) | `test_no_value_leaves_when_its_audit_row_cannot_be_written` | — | — | `test_no_value_leaves_without_its_audit_event` |
| Revocation per device, by the person and by an administrator; epoch per principal and client (SC-26) | PROFILE-oauth-resolver-1.md, V1 to V7 | — | — | `DeviceTests` |
| Every person with an account may use the resolver; a block list; no service account (A7) | `test_a_member_and_a_guest_without_a_block_sign_in_and_resolve`, `test_a_blocked_person_gets_access_denied_without_a_consent_page`, `test_a_service_account_gets_access_denied_without_a_consent_page` | — | — | Not implemented (fixture accounts and a block list only) |
| `form-action` names the loopback origin of the request; `[::1]` is no resolver redirect (SC-20) | `test_the_consent_page_lets_its_form_redirect_to_this_loopback_client_and_nowhere_else`, `test_a_redirect_uri_the_consent_policy_cannot_name_is_no_resolver_redirect`, `test_the_consent_policy_names_the_origin_rebuilt_from_host_and_port` | — | — | `test_the_consent_page_forbids_framing_and_lets_its_form_reach_only_this_loopback_origin`, `test_registration_takes_only_ipv4_loopback_redirect_uris`, `test_a_loopback_redirect_uri_takes_any_port_and_nothing_else_changes` |

The SC-20 rule "any loopback port" is not covered by a reference server test that this package read. The
prototype issuer covers it (`test_a_loopback_redirect_uri_takes_any_port_and_nothing_else_changes`).

### Runs of Concept 0.7

| Run | Setting | Fact |
|---|---|---|
| E13 | production, 2026-11-08, observed in one operator run, not independently reproduced, synthetic data | The second host at release 0.9.1 against the reference server at R3. First, a resolve got `409 unresolvable` with the reason `unknown`: the person had signed in to the resolver with one account and had an MCP session with another account. After the person signed in to the resolver with the same account, a click on a reference showed its value on the screen (`display-1`). |

No end-to-end run of `process-1` against the reference server is recorded in this package. The reference
host in `prototype/` did not run against R3. It ran `process-1` and `display-1` offline against the
prototype issuer (`test_concept_07_host.py`); that is evidence of the prototype only, not of interoperability.

## Known deviation of the reference server (SC-01, P16)

**Fixed on 2026-10-27.** An operator check after a server fix observed the MCP URL as `resource`, and
run E12 ran without a deviation option ([IMPLEMENTATION-EVIDENCE.md](../IMPLEMENTATION-EVIDENCE.md)). This
section keeps the record of the state before the fix.

The reference server publishes its base URL as the RFC 9728 `resource` value. Its MCP URL is a path below
that value. This is **not conformant** to SC-01, which follows RFC 9728 section 3.3 strictly. The server
becomes conformant if it publishes metadata with `resource` identical to the MCP URL at the path-specific
well-known URL, names that document in its `WWW-Authenticate` answers, and puts the discovery object into
it (SPEC-CHANGES.md, SC-01).

A test host that resolves against the reference server today needs a tolerance for this deviation. The
test host has the operator option `--resource`, which accepts an MCP URL under a configured parent
resource. E8 to E10 used it (see "Production runs of 2026-10-26"). For E1 to E7, this file does not
record which option each run used. That option is an implementation choice of the test host. Its
tests (`test_a_configured_parent_resource_is_the_issuer`, `test_a_resource_the_mcp_url_is_not_under_stops_the_host`,
`test_the_mcp_url_must_lie_under_the_resource`) show the tolerance. They are not evidence for SC-01.

## Gaps that this matrix shows

- Concept 0.7: the reference server tests of R3 were read, not run. E13 is one operator run. The reference
  host and the prototype issuer implement Concept 0.7 at demo level and ran offline only, not against R3.
  The second host declares no extension and does not read `sinks`.
- Prototype gaps of Concept 0.7: the rule that every person with an account may use the issuer, with a
  block list and without service accounts (A7), is not tested; the issuer has fixture accounts and a
  block list only. The minimum audit content and the rate limits (OQ-18) are not implemented beyond a
  daily quota. `process-1` runs on POSIX only and was not tested on Windows.

- The reference server does not conform to SC-01 (P16). No server test checks that the MCP URL and the
  RFC 9728 `resource` are identical.
- E1 to E10 ran before the second review round. Since then, the test host refuses authorization server
  metadata without S256 and refuses a configured endpoint on another origin. Whether the reference server
  meets both is **not verified**.
- No test covers PKCE S256 enforcement at the server, the audit event, the 30-second expiry
  margin of the host, or the duplicate removal of the host.
- No test covers the SC-06 binding to resource, scope and profile set, or the SC-20 exact redirect
  matching. The prototype issuer stores the approval with subject, client, resource and scope set, but no
  test asserts the binding. The reference server tests that this package read do not cover it.
- No end-to-end run used a second, independent server or a second, independent host.
- `test_mcp_sdk_demo` was not run with SDK 1.x.
