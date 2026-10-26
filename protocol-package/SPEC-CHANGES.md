# Proposed changes to concept 0.5

**Status: proposed change. Not concept text.** Each entry below proposes a change to concept 0.5. The
concept files in the repository root do not change. If the community accepts an entry, a later concept
version can take its text.

Each entry has four parts:

- **Problem:** what concept 0.5 does not say, or says in a way that an implementation cannot follow.
- **Evidence:** the finding ids, and the file, section or test that shows the problem.
- **Proposed text:** normative text with MUST, SHOULD and MAY in the sense of RFC 2119 and RFC 8174.
- **Compatibility:** the effect on an implementation that follows concept 0.5 today.

Notation. "Reference server test `x`" means a test of the reference server at revision `e5268633f`. This
package read that test and did not run it. "Host test `x`" means a test in `prototype/tests/` that ran on
2026-10-25 (see [CONFORMANCE-RESULTS.md](CONFORMANCE-RESULTS.md#test-run)).

## Merged findings

Several findings of the two lists describe the same gap. This table shows which ids each entry merges.

| Entry | Subject | Merged ids |
|---|---|---|
| SC-01 | Issuer identity is the RFC 9728 `resource` | F3, F12, P10, P16 |
| SC-02 | Discovery of the resolve endpoint | F1, P12 |
| SC-03 | Where the host learns the resolve scope | F2, F13, P15 |
| SC-04 | The resolve endpoint is bound to the origin of the resource | F4 |
| SC-05 | Resolver token class and scope separation | (plan section 6, M4a decisions) |
| SC-06 | Consent semantics | F5, P13 |
| SC-07 | Resolver token lifetime, cache and renewal | F6 |
| SC-08 | Authorization response and authorization server checks | F10, F11 |
| SC-09 | Batch limits, splitting and duplicates | F7 |
| SC-10 | The sink context on the wire | F8 |
| SC-11 | Error format of the resolve endpoint | F9 |
| SC-12 | A refused reference inside an MCP tool call | P14 |
| SC-13 | Reference lifetime | P5 |
| SC-14 | Integrity of the issuer registry | P4 |
| SC-15 | The extension identifier | P7 |
| SC-16 | Protocol versions with an `extensions` map | P8 |
| SC-17 | Server text in the reference shape | P9 |
| SC-18 | The issuer-side sink | P1 |
| SC-19 | Hosts that cannot verify negotiation | P11, P6 |

P2 (two issuers) and P3 (where the display travels) get no normative text in this package. They are in
[OPEN-QUESTIONS.md](OPEN-QUESTIONS.md) as OQ-1 and OQ-2.

---

## SC-01. The issuer identity is the RFC 9728 `resource` value

**Problem.** Concept 0.5 says that the host records "the authenticated issuer/protected-resource identity"
(`prototype/EXTENSION-PROFILE-DRAFT.md`, "Token and host rules"). It does not say which string that is or
how a host compares two of them. The test host first used the MCP URL without credentials, query and
fragment (`prototype/README.md`, "Independent MCP test host"). The reference server publishes its RFC 9728
metadata for its base URL, not for the MCP URL (P16). The two strings differ. The host then cannot tell
which string is the issuer (F12). A trailing slash also makes two different issuers (F3).

RFC 9728 section 3.3 already answers the question. The `resource` value in the metadata MUST be identical
to the resource identifier from which the client built the metadata URL. If the client found the metadata
through the `resource_metadata` parameter of a `WWW-Authenticate` header, the `resource` value MUST be
identical to the URL that the client sent its request to. For an MCP endpoint, that URL is the MCP URL.
RFC 9728 does not allow a `resource` value of which the MCP URL is only a path below.

**Evidence.**

- F3 and F12 in `prototype/M4-FINDINGS.md`.
- P10: over HTTP with a bearer token, the URL is a locator and a TLS origin, not a cryptographic identity.
- P16: the reference server names the base URL as `resource` for compatibility with an existing client.
  This is a deviation from RFC 9728 section 3.3.
- Host test `test_metadata_for_another_resource_is_refused`: the host refuses metadata whose `resource`
  is not the issuer, as an exact string.

**Proposed text.**

> The issuer identity of a Sensitive Reference is the `resource` value of the RFC 9728 protected-resource
> metadata of the MCP endpoint. A server MUST publish protected-resource metadata whose `resource` value is
> identical to the URL of the MCP endpoint (RFC 9728 section 3.3). A host MUST compare two issuer
> identities as exact strings. A host MUST NOT normalize case, a trailing slash, a default port or a
> percent-encoding before it compares. If the metadata `resource` is not identical to the URL of the MCP
> endpoint, the host MUST NOT use the metadata, MUST NOT record an observation with that issuer and MUST
> NOT resolve.

The proposed text does not permit a `resource` value of which the MCP URL is a path below. An earlier
version of this entry permitted it. That rule is not compatible with RFC 9728 section 3.3, and this
revision removes it.

**Known deviation of the reference server (non-normative).** The reference server publishes its base URL
as `resource`, and its MCP URL is a path below that value (P16). This behaviour is **not conformant** to
SC-01. The reference server becomes conformant if it does these steps:

1. Publish protected-resource metadata at the path-specific well-known URL of the MCP endpoint (RFC 9728
   section 3.1), with `resource` identical to the MCP URL.
2. Name that metadata document in the `resource_metadata` parameter of its `WWW-Authenticate` answers on
   the MCP endpoint.
3. Put the `sensitive_references` object (SC-02) into that document, and bind resolver tokens to that
   `resource` value (RFC 8707).

The metadata document for the base URL can stay for the existing client, as the metadata of a separate
protected resource.

**Tolerance of the test host (non-normative).** The test host has an option `--resource`. With it, an
operator names a parent resource, and the host accepts an MCP URL that lies under it on the same origin
(host tests `test_a_configured_parent_resource_is_the_issuer`,
`test_a_resource_the_mcp_url_is_not_under_stops_the_host` and `test_the_mcp_url_must_lie_under_the_resource`).
This is an implementation choice of the test host, so that it can interoperate with the reference server
as the server is today. It is not conformant to SC-01, and it is not a proposal. Without `--resource`, the
test host requires that `resource` is identical to the MCP URL.

**Compatibility.** A host that records the MCP URL today records the same string as this text requires.
A server that publishes metadata for a parent resource, as the reference server does, must add metadata
for the MCP URL. Until it does, a conformant host does not resolve its references. A server that has no
RFC 9728 metadata has no issuer identity under this text. For such a server, a host can only use operator
configuration (see SC-02).

## SC-02. Discovery of the resolve endpoint

**Problem.** Concept 0.5 does not say where a host finds the resolve endpoint (`OPEN-QUESTIONS.md`, item 4).
The extension settings object cannot carry the endpoint today, because
`prototype/schema/sensitive-references-settings.schema.json` sets `additionalProperties: false`. Also, the
agent token authenticates the extension settings, while the resolver token is a different credential (F1).

**Evidence.**

- F1 in `prototype/M4-FINDINGS.md`. P12: the reference server publishes a provisional
  `sensitive_references` object in its RFC 9728 metadata.
- Reference server tests `test_discovery_publishes_the_endpoint_and_the_profiles_while_on` and
  `test_every_protected_resource_document_carries_the_discovery_block_while_on`.
- Reference server test `test_an_empty_allowlist_switches_the_resolver_off`: the object is absent while
  the profile is off.
- Host test `test_the_endpoint_and_scope_come_from_discovery`.

**Proposed text.**

> A server that offers `oauth-resolver-1` MUST publish a `sensitive_references` object in its RFC 9728
> protected-resource metadata. The object MUST contain `resolve_endpoint`, `resolve_scope`,
> `resolver_profiles` and `sink_profiles`. The object MAY contain `status`. A server MUST NOT publish the
> object while it does not accept resolve requests. A host MAY use an operator-configured endpoint
> instead of the discovered one. An operator-configured endpoint takes precedence.

Example:

```json
{
  "resource": "https://mcp.example.com/",
  "authorization_servers": ["https://mcp.example.com"],
  "scopes_supported": ["mcp"],
  "sensitive_references": {
    "resolve_endpoint": "https://mcp.example.com/sensitive-references/resolve",
    "resolve_scope": "sensitive-references.resolve",
    "resolver_profiles": ["oauth-resolver-1"],
    "sink_profiles": ["local-file-1"],
    "status": "experimental"
  }
}
```

**Compatibility.** No conflict with concept 0.5, which leaves discovery open. The field name
`sensitive_references` is not registered in the IANA "OAuth Protected Resource Metadata" registry. A SEP
must register it or choose another location (see [SEP-READINESS.md](SEP-READINESS.md)).

## SC-03. The resolve scope is in the discovery object, not in `scopes_supported`

**Problem.** The profile calls the resolve scope "deployment-defined" (`prototype/EXTENSION-PROFILE-DRAFT.md`,
"OAuth Resolver Profile"). RFC 9728 `scopes_supported` lists scopes but does not say which scope gives
resolve rights (F2). Many MCP clients request every scope in `scopes_supported` (F13, P15). A request that
mixes the resolve scope with agent scopes gets neither, so such a client fails.

**Evidence.**

- F2 and F13 in `prototype/M4-FINDINGS.md`. P15 in the plan.
- Reference server test `test_the_resolve_scope_stays_out_of_scopes_supported` (five metadata documents).
- Reference server test `test_a_request_that_mixes_the_resolve_scope_with_agent_scopes_gets_neither`.
- Host test `test_a_token_without_the_resolve_scope_is_refused` (`scope_not_granted`).

**Proposed text.**

> A server MUST name the resolve scope in `sensitive_references.resolve_scope`. A server SHOULD NOT list
> the resolve scope in `scopes_supported` of its RFC 9728 or RFC 8414 metadata. An authorization server
> MUST refuse an authorization request that names the resolve scope together with any scope other than
> `openid`. It MUST answer with `invalid_scope`. A host MUST request the resolve scope alone. If a token
> response names a scope set without the resolve scope, the host MUST NOT use the token.

**Compatibility.** A generic MCP client that requests every scope in `scopes_supported` keeps working,
because the resolve scope is not there. A deployment that lists the resolve scope in `scopes_supported`
today must remove it.

## SC-04. The resolve endpoint is bound to the origin of the resource

**Problem.** A resolver token has the protected resource as its audience. A resolve endpoint on another
origin would receive a token for the resource. Concept 0.5 does not bind the endpoint to an origin, and
it does not forbid redirects (F4).

**Evidence.**

- F4 in `prototype/M4-FINDINGS.md`.
- Host tests `test_a_discovered_cross_origin_endpoint_is_refused`,
  `test_a_redirect_from_the_resolve_endpoint_is_not_followed` and
  `test_an_insecure_resolve_endpoint_is_refused`.

**Proposed text.**

> A host MUST accept a discovered `resolve_endpoint` only on the origin of the `resource` value. A host
> MAY accept an operator-configured endpoint on another `https` origin. A host MUST use `https` for the
> resolve endpoint. A host MAY use `http` only on a loopback address, for tests. A host MUST NOT follow
> an HTTP redirect from the resolve endpoint or from the token endpoint.

**Compatibility.** A server that hosts its resolve endpoint on another origin must change its layout or
tell its users to configure the endpoint.

## SC-05. The resolver token is a separate token class

**Problem.** Concept 0.5 says: "The ordinary MCP agent token must not automatically grant plaintext
resolution rights" (`SPEC-DRAFT.md`, "Resolver profile boundary"). It does not say the reverse: a resolver
token must not work as an agent token. The reference server found agent-token readers that accept a token
by its suffix alone (plan section 6, M4, "What the OAuth layer has today"). A scope check alone does not
protect such a reader.

**Evidence.**

- Plan section 6, M4a, "A token class, not only a scope", and Gate A finding LOW.
- Reference server tests `test_the_resolver_token_is_its_own_class_and_short_lived`,
  `test_a_resolver_token_is_refused_where_an_agent_token_is_expected`,
  `test_an_agent_token_is_refused_at_the_resolve_endpoint` and
  `test_a_resolver_token_never_reaches_the_agent_suffix_lookup`.
- Host test `test_the_agent_token_is_never_sent`.

**Proposed text.**

> A resolver token MUST NOT authorize an MCP request. An agent token MUST NOT authorize a resolve request.
> A server SHOULD make the two classes distinct by more than the scope, for example by a separate token
> record or a separate audience. A host MUST NOT send the agent token to the resolve endpoint. A host MUST
> refuse to send a resolver token that is equal to the agent token.

**Compatibility.** No conflict. A server that issues one token class for both purposes today must split it.

## SC-06. Consent semantics

**Problem.** The profile does not say what the user agrees to, how long the approval lives, or whether a
new client needs new consent (F5, P13). Without a consent step, any local program that can open the
browser of the user can get a resolver token silently (plan section 6, M4a, "One consent, once"). A
consent that does not bound refresh lets a client that refreshes often outlive the approval (plan
section 6, Gate A finding HIGH).

**Evidence.**

- F5 in `prototype/M4-FINDINGS.md`. P13 in the plan.
- Reference server tests `test_the_first_authorization_shows_a_consent_page_and_issues_no_code`,
  `test_consent_is_asked_once_per_client_then_codes_follow_without_interaction`,
  `test_consent_cannot_be_given_without_the_users_own_answer_on_the_page` (five cases),
  `test_a_consent_post_without_an_origin_header_grants_nothing`,
  `test_without_a_session_there_is_no_consent_page_and_no_code` and
  `test_a_withdrawn_or_expired_consent_stops_refresh_and_the_live_token`.
- End-to-end run of 2026-10-25: one consent page on the first run, zero on the second run with a cached
  token (see [CONFORMANCE-RESULTS.md](CONFORMANCE-RESULTS.md#end-to-end-runs)).

**Proposed text.**

> An authorization server MUST get an explicit approval from the user before it issues the first
> authorization code with the resolve scope to a client. The approval applies to one pair of subject and
> client. The approval covers resolution of every reference of that subject into the sink profiles that
> the server offers. An authorization server MUST NOT issue a resolver code on the basis of a browser
> session alone. The consent page MUST resist framing and cross-site request forgery. A withdrawn or
> expired approval MUST stop the refresh of resolver tokens and MUST stop every live resolver access token
> of that pair. An authorization server SHOULD NOT ask for consent per reference or per tool call.

**Compatibility.** A server that issues resolver tokens without consent today must add a consent step. A
host that registers a new client (RFC 7591) for each interactive authorization causes a new consent each
time, because each loopback port gives a new redirect URI (F5). See OQ-4 in
[OPEN-QUESTIONS.md](OPEN-QUESTIONS.md).

## SC-07. Resolver token lifetime, cache and renewal

**Problem.** The profile does not say how long a host keeps a resolver token, how the host stores it, or
when the host gets a new token (F6). Two implementations can disagree, and a loop of renewals is possible.

**Evidence.**

- F6 in `prototype/M4-FINDINGS.md`.
- Reference server tests `test_the_resolver_token_is_its_own_class_and_short_lived` (`expires_in` 3600),
  `test_refresh_rotates_and_the_old_refresh_token_is_dead`,
  `test_a_refresh_token_works_only_for_its_own_client` and `test_an_expired_resolver_token_resolves_nothing`.
- Host tests `test_a_cached_token_is_used_without_a_new_authorization`,
  `test_an_expired_token_is_refreshed_and_rotated`, `test_an_expired_token_is_refreshed_once_then_the_run_fails`,
  `test_a_failed_refresh_without_interaction_writes_nothing` and `test_a_cache_file_that_others_can_read_is_refused`.

**Proposed text.**

> A server MUST enforce the expiry of a resolver access token. A server SHOULD issue resolver access
> tokens with a lifetime of one hour or less. A server MUST rotate a resolver refresh token on each use and
> MUST bind it to the client that received it. A host that keeps a resolver token MUST store it so that
> other operating-system users cannot read it. A host MUST key a cached token by the triple of resource,
> authorization server and scope. After a 401 answer from the resolve endpoint, a host MAY get one new
> token and try once again. After a second 401 answer, the host MUST stop and MUST NOT write the sink.

**Compatibility.** No conflict. Sender-constrained tokens (DPoP, mTLS) are not part of this text. See OQ-5.

## SC-08. Authorization response and authorization server checks

**Problem.** The profile does not mention the RFC 9207 `iss` parameter, the RFC 8414 issuer check, or
the case of several authorization servers in RFC 9728 metadata (F10, F11). Without these checks, an
authorization server mix-up is possible.

**Evidence.**

- F10 and F11 in `prototype/M4-FINDINGS.md`.
- Host tests `test_a_callback_with_another_state_is_refused` and `test_a_callback_from_another_issuer_is_refused`.
- The host also checks RFC 8414 section 3.3 issuer equality, PKCE S256 in
  `code_challenge_methods_supported`, and the number of authorization servers. These checks are in
  `prototype/src/sensitive_references/resolver_client.py` and `prototype/demo/mcp_host.py`. **Not verified
  by a test.**

**Proposed text.**

> A host MUST use Authorization Code with PKCE S256 and the `resource` parameter (RFC 8707). A host MUST
> check `state`. If the authorization response has an `iss` parameter, or the authorization server
> metadata has `authorization_response_iss_parameter_supported: true`, the host MUST compare `iss` with the
> issuer of the authorization server (RFC 9207). A host MUST refuse authorization server metadata whose
> `issuer` is not the requested issuer (RFC 8414 section 3.3). If the RFC 9728 metadata lists more than one
> authorization server, the host MUST NOT select one automatically.

**Compatibility.** No conflict. These are current OAuth security practices.

## SC-09. Batch limits, splitting and duplicates

**Problem.** Concept 0.5 says that `local-file-1` "must resolve all references before it replaces its
destination" (`SPEC-DRAFT.md`, "Resolution and sinks"). The reference server accepts 1 to 100 references
in one request. A host with more references must split them. If batch 2 fails, the server already released
the values of batch 1 to the host. The file stays unchanged, but the server audit shows a release (F7).
The profile also does not say if a duplicate reference is valid.

**Evidence.**

- F7 in `prototype/M4-FINDINGS.md`.
- Reference server test `test_a_request_outside_the_profile_is_refused` (`too_many`: 101 references give
  413; `empty`: 0 references give 400).
- Host test `test_more_than_100_references_go_in_batches_of_100` (batches of 100 and 50).
- Duplicate removal by the host: `prototype/src/sensitive_references/resolver_client.py`,
  `OAuthHttpResolver.resolve`. **Not verified by a test.**

**Proposed text.**

> A server MUST accept at least 100 references in one resolve request. A server MAY publish a larger
> limit as `sensitive_references.max_references`. A host SHOULD send all references of one sink write in
> one request. If the host must split the references, the host MUST NOT write the sink until every request
> succeeded. The host MUST discard all values if one request fails. A host SHOULD remove duplicate
> references before it sends a request. A server MUST treat a duplicate reference as one reference.

**Compatibility.** The text does not change the all-or-nothing rule for the sink. It states that the
all-or-nothing rule of the server applies to one request only. `max_references` is a new optional field.

## SC-10. The sink context on the wire

**Problem.** The profile draft says that the resolver receives "the sink type, destination, and
authenticated principal" (`prototype/EXTENSION-PROFILE-DRAFT.md`, "Local file sink profile"). The
implementations differ from this text in three points:

1. The wire request carries `references`, `sink_type` and `destination`. It carries no principal. The
   server takes the principal from the resolver token (`prototype/src/sensitive_references/resolver_client.py`,
   `OAuthHttpResolver._batch`; plan section 6, M4a, "Resolve").
2. The profile identifier is `local-file-1`, but the wire value of `sink_type` is `local_file`. Concept
   0.5 does not define the wire value.
3. The host sends the absolute local path as `destination`. This tells the server the layout of the local
   file system, for example a user name in a home directory (F8). The reference server checks only the
   length of the value (at most 4096 characters, read in its source). It does not use the value for policy.

**Evidence.**

- F8 in `prototype/M4-FINDINGS.md`.
- Reference server test `test_a_request_outside_the_profile_is_refused` (`sink`: `sink_type: command`
  gives 403).

**Proposed text.**

> A resolve request MUST NOT carry a principal. The server MUST take the principal from the resolver
> token. A resolve request MUST carry `sink_type` with the value `local_file` for `local-file-1`. A server
> MUST refuse any other `sink_type` that it does not offer. A host SHOULD send a destination label, not
> an absolute path. A host MAY send a one-way hash of the path instead. A server MUST use `destination`
> for audit only. A server MUST NOT return `destination` in an error.

**Compatibility.** A server that requires an absolute path today must accept a label. The host must
change what it sends. See OQ-6 for the choice between a label and a hash.

## SC-11. Error format of the resolve endpoint

**Problem.** The profile says only that a failure returns no plaintext values (F9). The reference server
and the fake server in the host tests use different codes for the same case. For example, a batch that is
too large gives `too_many_references` at the reference server and `batch_too_large` at the fake server
(`prototype/tests/test_mcp_host_resolve.py`, `FakeServer`). A reference of another user gives
`409 unresolvable` with the reason `unknown` at the reference server and `403 forbidden` at the fake server.
A host cannot interpret a code that a standard does not define.

**Evidence.**

- F9 in `prototype/M4-FINDINGS.md`.
- Reference server tests `test_a_batch_with_one_reference_that_does_not_resolve_returns_no_value` (five
  cases), `test_a_replayed_mapping_body_does_not_resolve_a_revoked_reference` (`reasons: {"revoked": 1}`),
  `test_an_expired_resolver_token_resolves_nothing` (401) and
  `test_removing_a_principal_from_the_allowlist_stops_a_live_token` (403).
- The host accepts a code of at most 64 characters from `[A-Za-z0-9_.-]` and treats only 401 as a reason to
  renew (`resolver_client.py`, `OAuthHttpResolver._batch`). Host tests
  `test_a_revoked_reference_in_a_batch_writes_nothing` and `test_an_expired_token_is_refreshed_once_then_the_run_fails`.

**Proposed text.**

> A resolve endpoint MUST answer a failure with one JSON object `{"error": "<code>"}` and an optional
> `reasons` object that maps a reason to a count. The answer MUST NOT contain a value, a reference, an
> identifier or a destination. The endpoint MUST use these codes:
>
> | Status | `error` | Meaning |
> |---|---|---|
> | 400 | `invalid_request` | The body is malformed, empty, or has no valid destination. |
> | 401 | `invalid_token` | The token is absent, unknown, expired, for another resource, or its consent ended. The host may renew once. |
> | 403 | `insufficient_scope` | The token has no resolve scope. |
> | 403 | `ineligible_sink` | The server does not offer the `sink_type`. |
> | 403 | `not_enabled` | The server does not allow resolution for this principal. |
> | 409 | `unresolvable` | At least one reference does not resolve. `reasons` counts `malformed`, `unknown`, `revoked` and `expired`. |
> | 413 | `too_many_references` | The batch exceeds the limit. |
> | 429 | `quota_exceeded` | The principal exceeded a rate or a quota. |
>
> A host MUST treat only 401 as a reason to get a new token. A host MUST NOT show a server message to the
> model.

**Compatibility.** The codes are the codes of the reference server (read in its source). The fake server
in the host tests uses other codes, and the host still fails closed for all of them, because the host
treats every non-200 answer as a failure. The `expired` reason is new (see SC-13).

## SC-12. A refused reference inside an MCP tool call

**Problem.** The reference server refuses a reference inside a tool call as a successful MCP result with
`isError: false` and a refusal text (P14; plan section 6, M3, "Limits"). A host cannot tell from the
protocol that the server sent nothing upstream. The test host needs a configurable `--refusal-pattern` to
detect such a refusal (`prototype/README.md`, "Independent MCP test host").

**Evidence.**

- P14 in the plan.
- Host tests `test_a_structured_reference_refusal_fails_an_expected_success`,
  `test_ordinary_results_are_not_taken_for_refusals` and `test_the_refusal_pattern_is_configuration`.
- Production run (synthetic): malformed references were refused (see
  [CONFORMANCE-RESULTS.md](CONFORMANCE-RESULTS.md#end-to-end-runs)).

**Proposed text.**

> If a negotiated server refuses a tool call because a reference does not resolve, the server MUST return
> a tool result with `isError: true`. The `structuredContent` of that result SHOULD contain
> `error_code` with one of `reference_malformed`, `reference_unknown`, `reference_revoked` or
> `reference_expired`, and counts. The result MUST NOT contain a value or a reference identifier.

**Compatibility.** A server that returns `isError: false` today must change for negotiated sessions only.
Legacy sessions keep their behaviour.

## SC-13. Reference lifetime

**Problem.** A short lifetime breaks long workflows. A long lifetime widens exposure. Concept 0.5 does not
state a lifetime or what a client sees after expiry (P5). The reference server keeps a binding for 24 hours
after the last use (plan section 4, G13).

**Evidence.** P5 in the plan. Prototype test `test_expired_reference_fails_closed`.

**Proposed text.**

> A server MUST state the lifetime rule of its references in its documentation. After a reference
> expires, a resolution of it MUST fail with the reason `expired`. A server SHOULD NOT report `unknown`
> for a reference that it issued and that expired.

**Compatibility.** The reference server cannot always tell `expired` from `unknown` after the binding is
gone (plan section 6, M3, "Limits"). The text therefore uses SHOULD NOT.

## SC-14. Integrity of the issuer registry

**Problem.** Concept 0.5 states provenance integrity for the host (`HOST-INTEGRATION.md`, "Restart and
ambiguity"). The issuer also persists a registry of bindings. That registry needs the same property: a
record must be authenticated and bound to its principal (P4). The reference server found that its
registry accepted a plaintext record and a ciphertext copied from another user (plan section 4, G1, G2).

**Evidence.** P4 in the plan. Plan section 6, M0 and M2. Reference server test
`test_a_replayed_mapping_body_does_not_resolve_a_revoked_reference`.

**Proposed text.**

> An issuer MUST store its reference bindings with integrity protection. An issuer MUST bind each stored
> record to its principal, so that a record copied from another principal does not resolve. A revocation
> MUST survive a replay of an older record of the same principal.

**Compatibility.** No conflict with the wire. Server storage changes only.

## SC-15. The extension identifier

**Problem.** Concept 0.5 leaves the reverse-DNS prefix to "its controlling organization"
(`prototype/EXTENSION-PROFILE-DRAFT.md`, "Negotiation"). Until a prefix exists, each implementation
selects its own string, and two implementations do not negotiate with each other (P7). The test host
therefore takes the identifier as a required option (`--extension-id`). The reference server uses a
provisional reverse-DNS identifier of its own.

**Evidence.** P7 in the plan. `prototype/demo/mcp_host.py`, option `--extension-id`.

**Proposed text.**

> Until the MCP project assigns an identifier, implementations SHOULD accept an identifier from
> configuration. A SEP MUST name one identifier. Examples use `org.example/sensitive-references`.

**Compatibility.** The provisional identifier of the reference server stops working when the official
identifier exists. A server MAY advertise both for one release.

## SC-16. Protocol versions with an `extensions` map

**Problem.** The server capabilities of MCP protocol versions up to 2025-11-25 have no `extensions` map
(P8). A server cannot advertise the extension to a client on such a version. The reference server can
negotiate only in its stateless core (plan section 6, M3, "Advertisement").

**Evidence.** P8 in the plan. Host test
`test_without_negotiation_no_provenance_is_recorded_and_a_token_fails`. Production run (synthetic): legacy
sessions got no references.

**Proposed text.**

> Sensitive References apply only to an MCP protocol version that has an `extensions` map in the client
> and server capabilities. A server MUST NOT emit a canonical token to a client on another protocol
> version.

**Compatibility.** A client on an older protocol version gets no canonical token. This is the current
behaviour of the reference server.

## SC-17. Server text in the reference shape

**Problem.** A server notice that holds an example in the reference shape is a reference-like string that
is not a canonical token. A model can copy it into a tool call (P9). The first run of the test host against
the reference server failed for this reason (plan section 6, M3).

**Evidence.** P9 in the plan. Host test `test_a_reference_like_string_that_is_not_canonical_fails`.

**Proposed text.**

> A negotiated server MUST NOT emit text in a tool result that starts with the token marker `⟦sref:` and
> is not a canonical token that the server issued. A server MUST describe references in words in its
> own notices.

**Compatibility.** No conflict. A server must change its own documentation strings.

## SC-18. The issuer-side sink

**Problem.** Concept 0.5 defines sinks outside the issuer. In the reference server, a tool call can use a
reference as an argument. The server resolves it inside the issuer and sends the value to its own
upstream connector. The plan reads "the agent token must not automatically grant plaintext resolution
rights" as a rule for plaintext that leaves the issuer toward the agent (P1; plan section 3). Concept 0.5
does not describe this case.

**Evidence.** P1 in the plan. Plan section 3, "Compatibility with concept 0.5". Plan section 6, M1 (echo
guard on ten model-visible paths, V1 to V10).

**Proposed text.**

> An issuer MAY resolve its own references into its own outbound calls ("issuer-side sink"). The rule
> about the agent token applies to plaintext that leaves the issuer toward the host or the model.
>
> Possession of a reference MUST NOT authorize its resolution. An issuer MUST resolve a reference into an
> issuer-side sink only after an explicit authorization decision for that tool execution. The decision
> MUST use the authenticated principal of the call, the tool and the action that the issuer authorized for
> that principal, and the owner of the reference. The issuer MUST refuse the resolution if the owner of
> the reference is not the authenticated principal, or if the principal is not authorized for the tool and
> the action. This profile requires no user confirmation in addition to that decision.
>
> An issuer-side sink MUST also check that the token is exact, that the issuer issued it, and that it is
> current. A failure of one reference MUST refuse the whole call. The issuer MUST replace each resolved
> value with its reference in every model-visible result of the call, including error results.

The authorization decision is the existing decision of the issuer for the tool execution: the issuer
authenticates the principal and authorizes the tool and the action before it runs the call. SC-18 adds
one input to that decision, the owner of the reference. A reference in the arguments is never the
authorization itself. A copied reference of another principal therefore resolves nothing, also when the
call is otherwise authorized.

**Compatibility.** This text makes explicit a case that the concept does not cover. A reader who reads the
agent-token rule as a ban on all resolution under the agent token sees a conflict. The provisional v1
design decision of OQ-3 is option A with these checks. The community must still confirm this reading.
The earlier text of this entry already required that the reference belongs to the authenticated
principal (P1). This package did not find a reference server test that shows the refusal of an
authorized tool call with the reference of another principal. That case is **not verified**.

## SC-19. Hosts that cannot verify negotiation

**Problem.** A coding-agent plugin that works through hooks sees tool results. It does not see whether the
session negotiated the extension, and it has only a locally configured server name, not an authenticated
issuer (P11). It cannot meet the host rules of concept 0.5. A client hook of this kind also read an example
token in a documentation file as a reference and tried to resolve it (P6).

**Evidence.** P11 and P6 in the plan. Host tests `test_an_unobserved_or_forged_reference_is_not_sent` and
`test_unobserved_forged_token_fails_closed`.

**Proposed text.**

> A host that cannot verify the negotiated capabilities of a session and the authenticated issuer of a
> result is not a supporting host. Such a host MUST NOT declare the extension. A host MUST NOT resolve a
> token that it did not observe in a negotiated, authenticated result, also when the token occurs in a
> file that the host reads.

**Compatibility.** No conflict. The text repeats the existing rule of `SPEC-DRAFT.md`, "Host semantics",
for a class of hosts that exists today.
