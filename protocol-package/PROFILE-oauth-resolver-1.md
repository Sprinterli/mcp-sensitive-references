# Profile `oauth-resolver-1` (as implemented and tested)

**Status: proposed change, experimental.** This file states the OAuth resolver profile as the reference
server and the test host implement it. It replaces nothing in concept 0.5. The candidate text in
`prototype/EXTENSION-PROFILE-DRAFT.md`, "OAuth Resolver Profile", stays as it is.

## How to read the evidence columns

- **Server:** a test of the reference server at revision `e5268633f`. This package read the test and did
  not run it.
- **Host:** a test in `prototype/tests/test_mcp_host_resolve.py` unless another file is named. These tests
  ran on 2026-10-25.
- **Not yet tested:** the source implements the rule, but no test shows it. The cell names the source.
- **Not verified:** this package found no evidence for the rule in either implementation.

## 1. Roles

| Role | What it does |
|---|---|
| Protected resource | The MCP server. Its RFC 9728 `resource` value is the issuer identity of its references (SC-01). |
| Authorization server | Issues resolver tokens. In the reference server it is the authorization server of the MCP endpoint. |
| Resolver client | A separate OAuth client of the host. It is not the MCP client that holds the agent token. |
| Resolve endpoint | An HTTP endpoint of the protected resource. It returns plaintext values to the resolver client only. |

## 2. Discovery

| ID | Rule | Server | Host |
|---|---|---|---|
| D1 | The server publishes `sensitive_references` in its RFC 9728 metadata with `resolve_endpoint`, `resolve_scope`, `resolver_profiles`, `sink_profiles` and `status`. | `test_discovery_publishes_the_endpoint_and_the_profiles_while_on` | `test_the_endpoint_and_scope_come_from_discovery` |
| D2 | Every protected-resource metadata document of the server carries the object while the profile is on, and no document carries it while the profile is off. | `test_every_protected_resource_document_carries_the_discovery_block_while_on`, `test_an_empty_allowlist_switches_the_resolver_off` | — |
| D3 | The resolve scope is not in `scopes_supported` of any RFC 9728, RFC 8414 or OpenID Connect discovery document. | `test_the_resolve_scope_stays_out_of_scopes_supported` | — |
| D4 | The host refuses metadata whose `resource` is not the issuer, as an exact string. | Not applicable | `test_metadata_for_another_resource_is_refused` |
| D5 | The issuer is the RFC 9728 `resource` value. That value is identical to the MCP URL (SC-01, RFC 9728 section 3.3). | **Not conformant.** The reference server publishes its base URL as `resource` (P16). See the note below the table. | Default path: `test_metadata_for_another_resource_is_refused` (exact string). The `--resource` tolerance is not evidence for D5 (see the note). |
| D6 | The host accepts a discovered resolve endpoint only on the origin of the resource. | Not applicable | `test_a_discovered_cross_origin_endpoint_is_refused` |
| D7 | The host uses `https`, or `http` on loopback only. | Not applicable | `test_an_insecure_resolve_endpoint_is_refused` |
| D8 | The host takes the scope from configuration, then from `resolve_scope`, then from the default `sensitive-references.resolve`. | Not applicable | `test_the_endpoint_and_scope_come_from_discovery` (discovery path). The configuration path and the default are not yet tested (`demo/mcp_host.py`, `_resolver_setup`). |
| D9 | The host refuses to select one of several authorization servers. | Not applicable | Not yet tested (`demo/mcp_host.py`, `_resolver_setup`). |
| D10 | The host refuses authorization server metadata whose `issuer` is another issuer (RFC 8414 section 3.3), and metadata without S256 in `code_challenge_methods_supported`. | Not applicable | Not yet tested (`src/sensitive_references/resolver_client.py`, `discover_authorization_server`). |

**Known deviation of the reference server (D5).** The reference server publishes its base URL as
`resource`. Its MCP URL is a path below that value (P16). This is not conformant to D5 and SC-01. The
server becomes conformant if it publishes metadata with `resource` identical to the MCP URL at the
path-specific well-known URL, names that document in `WWW-Authenticate`, and puts the discovery object
into it ([SPEC-CHANGES.md, SC-01](SPEC-CHANGES.md#sc-01-the-issuer-identity-is-the-rfc-9728-resource-value)).
The test host interoperates with the server today only through its operator option `--resource`, which
accepts an MCP URL under a configured parent resource (host tests
`test_a_configured_parent_resource_is_the_issuer`, `test_a_resource_the_mcp_url_is_not_under_stops_the_host`,
`test_the_mcp_url_must_lie_under_the_resource`). That option is an implementation choice of the test host.
It is not part of this profile.

## 3. Client registration and authorization

| ID | Rule | Server | Host |
|---|---|---|---|
| A1 | The resolver client is a separate client. The host registers it by dynamic client registration (RFC 7591) with a loopback redirect URI, or uses a configured `client_id`. | `test_an_unregistered_client_gets_no_resolver_code` | `test_interactive_authorization_materializes_and_reports_no_secret` (registration path). The configured `client_id` path is not yet tested. |
| A2 | The flow is Authorization Code with PKCE S256 and the RFC 8707 `resource` parameter. | The server refuses a request without S256 in its source (`authorize` branch). **Not yet tested** by a server test. | `test_interactive_authorization_materializes_and_reports_no_secret` (asserts `scope`, `resource`, `code_challenge_method=S256`, loopback redirect) |
| A3 | The request names the resolve scope alone. `openid` may ride along. A request that mixes the resolve scope with agent scopes gets `invalid_scope` and no token. | `test_a_request_that_mixes_the_resolve_scope_with_agent_scopes_gets_neither` (two scope sets) | The host requests the resolve scope alone: `test_interactive_authorization_materializes_and_reports_no_secret` |
| A4 | The host checks `state`. | Not applicable | `test_a_callback_with_another_state_is_refused` |
| A5 | The host checks the RFC 9207 `iss` parameter when it is present or advertised. | The server adds `iss` to the redirect in its source. **Not yet tested.** | `test_a_callback_from_another_issuer_is_refused` |
| A6 | Without a signed-in session, the server shows no consent page and issues no code. | `test_without_a_session_there_is_no_consent_page_and_no_code` | — |
| A8 | The server issues a code of this profile only to a loopback redirect URI (RFC 8252 section 7.3), because the only sink profile writes a local file. A web redirect that the server accepts for other clients gets no consent page and no code. | `test_a_client_whose_redirect_is_not_loopback_gets_no_page_and_no_code` | The host listens on loopback: `test_interactive_authorization_materializes_and_reports_no_secret` |
| A7 | A principal that the server does not enable gets `access_denied` and no consent page. | `test_a_principal_not_on_the_allowlist_is_denied_without_a_consent_page` | — |

## 4. Consent

| ID | Rule | Server | Host |
|---|---|---|---|
| C1 | The first authorization of a client for a user shows a consent page. A browser session alone issues no code. | `test_the_first_authorization_shows_a_consent_page_and_issues_no_code` | End-to-end run 2026-10-25: one consent page |
| C2 | Consent applies once per user and client. A second authorization of the same client gets a code without a page. Another client gets a new page. | `test_consent_is_asked_once_per_client_then_codes_follow_without_interaction` | End-to-end run 2026-10-25: zero consent pages with the cached token |
| C3 | Only the user's own answer on the page gives consent: a nonce that is absent or used, a cross-origin post, another user and a "deny" answer give nothing. | `test_consent_cannot_be_given_without_the_users_own_answer_on_the_page` (five cases) | — |
| C4 | A consent post without an `Origin` header gives nothing. | `test_a_consent_post_without_an_origin_header_grants_nothing` | — |
| C5 | The consent page cannot be framed (`frame-ancestors 'none'`). | `test_the_first_authorization_shows_a_consent_page_and_issues_no_code` | — |
| C6 | The consent bounds the whole authorization. A withdrawn or expired consent stops refresh and every live access token. | `test_a_withdrawn_or_expired_consent_stops_refresh_and_the_live_token` | — |
| C7 | The consent lives 180 days. The stored grant time decides, not only a storage expiry, so a lost expiry or a restored copy cannot extend it. | `test_a_consent_older_than_its_lifetime_is_no_consent_even_without_a_ttl` | — |
| C9 | A principal that the server disables loses every consent. A later enablement needs a new consent. The deletion of a user withdraws the consents and the enablement. | `test_taking_a_principal_off_the_allowlist_withdraws_its_consent_for_good`, `test_forgetting_a_user_withdraws_every_consent_and_the_listing` | — |
| C10 | The answer on the consent page checks the client registration again. A client that was deleted after the page was shown gets no consent and no code. | `test_a_consent_for_a_client_deleted_after_the_page_grants_nothing` | — |
| C8 | The server asks for no consent per reference or per tool call. | Plan section 6, M4a. **Not verified** by a test. | — |

## 5. Tokens

| ID | Rule | Server | Host |
|---|---|---|---|
| T1 | A resolver access token is its own class, has the resolve scope only, and lives 3600 seconds. | `test_the_resolver_token_is_its_own_class_and_short_lived` | — |
| T2 | A resolver token does not authorize an MCP request. | `test_a_resolver_token_is_refused_where_an_agent_token_is_expected`, `test_a_resolver_token_never_reaches_the_agent_suffix_lookup` | — |
| T3 | An agent token does not authorize a resolve request. The host never sends the agent token to the resolve endpoint. | `test_an_agent_token_is_refused_at_the_resolve_endpoint` | `test_the_agent_token_is_never_sent` |
| T4 | The server enforces the expiry of an access token. | `test_an_expired_resolver_token_resolves_nothing` | — |
| T5 | A refresh token rotates. The old refresh token stops working. | `test_refresh_rotates_and_the_old_refresh_token_is_dead` | `test_an_expired_token_is_refreshed_and_rotated` |
| T6 | A refresh token works only for its own client. | `test_a_refresh_token_works_only_for_its_own_client` | — |
| T7 | The refresh token lives 30 days. | Read in the server source (`REFRESH_TTL_SECONDS`). **Not yet tested.** | — |
| T8 | A token response without the resolve scope is refused (`scope_not_granted`). | Not applicable | `test_a_token_without_the_resolve_scope_is_refused` |
| T9 | The host caches the token in a file with mode 0600, keyed by resource, authorization server and scope. It refuses a cache file that others can read. | Not applicable | `test_interactive_authorization_materializes_and_reports_no_secret` (mode), `test_a_cached_token_is_used_without_a_new_authorization`, `test_a_cache_file_that_others_can_read_is_refused` |
| T10 | The host treats an access token as expired 30 seconds before `expires_in` ends. | Not applicable | `test_an_expired_token_is_refreshed_and_rotated` (an expired token). The 30-second margin itself is not yet tested. |
| T11 | After a 401, the host gets one new token and tries once again. After a second 401, the run fails and nothing is written. | Not applicable | `test_an_expired_token_is_refreshed_once_then_the_run_fails` |
| T12 | Without a valid token and with interaction off, the host writes nothing. | Not applicable | `test_without_a_token_and_without_interaction_nothing_is_written`, `test_a_failed_refresh_without_interaction_writes_nothing` |
| T13 | A principal that the server disables loses its live tokens. | `test_removing_a_principal_from_the_allowlist_stops_a_live_token` | — |

## 6. Resolve request

Request:

```http
POST /sensitive-references/resolve HTTP/1.1
Host: mcp.example.com
Authorization: Bearer <resolver access token>
Content-Type: application/json

{"references": ["⟦sref:email:AbCdEfGhIjKlMnOpQrStUvWx1234⟧"],
 "sink_type": "local_file",
 "destination": "<see SC-10>"}
```

Success: `200` with `{"values": {"<reference>": "<value>"}}` and `Cache-Control: no-store`.

| ID | Rule | Server | Host |
|---|---|---|---|
| R1 | A consented resolver token resolves a reference of its own user. | `test_a_consented_resolver_resolves_its_users_reference` | `test_interactive_authorization_materializes_and_reports_no_secret` |
| R2 | The whole batch resolves, or the answer holds no value. One unknown, malformed, revoked, cross-user or truncated reference refuses the batch with `409 unresolvable`. | `test_a_batch_with_one_reference_that_does_not_resolve_returns_no_value` (five cases) | `test_a_partially_invalid_batch_writes_nothing`, `test_a_revoked_reference_in_a_batch_writes_nothing`, `test_a_reference_of_another_user_writes_nothing` |
| R3 | A revocation holds when an older registry record comes back. | `test_a_replayed_mapping_body_does_not_resolve_a_revoked_reference` | — |
| R4 | A batch has 1 to 100 references. 101 references give 413. 0 references give 400. | `test_a_request_outside_the_profile_is_refused` (`too_many`, `empty`) | `test_more_than_100_references_go_in_batches_of_100` |
| R5 | A `sink_type` other than `local_file` gives 403. | `test_a_request_outside_the_profile_is_refused` (`sink`) | The host refuses another sink type before it sends. Not yet tested (`OAuthHttpResolver.resolve`). |
| R6 | The host accepts a 200 answer only if its key set is exactly the batch. | Not applicable | `test_an_incomplete_or_extra_batch_writes_nothing` |
| R7 | The host does not follow a redirect from the resolve endpoint. | Not applicable | `test_a_redirect_from_the_resolve_endpoint_is_not_followed` |
| R8 | An unreachable endpoint writes nothing. | Not applicable | `test_an_unreachable_resolve_endpoint_writes_nothing` |
| R9 | The server limits a principal to 1000 values per day and answers 429 after that. The counter lives on storage that does not evict. | `test_the_daily_quota_refuses_the_batch_that_crosses_it`, `test_every_key_of_the_profile_lives_on_the_auth_backend` | — |
| R10 | The server writes one audit event per resolve with hashed reference ids and a hashed client id, and no value. | Plan section 6, M4a, "Resolve". **Not yet tested** in the cited test module. | — |
| R11 | A token without the resolve scope gives `403 insufficient_scope`. | Read in the server source (`validate`). **Not yet tested.** | — |
| R12 | A token for another audience resolves nothing. | `test_a_token_for_another_audience_resolves_nothing` | — |
| R13 | A reference whose kind differs from the kind of the stored value counts as unknown. | `test_a_reference_with_the_wrong_kind_does_not_resolve` | — |
| R14 | A request body over 64 KiB gives 413 and no value. | `test_a_body_over_the_limit_is_refused_before_it_is_read` | — |

## 7. Error codes

The reference server uses the codes in [SPEC-CHANGES.md, SC-11](SPEC-CHANGES.md#sc-11-error-format-of-the-resolve-endpoint).
The authorization endpoint uses the OAuth codes `invalid_request`, `invalid_scope`, `invalid_client`,
`access_denied` and `login_required`. The token endpoint uses `invalid_grant` and `invalid_target`. These
codes were read in the server source. The host reports only the code. It accepts a code of at most 64
characters from `[A-Za-z0-9_.-]` and reports `error` for any other code
(`src/sensitive_references/resolver_client.py`, `OAuthHttpResolver._batch`). The replacement of an
unsafe code is not yet tested.

## 8. Not in this profile

- Sender-constrained tokens (DPoP, mTLS). Neither implementation uses them (F6). See OQ-5.
- Token introspection or JWT access tokens. The reference server uses opaque tokens with a server-side
  record. The concept text "a profile should use `sub` by default" (`RESOLVER-PROFILE.md`, "Subject
  identity") does not apply to an opaque token. The local Keycloak probes of the prototype use JWTs with
  `sub` (`prototype/demo/keycloak_pkce_probe.py`).
- Server-to-server redemption and cross-server delegation (`SPEC-DRAFT.md`, "Non-goals").
