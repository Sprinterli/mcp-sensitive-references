# Profile `display-1` (Concept 0.7, with implementation evidence)

**Status: evidence record, experimental.** The normative text of this profile is
[DISPLAY-PROFILE.md](../DISPLAY-PROFILE.md). This file maps each rule to the evidence of the reference server
and of the second host. The evidence columns use the terms of
[PROFILE-process-1.md](PROFILE-process-1.md). A cell marked "source" names code of the second host that no
test of it shows.

The reference host in `prototype/` implements this profile at demo level (the screen is the terminal), and
the prototype issuer implements its server rules. Their tests run offline only;
[CONFORMANCE-RESULTS.md](CONFORMANCE-RESULTS.md), section "Concept 0.7", names them.

## 1. Preconditions

| ID | Rule | Server | Second host |
|---|---|---|---|
| DS1 | The host resolves only if the negotiated intersection holds `display-1` and a resolver profile. | Not applicable | **Deviation**, as PROFILE-process-1.md, PR1: no extension, its own session rule. |
| DS2 | The discovery object lists the profile in `sink_profiles` and in `sinks`, with its whole scope set. | `test_discovery_and_server_settings_list_the_display_sink_with_its_scopes` | **Partial.** The host reads `sinks`, but the member `display_scope` wins over the scope set of `sinks`, and an object without `sinks` is not refused (`maisecrets/sref_client.py`, lines 113 to 127; `test_the_scopes_come_from_the_sinks_map_when_the_named_fields_are_missing`). |
| DS3 | A token without the display scope gets `403 insufficient_scope` before any lookup. Header and body name the whole scope set and carry an `error_description`. No value and no audit event. | `test_a_token_without_the_display_scope_gets_insufficient_scope_before_any_lookup` (asserts the header, `scope`, `error_description`, no lookup and no audit row), `test_a_token_without_the_display_scope_gets_403_whatever_the_rest_of_the_body_holds` | `test_a_login_without_the_display_scope_names_the_reason` |
| DS4 | The host asks for the display scope only where it meets sections 4 and 5 of DISPLAY-PROFILE.md. | Not applicable | **Deviation.** `login_scope` (`maisecrets/sref_client.py`, lines 88 to 90 at release 0.9.4) adds the display scope to every login where the server names one, also in a client where the host draws no value. The host draws values only on a surface that says it draws locally (its threat model, C32). |
| DS5 | The display scope alone, or with an agent scope, is `invalid_scope`. | `test_the_display_scope_alone_or_with_agent_scopes_is_refused` | Not applicable |
| DS6 | A refresh keeps the display scope. | `test_the_display_scope_survives_a_refresh` | Not applicable |
| DS7 | A token with the display scope resolves into a file, and not into a command without the process scope. | `test_a_display_token_still_resolves_into_a_file_and_not_into_a_command` | Not applicable |

## 2. Wire values

| ID | Rule | Server | Second host |
|---|---|---|---|
| DS8 | `sink_type` is `display`, `destination` is exactly `screen`. Another destination gets `400`. | `test_a_display_resolve_names_the_screen_and_nothing_else` | `maisecrets/show_values.py`, `reveal`: the sink `display` with the destination `screen`. |
| DS9 | Exactly one reference per request. Another number gets `400`. | `test_a_display_resolve_takes_exactly_one_reference` | `reveal` sends one reference. |

## 3. When the sink resolves

| ID | Rule | Server | Second host |
|---|---|---|---|
| DS10 | Only after an action of the person on that reference. Never while the host draws. | Not applicable | `test_a_click_on_the_screen_shows_a_noted_reference_once_through_the_display_sink`. Source: `claude-mod/show-values.mjs` calls `reveal` from the handler of a link press only. |
| DS11 | Only a reference that the session got from a server result. | Not applicable | `test_a_reference_this_session_did_not_get_or_show_values_off_resolves_nothing` |
| DS12 | A limit of resolves per session. | Not applicable | Source: at most 20 per session id of the client process, counted on the client only (`claude-mod/show-values.mjs`, `REVEAL_MAX` at line 33 and the check at lines 180 to 188, in the memory of the module). A `/clear`, a resume and a new process start the count again. |

## 4. Output boundary

| ID | Rule | Server | Second host |
|---|---|---|---|
| DS13 | The value goes to the screen only, never to the model, a transcript, a log, an export or a file. | Not applicable | Source: the value lives in the memory of the module only. The host threat model (C32) reports a measurement on one client version for values of its own store: no value in a model request, the transcript, the debug log or the export. A revealed reference uses the same drawing function. Not measured separately. |
| DS14 | The host keeps the released value, so a paste of it is masked back. | Not applicable | Source: `show_values.reveal` releases the value for the session (`_server_release`). |
| DS15 | Copy only on a second action. A link that the model wrote copies nothing. | Not applicable | Source: the copy link of a reference exists only after its value is shown. Each copy link carries a random part that only the drawing holds. |
| DS20 | No released value in a link target, a URL or markup. | Not applicable | Source: a line with a link, a URL or HTML keeps its references and gets no value (`LINKY` and `rewrite` in `show-values.mjs`). The copy link carries the random part and the reference, not the value. |
| DS21 | Text that the model wrote is not the label of the action that resolves or copies. | Not applicable | Since release 0.9.4 the label of the click target is the reference with the display part that a server result of the same session gave, never the display part that the drawn text holds; without such a display the label is the reference alone (`claude-mod/show-values.mjs`, lines 45 to 48, 87 and 133; `maisecrets/sref_notes.py`, `displays`, lines 84 to 101). A display with a character of the categories Cf, Zl or Zp, with markup, of more than 64 characters, or with a finding of the detector is not kept, so it is not drawn (`maisecrets/sref_notes.py`, lines 48 to 65). `test_a_display_is_kept_only_when_plain_and_given_only_to_its_session`, `test_a_display_with_a_hidden_character_or_a_value_the_detector_finds_is_not_kept`, and in `tests/show-values.test.ts` "a reference is labelled with the display the gateway gave, never with the text the AI wrote (DS21)". |

## 5. Server rules

| ID | Rule | Server | Second host |
|---|---|---|---|
| DS16 | One audit event per reveal, with the person, the kind and a hash of the reference. | `test_a_display_token_shows_one_value_and_writes_one_row_with_person_kind_and_reference_hash` | Not applicable |
| DS17 | A reveal counts toward the daily quota. | `test_a_reveal_counts_in_the_daily_quota` | Not applicable |
| DS18 | The consent page names the display scope in its own line, only when the client asks for it. | `test_the_consent_page_names_the_screen_only_when_the_client_asks_for_it` | Not applicable |
| DS19 | The device list says which device may show values on the screen. | `test_the_device_list_says_which_device_may_show_values_on_screen` | Not applicable |

## 6. End-to-end evidence

**Observed (one operator run, not independently reproduced), 2026-11-08.** The second host at release
0.9.1 against the reference server at R3, with synthetic data. First, a resolve got `409 unresolvable` with
the reason `unknown`: the person had signed in to the resolver with one account and had an MCP session with
another account. After the person signed in to the resolver with the same account, a click showed the value
on the screen (run E13 in [CONFORMANCE-RESULTS.md](CONFORMANCE-RESULTS.md#runs-of-concept-07)).
