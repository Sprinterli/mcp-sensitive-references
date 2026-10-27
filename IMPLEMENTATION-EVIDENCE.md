# Implementations and evidence

**Status: Concept 0.6 draft.** This file is not normative. It describes the two implementations and the
evidence for the normative text. The full evidence record is
[protocol-package/CONFORMANCE-RESULTS.md](protocol-package/CONFORMANCE-RESULTS.md). If this file and that
record differ, the record is correct. The record ends at E11. The fix of P16 and run E12 are recorded
only in this file.

**Limited interoperability claim.** On 2026-10-27, the reference host ran against the reference server
without a non-conformant option, and the flow of `oauth-resolver-1` and `local-file-1` succeeded (E12).
This is one operator run of each step, not independently reproduced. Concept 0.6 does not claim that
either implementation conforms to the whole specification.

## Reference server: MCPGate

MCPGate is the reference server implementation. It issues Sensitive References, implements
`oauth-resolver-1` and accepts `local-file-1`. Its source is not public.

What the evidence shows:

- Only negotiated sessions get references. Legacy sessions get no references (production run E5,
  synthetic data).
- The server tests cover discovery, the resolve scope, token classes, consent, refresh rotation, whole-batch
  refusal, revocation after a replay and batch limits. This repository read 25 test functions of the
  consent module and 26 test functions of the module for negotiated references, at a revision labelled R1.
  The tests were read, not run. After a second server review, the implementer reported 58 passing test
  cases in the consent module at revision R2. This repository did not run them.

Limits:

- **The issuer identity rule (P16), fixed on 2026-10-27.** Until then, the 401 challenge of the MCP URL
  named the metadata of the base URL, whose `resource` is the base URL (E11). After a server fix on
  2026-10-27, an operator check observed that the challenge names the path-specific metadata document of
  the MCP URL, and that its `resource` is the MCP URL. The metadata document of the base URL still names
  the base URL. The operator keeps the raw output of that check (the 401 headers and both metadata
  documents); it is not in this repository, and nobody reproduced it independently. The host reports of
  E12 do not record the challenge.
- The binding of an approval to resource, scope and sink-profile set, and the names on the consent page,
  are not verified.
- The `WWW-Authenticate` header on a 401 of the resolve endpoint is not verified.
- PKCE S256 enforcement at the server and the audit event are not covered by a test.
- The SC-20 redirect rules are not covered by a test.
- The server implements an issuer-side sink. Concept 0.6 does not define it as a conformant feature
  (OPEN-QUESTIONS.md, OQ-3), and sets only an interim floor (SPEC-DRAFT.md, section 6.4). No server test
  shows the refusal of an authorized tool call with the reference of another principal, so the owner rule
  of the floor is not verified for the server.
- The server uses a provisional extension identifier of its own.

## Reference host: `prototype/demo/mcp_host.py`

The reference host is an independent MCP host in this repository. It connects to an MCP server by URL with
the MCP Python SDK client. It negotiates the extension, records issuer provenance, gets its own resolver
token and writes a local file through `local-file-1`. The resolver client is
`prototype/src/sensitive_references/resolver_client.py`.

Tested configuration (2026-10-27): Python 3.14.8, MCP Python SDK 2.3.0, commit `6cdd658` of the branch
`m7-consolidation`. Results: 133 tests passed (pytest: 133 passed, 310 subtests passed; unittest: 133 OK).
Of these, `test_mcp_host_resolve.py` has 97 tests and `test_mcp_host.py` has 13 tests. A mutation check
disabled one guard per run: 54 of 54 mutants failed at least one test.

Limits:

- MCP Python SDK 1.x was not tested.
- The host keeps provenance in memory. It fails closed after a restart. It does not implement durable
  provenance.
- The host sends the absolute path as `destination`, not a label (OQ-6).
- The host takes the file content from its configuration, not from the model (OQ-16).
- The host does not check the refusal schema of WIRE-REPRESENTATION.md, section 5. A configurable pattern
  detects a refusal inside a successful result.
- The host does not read `max_references`. It sends at most 100 references per request.
- The host checks the mode of its token cache only, not access control lists. So it meets recovery item 3
  of RESOLVER-PROFILE.md, section 11.1, only for a cache that its mode bits make readable to others; a
  cache that an access control list opens to another user is not detected.
- Recovery (RESOLVER-PROFILE.md, section 11.1): tested are a refused refresh without interaction
  (`test_a_failed_refresh_without_interaction_writes_nothing`; the deletion of the refresh token is not
  asserted), a missing token without interaction (`test_without_a_token_and_without_interaction_nothing_is_written`)
  and a cache that others can read (`test_a_cache_file_that_others_can_read_is_refused`). Not tested: a
  refused refresh followed by a new interactive authorization, a cache that the host cannot parse (the host
  treats it as empty), a lost rotated refresh token, and the host recovery after an ended approval (new
  authorization and new approval). For an ended approval, the server side (refresh and live token stop) is
  covered by a reference server test (`test_a_withdrawn_or_expired_consent_stops_refresh_and_the_live_token`,
  read, not run), and the fail-closed result of the host (no file) by run E7.
- With `--authorization-server`, the host does not check that the configured authorization server is in
  the `authorization_servers` list of the metadata (RESOLVER-PROFILE.md, section 9.1).
- Not covered by a test: the refusal to select one of several authorization servers, duplicate removal,
  the 30-second expiry margin, and a crash between the temporary write and the replace.
- The browser opens the authorization endpoint and resolves its name again. The host cannot pin that
  address (TM-11, browser-side DNS rebinding).
- The host has three operator options for servers that deviate: `--resource` (a parent resource, for P16),
  `--no-resource-metadata` and `--no-discovery-object`. A run with one of them is not conformant. The host
  report lists each such deviation.

The prototype also holds early probes against a local open-source authorization server (Keycloak): JWT
verification through JWKS, and Authorization Code with PKCE. They did not run the full
`oauth-resolver-1` flow with consent and refresh. The modules `oidc.py` and `http_resolver.py` of these
probes do not apply the fetch policy. The reference host does not use them.

## End-to-end runs

All runs used synthetic data. This repository did not repeat them.

| Run | Setting | Fact |
|---|---|---|
| E1 to E3 | local, reported | First run with one consent page and a materialized file; second run from the cache with no consent page; a forged reference produced no file. |
| E7 | local, revision R2, reported | Seven scenarios: materialization, refusal of forged and foreign references before any request, withdrawn consent, revocation before the write. |
| E4 to E6 | production, reported | Negotiated sessions got references; legacy sessions got none; malformed references were refused. |
| E8 to E10 | production, 2026-10-26, observed in one operator run, not independently reproduced | Interactive consent, cache, and refresh after expiry. The host materialized the file. Zero sentinel values in model-visible content. **All three runs used the non-conformant option `--resource`.** |
| E11 | production, 2026-10-26, observed in one operator run | The host at commit `8394a02`, without `--resource`, read the metadata that the challenge names, found the base URL as `resource`, stopped with `wrong_issuer` and resolved nothing. |
| E12 | production, 2026-10-27, observed in one operator run of each step, not independently reproduced | The host at commit `9b95733` (host code equal to the tested commit `6cdd658`), with no deviation option, discovered the MCP URL as `resource` and used it. The authorization request named the MCP URL as `resource`. Three runs: interactive consent; a run from the cache that opened no page; a run after the real expiry of the access token that got a new one with the refresh token. Each run negotiated version 1, observed one reference with provenance, sent one resolve request and materialized the file with the synthetic value. Zero sentinel values in model-visible content, in the host report and in the token cache. |

E8 to E10 show the profile flow under the known deviation P16. They are no evidence of conformance. E12
shows the same flow without a deviation.

## Lessons with limited evidence

The consent-page lessons L-a and L-b come from one operator run in one browser (Google Chrome
155.0.8059.85 on macOS 27.2, arm64). Other browsers were not tested. The `form-action` rule and the
`127.0.0.1` rule of RESOLVER-PROFILE.md, section 9.2, rest on this observation. See
[protocol-package/IMPLEMENTATION-GUIDE.md](protocol-package/IMPLEMENTATION-GUIDE.md#lessons-from-a-production-run-2026-10-26).

## Known gaps

- **E12 is one run of each step.** Nobody else reproduced it. The automated tests of this repository do
  not run against the reference server.
- **SC-20 has no automated test.** No test in this repository and no server test that this repository read
  covers the loopback redirect rules.
- **TM-11.** Browser-side DNS rebinding of the authorization endpoint is a residual risk.
- **MCP SDK 1.x untested.**
- **Single-browser observation** for the consent lessons L-a and L-b.
- No validator checks the refusal schema (SC-12) or the protected-data vectors (SC-11).
- No second independent server and no second independent host exist.
- No external security review of the protocol text exists.

## Earlier implementation experience

The design also draws on earlier client-side work: [maisecrets](https://github.com/Mcpgate-de/maisecrets)
and its predecessor design Client-Vault. That work gave evidence for out-of-model resolution, first-sighting
and origin binding, protection against stale references, fail-closed behaviour and separate resolver
authorization. It is not the protocol, and its product mechanics are not core requirements.

## Supporting material

- [protocol-package/SPEC-CHANGES.md](protocol-package/SPEC-CHANGES.md): the problem, evidence and
  compatibility of each SC entry.
- [protocol-package/PROFILE-oauth-resolver-1.md](protocol-package/PROFILE-oauth-resolver-1.md) and
  [protocol-package/PROFILE-local-file-1.md](protocol-package/PROFILE-local-file-1.md): each profile rule
  with its test.
- [protocol-package/THREAT-MODEL.md](protocol-package/THREAT-MODEL.md): TM-1 to TM-12 with evidence. TM-13
  (SECURITY-MODEL.md) is new in Concept 0.6 and has no evidence entry yet.
- [protocol-package/SEP-READINESS.md](protocol-package/SEP-READINESS.md): the state of each SEP item.
- [prototype/M4-FINDINGS.md](prototype/M4-FINDINGS.md): findings F1 to F13.
