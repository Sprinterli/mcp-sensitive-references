# Profile `local-file-1` (as implemented and tested)

**Status: proposed change, experimental.** This file states the local-file sink profile as the test host
implements it (`prototype/demo/mcp_host.py`, `--resolve-into`, and
`prototype/src/sensitive_references/sink.py`, `ProtectedFileSink`). It replaces nothing in concept 0.5.
`SPEC-DRAFT.md`, "Resolution and sinks", and `prototype/EXTENSION-PROFILE-DRAFT.md`, "Local file sink
profile", stay as they are.

The evidence columns use the same terms as [PROFILE-oauth-resolver-1.md](PROFILE-oauth-resolver-1.md).
"Host" means `prototype/tests/test_mcp_host_resolve.py` unless another file is named. "Prototype" means
`prototype/tests/test_sensitive_references.py`.

## 1. Purpose

The sink writes plaintext values into one local file. The model-facing result keeps the references. The
model does not see the file content.

## 2. Preconditions

| ID | Rule | Evidence |
|---|---|---|
| L1 | The host resolves only if both `oauth-resolver-1` and `local-file-1` are in the negotiated intersection of the host and the server. | Host `test_without_the_negotiated_profiles_nothing_is_sent`; host `test_without_advertised_profiles_the_host_does_not_resolve` (real MCP SDK 2.x server); host `test_a_resolving_host_declares_both_profiles` |
| L2 | If the metadata holds the discovery object, the object must list both profiles. Otherwise the host stops (`profile_not_offered`), also when the endpoint is configured. | Host `test_a_discovery_object_without_the_negotiated_profiles_is_refused`, `test_a_configured_endpoint_does_not_excuse_a_bad_discovery_object` |
| L3 | The host chooses the destination under its own policy. The model does not choose it. In the test host the destination is the operator option `--resolve-into`. | Host `test_the_options_map_to_the_configuration` |
| L4 | The content that the sink writes comes from host configuration (`--materialize-template`). It is not model output. | Host `test_the_template_is_configuration`. End-to-end run 2026-10-25: a forged reference in the template produced no file. |

## 3. Which references the sink resolves

| ID | Rule | Evidence |
|---|---|---|
| L5 | The sink resolves a reference only if the host observed it in a negotiated, authenticated result, and only if it has exactly one trusted issuer. | Host `test_an_ambiguous_reference_is_not_sent`, `test_an_unobserved_or_forged_reference_is_not_sent`; prototype `test_unobserved_forged_token_fails_closed`, `test_ambiguous_issuer_fails_closed` |
| L6 | The sink sends a reference only to the resolve endpoint of its own issuer. | Host `test_a_reference_from_another_issuer_is_not_sent`; prototype `test_wrong_issuer_does_not_resolve` |
| L7 | A reference matches by exact code points. The host does not normalize, case-fold, trim or rebuild a token. | `prototype/tests/test_reference_grammar.py` (both tests) |
| L8 | The host removes duplicate references before it sends a batch. | Not yet tested (`resolver_client.py`, `OAuthHttpResolver.resolve`; `mcp_host.py`, `materialize`) |

## 4. Materialization

| ID | Rule | Evidence |
|---|---|---|
| L9 | The sink resolves every reference of the content before it writes. If the host splits the references into batches, each batch has at most the effective limit of the server (SC-09: the published `max_references`, else 100), and every batch must succeed first. The test host uses batches of 100, which every server accepts. | Host `test_more_than_100_references_go_in_batches_of_100`; prototype `test_batch_is_all_or_nothing`. Observed (one operator run, not independently reproduced): E8 to E10 materialized. |
| L10 | A failure leaves the destination unchanged. If the file existed, its content stays. No temporary file stays. | Host helper `assert_nothing_written` in every failure test, for example `test_a_partially_invalid_batch_writes_nothing` and `test_an_unreachable_resolve_endpoint_writes_nothing` (existing content kept) |
| L11 | The sink writes a temporary file in the destination directory, calls `fsync`, and then replaces the destination atomically (`os.replace`). | `src/sensitive_references/sink.py`. The atomic replace is shown indirectly by L10. A crash between write and replace is not yet tested. |
| L12 | The written file has no permission bits for group or others. | Host `test_interactive_authorization_materializes_and_reports_no_secret` (asserts `st_mode & 0o077 == 0`) |
| L13 | The sink accepts a 200 answer only if it holds exactly the references of the batch, each with a string value. | Host `test_an_incomplete_or_extra_batch_writes_nothing`; `prototype/tests/test_oidc_and_resolve_http.py`, `test_http_resolver_accepts_only_complete_batch_from_configured_endpoint` |

## 5. What leaves the sink

| ID | Rule | Evidence |
|---|---|---|
| L14 | The model-facing result keeps the references. It holds no value. | Host `test_interactive_authorization_materializes_and_reports_no_secret` (`model_content_keeps_reference`, zero sentinels in model content); prototype `test_valid_observed_reference_resolves_to_protected_file_only`. Observed (one operator run, not independently reproduced): E8 to E10, zero sentinel values in model content. |
| L15 | The report holds no reference, no value and no credential. | Host helper `assert_report_clean`; host `test_the_host_materializes_an_observed_reference` (end to end) |
| L16 | The sink sends `sink_type: local_file` and a `destination` to the resolve endpoint. The test host sends the absolute path. See SC-10 for the proposed change to a label. | `resolver_client.py`, `OAuthHttpResolver._batch`. The content of `destination` is not asserted by a host test. |
| L17 | If a later action echoes a value that this operation resolved, the host can replace the value with its reference. | Prototype `test_downstream_echo_redaction_uses_only_values_resolved_in_this_operation`. The test host does not run a later action. |

## 6. Not in this profile

- Command interpolation, document sinks and a general filesystem policy (`prototype/EXTENSION-PROFILE-DRAFT.md`,
  "Local file sink profile").
- Protection after the file exists. A process with the same operating-system privileges can read the file
  (`SECURITY-MODEL.md`, "Limits").
- A destination policy at the server. The reference server checks only the length of `destination`
  (at most 4096 characters, read in its source).
