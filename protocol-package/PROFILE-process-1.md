# Profile `process-1` (Concept 0.7, with implementation evidence)

**Status: evidence record, experimental.** The normative text of this profile is
[PROCESS-PROFILE.md](../PROCESS-PROFILE.md). This file maps each rule to the evidence of the reference server
and of the second host. Where an implementation differs from a rule, the evidence column says so.

The evidence columns use these terms:

- **Server:** a test of the reference server at revision R3, or at R4 where the cell says "(R4)"
  ([README.md](README.md#sources-and-versions)). This package read the test name and its assertions at
  that revision. It did not run the test.
- **Second host:** the coding-agent plugin that [IMPLEMENTATION-EVIDENCE.md](../IMPLEMENTATION-EVIDENCE.md)
  names, at its release 0.9.1. A test name refers to its `tests/test_sref_client.py` or
  `tests/test_sref_hooks.py`. This package read the source and the test names. It did not run the tests.
- **Not verified:** this package found no evidence for the rule.

The reference host in `prototype/` implements this profile at demo level (POSIX only), and the prototype
issuer implements its server rules. Their tests run offline only; [CONFORMANCE-RESULTS.md](CONFORMANCE-RESULTS.md),
section "Concept 0.7", names them. No end-to-end run against the reference server is recorded.

**Identifier.** The identifier is `process-1` (OQ-21, decided). Since R4 the reference server publishes
this profile as `process-1`, with the `sink_type` `process` and the resolve scope and the process scope
(R4 `test_discovery_names_the_process_sink_process_1_and_not_the_former_name`,
`test_the_process_sink_type_maps_to_process_1_with_its_scopes`;
[IMPLEMENTATION-EVIDENCE.md](../IMPLEMENTATION-EVIDENCE.md) quotes the live object). At R3 the server used
a vendor-prefixed identifier. R4 keeps no alias for it. The second host at release 0.9.1 asks for the
identifier of R3: it looks for it in `sink_profiles` before a request (`maisecrets/sref_client.py`,
`SINKS` and `resolve`). So against R4 it refuses the process sink before any request. This package read
that in the source and did not run it.

## 1. Preconditions

| ID | Rule | Server | Second host |
|---|---|---|---|
| PR1 | The host resolves only if the negotiated intersection holds `process-1` and a resolver profile. | Not applicable | **Deviation.** The second host declares no extension to the server (its threat model, C31). It applies its own rule in place of negotiated provenance: a reference resolves only if an MCP result of a server in the user scope showed it in the same session in the last 24 hours. |
| PR2 | The discovery object lists the profile in `sink_profiles` and in `sinks`, with its `sink_type` and its whole scope set. | `test_discovery_and_server_settings_list_both_sinks_with_their_scopes`, `test_discovery_and_server_settings_name_exactly_the_three_sinks`; the identifier `process-1`: (R4) `test_discovery_names_the_process_sink_process_1_and_not_the_former_name` | **Partial.** The host reads `sink_profiles` and `process_scope`, not `sinks` (`maisecrets/sref_client.py`, `discover`). It refuses a sink that the server does not offer before a request: `test_a_sink_the_gateway_does_not_offer_is_refused_before_a_request`. |
| PR3 | A token without the process scope gets `403 insufficient_scope` before any lookup, with no value and no audit event. | `test_a_file_only_token_gets_insufficient_scope_for_a_process_without_a_value_or_a_row` | `test_a_login_without_commands_names_the_reason_and_runs_nothing`. The command prints a fixed reason and stops with exit status 97. |
| PR4 | The host asks for the process scope only where it masks command output. | Not applicable | `test_the_process_scope_is_asked_for_on_top_where_command_output_is_masked`. The host asks for it on macOS and Linux, not on Windows (`login_scope`). |
| PR5 | The process scope alone, or with an agent scope, is `invalid_scope`. | `test_the_process_scope_alone_or_with_agent_scopes_is_refused` | Not applicable |
| PR6 | A refresh keeps the granted scope set. A token without the process scope stays without it. | `test_the_process_scope_survives_a_refresh_and_a_file_grant_stays_file_only` | `allows` names what a login allows. A login without the scope needs a new login: `test_a_login_without_the_process_scope_still_fills_a_file`. |
| PR7 | A token with the process scope also resolves into a file. A token without it still resolves into a file. | `test_a_process_token_also_resolves_into_a_file_and_that_row_names_no_program`, `test_a_file_only_token_still_resolves_into_a_file` | `test_a_login_without_the_process_scope_still_fills_a_file` |

## 2. Which references the sink resolves

| ID | Rule | Server | Second host |
|---|---|---|---|
| PR8 | Only observed references with one trusted issuer. | Not applicable | Under its own session rule (PR1): `test_a_reference_no_session_received_is_refused_with_its_cause`, `test_another_session_gets_a_reason_and_the_gateway_is_not_asked`. |
| PR9 | A reference of another person is `unknown`. | See PROFILE-oauth-resolver-1.md, R15. | Not applicable |

## 3. Wire values

| ID | Rule | Server | Second host |
|---|---|---|---|
| PR10 | `sink_type` is `process`. A value that is not exactly a known `sink_type` gets `403 ineligible_sink`. | `test_a_sink_type_that_is_not_exactly_a_known_one_is_refused` | `maisecrets/sref_client.py`, `SINKS` |
| PR11 | `destination` is the program name: the first word after leading `NAME=value` assignments, its last path part. Never the command line. | Not applicable (the server cannot see the command) | `maisecrets/sref_hooks.py`, `program_of` (the base name of the first word after the assignments; `sh` if the command holds only assignments). `test_the_value_reaches_the_command_and_the_gateway_learns_the_program`, `test_the_program_name_comes_from_the_command_not_from_a_display`. The host splits words at white space, without the quoting rules of the shell. The reference host uses the quoting rules (`shlex`). PROCESS-PROFILE.md, section 3 leaves this open. |

## 4. When the sink resolves

| ID | Rule | Server | Second host |
|---|---|---|---|
| PR12 | The host resolves only when the command reads the value. A refused command costs no resolve. | Not applicable | `test_the_hook_resolves_nothing_and_the_command_fetches_the_value_once_when_it_starts`. A child process serves the value through a FIFO and resolves only after the command opened it (C31). |
| PR13 | All references of a command resolve before it gets a value. A failure stops the command. | Whole-request refusal: PROFILE-oauth-resolver-1.md, R2. | `test_a_failed_resolve_stops_the_command_instead_of_running_it_without_the_value` (exit status 97) |
| PR20 | The value goes through a channel that only the command reads, never in the command line. A named channel is owner-only, in a directory that only the owner can open, and gives the value once, to one reader. | Not applicable | Source: a FIFO with mode 0600 in a per-user directory with mode 0700 (`maisecrets/hooks.py`, `_run_dir` and `_serve_value_later`). The child writes the value once and removes the FIFO. A process of the same user can open the FIFO before the command (PROCESS-PROFILE.md, section 7). |

## 5. Output boundary

| ID | Rule | Server | Second host |
|---|---|---|---|
| PR14 | The host masks the command output before the model sees it. | Not applicable | `test_an_echo_of_the_value_comes_back_as_the_reference` and the other echo tests of `tests/test_sref_hooks.py`. |
| PR15 | The masking applies also on the failure path. | Not applicable | **Partial.** In one coding-agent client, the host ends a command that got a server value with exit status 0 and names the real status as text, so that the client masks the output: `test_a_command_that_prints_the_value_and_fails_ends_with_0_so_its_output_is_masked`, `test_only_a_claude_code_command_with_a_server_value_gets_the_exit_trap`. The host threat model (C27) lists the paths where this fails: a command that sets its own EXIT trap, replaces the shell with `exec`, is killed or runs past the timeout of the client. On these paths a printed value reaches the model. |
| PR16 | The report holds no value, no reference and no credential. The audit of the host names a reference by its kind and 4 characters of its identifier. | Not applicable | `test_the_audit_names_the_reference_without_its_id` |

## 6. Server rules

| ID | Rule | Server | Second host |
|---|---|---|---|
| PR17 | The audit event keeps of `destination` only the last path part without white space, else `other`. | `test_a_process_token_resolves_into_a_command_and_the_row_names_sink_and_program`, `test_the_audit_row_keeps_a_plain_program_name_and_nothing_else`. The server is stricter than the rule: a last path part that does not match `[A-Za-z0-9][A-Za-z0-9._+-]{0,63}` is also `other` (read in the source). | Not applicable |
| PR18 | The consent page names the process scope in its own line, only when the client asks for it. | `test_the_consent_page_names_commands_only_when_the_client_asks_for_them` | Not applicable |
| PR19 | The device list says which device may put values into commands. | `test_the_device_list_says_which_device_may_write_into_commands` | Not applicable |

## 7. End-to-end evidence

No end-to-end run of this profile is recorded in this package.
