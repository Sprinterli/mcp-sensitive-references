# Implementations and evidence

**Status: Concept 0.7 draft.** This file is not normative. It describes the three implementations and the
evidence for the normative text. The full evidence record is
[protocol-package/CONFORMANCE-RESULTS.md](protocol-package/CONFORMANCE-RESULTS.md). If this file and that
record differ, the record is correct. The fix of P16 and run E12 are recorded only in this file.

**Limited interoperability claim.** On 2026-10-27, the reference host ran against the reference server
without a non-conformant option, and the flow of `oauth-resolver-1` and `local-file-1` succeeded (E12).
This is one operator run of each step, not independently reproduced. On 2026-11-08, the second host showed
a value through `display-1` against the reference server (E13, one operator run, not independently
reproduced). Concept 0.7 does not claim that any implementation conforms to the whole specification.

## Reference server: MCPGate

MCPGate is the reference server implementation. It issues Sensitive References, implements
`oauth-resolver-1` and accepts `local-file-1`, `display-1` and `process-1`. Its source is not
public. Revision R3 (versions 2.0.3824 and 2.0.3826 of 2026-11-08) is the revision of Concept 0.7. Revision R4
(version 2.0.3830 of 2026-11-08) adds two changes to R3: the identifier `process-1`, and the binding of the
stored approval to resource and scope set. Revision R5 (version 2.0.3837 of 2026-11-09) adds two changes
to R4: a missing resolve scope names the whole scope set of the sink, and the consent page has a new layout
and new wording, with a test for the time of the request.

What R3, R4 and R5 do, as their tests and their source show (read at the release tags of 2.0.3826,
2.0.3830 and 2.0.3837, not run by this repository):

- **Discovery.** The live metadata document of the base URL at R4, fetched on 2026-11-08 from version
  2.0.3831. Between the release tags of 2.0.3830 and 2.0.3831 no server source file changed. The same
  document, fetched on 2026-11-09 from version 2.0.3837 (R5), has the same members and values. The object
  is formatted, and the host is replaced with `mcp.example.com`. Nothing else is left out:

  ```json
  {
    "resource": "https://mcp.example.com",
    "authorization_servers": [
      "https://mcp.example.com"
    ],
    "scopes_supported": [
      "mcp",
      "openid",
      "email"
    ],
    "bearer_methods_supported": [
      "header"
    ],
    "mcp": {
      "endpoint": "https://mcp.example.com/mcp",
      "protocol": "mcp",
      "version": "2024-11-05"
    },
    "sensitive_references": {
      "resolve_endpoint": "https://mcp.example.com/sensitive-references/resolve",
      "resolve_scope": "sensitive-references.resolve",
      "process_scope": "sensitive-references.resolve.process",
      "display_scope": "sensitive-references.resolve.display",
      "resolver_profiles": [
        "oauth-resolver-1"
      ],
      "sink_profiles": [
        "display-1",
        "local-file-1",
        "process-1"
      ],
      "sinks": {
        "display-1": {
          "sink_type": "display",
          "scopes": [
            "sensitive-references.resolve",
            "sensitive-references.resolve.display"
          ]
        },
        "local-file-1": {
          "sink_type": "local_file",
          "scopes": [
            "sensitive-references.resolve"
          ]
        },
        "process-1": {
          "sink_type": "process",
          "scopes": [
            "sensitive-references.resolve",
            "sensitive-references.resolve.process"
          ]
        }
      }
    }
  }
  ```

  Since R4 the process profile has the identifier `process-1` (OQ-21). The vendor-prefixed identifier
  of R3 is gone, with no alias. A resolve request names the `sink_type` `process`, not the profile, so
  the request does not change. The audit row names `process-1`. Reference server tests (R4)
  `test_discovery_names_the_process_sink_process_1_and_not_the_former_name`,
  `test_a_process_resolve_is_audited_as_process_1` and
  `test_a_profile_identifier_sent_as_the_sink_type_is_refused`. The second host at release 0.9.1 looked for
  the identifier of R3 in `sink_profiles`, so it refused the process sink of R4 before any request. Since
  release 0.9.4 it accepts `process-1`
  ([protocol-package/PROFILE-process-1.md](protocol-package/PROFILE-process-1.md)).
  The code of the server still calls the field name provisional; Concept 0.7 fixes it.
- **Sink scopes.** A token without the scope of the sink gets `403 insufficient_scope` before any lookup,
  with no value and no audit row. For the display sink, the header is
  `Bearer error="insufficient_scope", scope="sensitive-references.resolve sensitive-references.resolve.display", error_description="This sign-in does not allow real values on your screen. Sign in again and allow the screen on the consent page."`,
  and the body carries `error`, `error_description` and `scope` with the same values. For the process sink,
  the shape is the same with the process scope and the text "This sign-in does not allow real values in
  commands. Sign in again and allow commands on the consent page." The answer carries
  `Cache-Control: no-store`. Since R4, a token without the resolve scope gets the same shape with
  `scope="sensitive-references.resolve"` and the text "This sign-in does not allow real values. Sign in
  again and allow the program on the consent page." At R4 this answer named only the resolve scope, also
  for a process or a display request. Since R5 the server then reads the body, for at most 2 seconds, and
  names the resolve scope and the scope of the sink in the body: for `process`
  `scope="sensitive-references.resolve sensitive-references.resolve.process"`, for `display` the same with
  the display scope. A body without a known sink, or a body that does not arrive in time, gets the resolve
  scope only. No value, no lookup and no audit event. Another `sink_type` gets `403 ineligible_sink`. A
  display request with another destination than `screen`, or with not exactly one reference, gets `400`.
- **Consent.** A consent page at every authorization request. At R5 the title is "Allow this program to
  use your real values?", with the lead line "The values go to this computer, never to the AI model." One
  line per requested sink scope follows: "Write values into files", "Use values in commands it runs — it
  says it masks the command output before the AI sees it" and "Show values on your screen — it says it
  never gives them to the AI". The rows are "Signed in as" (the account, with a "Use another account"
  button in the same row), "Program" (the name the client gave itself, tagged "self-declared"), "Client"
  (the client id), "Resource", "Returns to" (the loopback host and port) and "Requested" (the time of the
  request in UTC). The line "Only allow this if you just started a sign-in from this program." stands
  directly above the Allow and Deny buttons. The title does not carry the name of the client. The button
  to use another account shows only where the server has its own sign-in page; else the page names the
  account and offers no switch. Since R4 the code and the stored approval are bound to subject, client,
  resource and the exact scope set that the page named. A token request that names another resource gets
  `invalid_target`, and a `scope` in the token request adds nothing. A token and a refresh work only while an approval for their own resource
  and scope set holds, for at most 180 days from the grant time of that approval. One record keeps at
  most 8 approvals per person and client.
- **People.** Every person with an account (members and guests) may use the resolver. Administrators keep
  a block list per user. Service accounts and synthetic identities are refused.
- **References per principal.** The server looks up a reference in the pseudonym map of the token principal
  (lifetime 24 hours). A reference of another account is `409 unresolvable` with the reason `unknown`.
- **Account hint.** Token and refresh answers carry `account_hint`: at most three first characters of the
  local part (never more than half of it), an ellipsis and the whole domain, for example
  `al…@example.com` for `alice@example.com`. The refresh mints through the same function as the token answer.
- **Audit.** No value leaves without its audit row; else `503 audit_unavailable`. The audit of a process
  resolve keeps the last path part of the destination if the destination has no white space and that part
  is a plain name (`[A-Za-z0-9][A-Za-z0-9._+-]{0,63}`), else `other`. Each reveal of the display sink
  writes one row and counts in the daily quota. If a reference is revoked or the approval is withdrawn
  while the request runs, the server writes a second row with the stage `withheld`, without a value, and
  sends no value.
- **Revocation.** The person (on a connections page) and an administrator revoke a device. Each pair of
  principal and client has an epoch, written with an atomic compare-and-write. A token is valid only while
  the token index of its client names it, carries the overflow marker, or does not decode. The marker
  replaces the entries when the index holds more than 200; in both of these cases a revocation walks every
  token record. A token whose index cannot be read is refused.

The rows of [protocol-package/PROFILE-oauth-resolver-1.md](protocol-package/PROFILE-oauth-resolver-1.md),
[protocol-package/PROFILE-process-1.md](protocol-package/PROFILE-process-1.md) and
[protocol-package/PROFILE-display-1.md](protocol-package/PROFILE-display-1.md) name the tests.

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
- The binding of the stored approval to resource and scope set, and the resource on the consent page,
  are covered by R4 tests (protocol-package/PROFILE-oauth-resolver-1.md, C5 and C7). The names of account,
  client, loopback host and port and the sink lines on the page are covered by R3 tests, with the wording
  of R5. The time on the page is covered by R5 tests.
- The `WWW-Authenticate` header on a 401 of the resolve endpoint is not verified.
- PKCE S256 enforcement at the server and the audit event are not covered by a test.
- The SC-20 rules for `form-action` and for `[::1]` are covered by R3 tests. The rule "any loopback port"
  is not covered by a test that this repository read.
- The R3 tests were read at the release tag. The pipeline of that tag does not run the unit tests, so this
  repository has no run record of them.
- The server implements an issuer-side sink. Concept 0.7 does not define it as a conformant feature
  (OPEN-QUESTIONS.md, OQ-3), and sets only an interim floor (SPEC-DRAFT.md, section 6.4). No server test
  shows the refusal of an authorized tool call with the reference of another principal, so the owner rule
  of the floor is not verified for the server.
- The server uses a provisional extension identifier of its own.

## Reference host: `prototype/demo/mcp_host.py`

The reference host is an independent MCP host in this repository. It connects to an MCP server by URL with
the MCP Python SDK client. It negotiates the extension, records issuer provenance, gets its own resolver
token and writes a local file through `local-file-1`. Since Concept 0.7 it also runs a command through
`process-1` (POSIX) and shows a value on the terminal through `display-1`. The prototype also holds a
demo-level issuer, `prototype/src/sensitive_references/issuer_server.py`, which implements the server
rules of Concept 0.7. The resolver client is
`prototype/src/sensitive_references/resolver_client.py`.

Tested configuration of Concept 0.7 (2026-11-08): Python 3.14.8 on macOS, MCP Python SDK 2.3.0, commit
`65f17e5` of the branch `concept-0.7`. Results: 212 tests passed (pytest: 212 passed, 393 subtests passed;
unittest: 212 OK). Of these, `test_issuer_server.py` has 38 tests and `test_concept_07_host.py` has 41.
Round 10 of the mutation check disabled each guard of the Concept 0.7 rules once: 60 of 60 mutants failed
at least one test. The whole probe (54 mutants of rounds 2 to 9 and 60 of round 10) killed 114 of 114 (two round-3 mutants
moved to the new text of `materialize` first).

What the prototype implements of Concept 0.7, tested offline only:

- Discovery: the host refuses an object without valid `sinks` and takes the scope set from `sinks`. It asks
  for the scopes of every sink of the run in one authorization.
- The issuer: `sinks`, `process_scope` and `display_scope` (it publishes `process-1` only); the scope
  combinations and `invalid_scope`; `403 insufficient_scope` before any lookup, with no value and no audit
  event; a refresh that keeps the granted set; consent at every authorization with the account, a switch
  action, the client, the loopback host and port, the time, the resource and one line per sink scope;
  references per principal; `account_hint`; `503 audit_unavailable`; revocation per device with an epoch.
- `process-1`: the program name as destination, a resolve only when the command reads the value, a stop
  after a failed resolve, and the masked output before the model, also after a failure, a signal or a
  timeout.
- `display-1`: one reference per request to `screen`, only after an explicit action of the person on the
  terminal, never in the report or the transcript.

Demo level, and not covered: the issuer has fixture accounts, no identity provider and no persistence. The
`process-1` mask knows clear text, percent-encoding and base64 only, and there is no sandbox; a program that
changes the value in another way, writes it to a file or sends it to the network passes the mask.
`process-1` runs on POSIX only. Where a reference stands in an argument, the program gets the value in its
argument list. `display-1` draws on the terminal, which a screen share or a terminal log can see. No run of
the prototype against the reference server at R3 is recorded.

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
- Until Concept 0.7 the host did not read `max_references`. Since commit `65f17e5` it uses the published
  limit, else 100.
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

## Second host: maisecrets

[maisecrets](https://github.com/Mcpgate-de/maisecrets) is a public plugin for coding agents. Release 0.9.0
added the process sink; release 0.9.1 added the display click (both 2026-11-08). Release 0.9.4 (2026-11-09)
accepts `process-1`, reads `sinks` and labels a reference on the screen with the display of the server.
This repository read its source and its test names at the tag `v0.9.4` (commit `03a51ef`). The package
of release 0.9.4 on PyPI holds only the detection library of the plugin, not the code below, so the
citations refer to that tag. This repository did not run its tests.

What the source and the tests show:

- It resolves references from a server in the user scope into the content of a file tool (`local_file`,
  destination the path), into a Bash command (`process`, destination the program name: the base name of
  the first word after `NAME=value` assignments) and onto the screen (`display`, destination `screen`, one
  reference per click) (`maisecrets/sref_client.py`, `maisecrets/sref_hooks.py`,
  `claude-mod/show-values.mjs`, `maisecrets/show_values.py`; its threat model, C27, C31 and C32).
- Its login asks for the resolve scope, the process scope on macOS and Linux (where it masks command
  output), and the display scope where the server names one.
- A command gets its value through a FIFO. A child process resolves only after the command opened it, so a
  refused command costs no resolve. A failed resolve stops the command (exit status 97).
- A display resolves only on a click, at most 20 per session id of the client process. The client
  counts them in the memory of the drawing module; a `/clear`, a resume and a new process start the count
  again. The value stays in the memory of the drawing
  module. A copy needs a second click on the shown value, and each copy link carries a random part that
  only the drawing holds.

Limits:

- It declares no extension to the server. It applies its own rule in place of negotiated provenance: a
  reference resolves only if a result of a server in the user scope showed it in the same session in the
  last 24 hours. So it is not a supporting host (SPEC-DRAFT.md, section 6.2).
- It reads the discovery object from the path-inserted well-known URL only, not from the challenge first
  (RESOLVER-PROFILE.md, section 3; `maisecrets/sref_client.py`, line 103). It reads `sinks`, but the members
  `process_scope` and `display_scope` win over the scope set of `sinks`, and it does not refuse an object
  without `sinks` (lines 113 to 127). So it does not meet the host rules of RESOLVER-PROFILE.md, section 4,
  for `sinks`.
- It masks the output of a failed command in one client through an EXIT trap that ends the command with
  status 0. Its threat model (C27) lists the paths where a printed value still reaches the model: a
  command with its own EXIT trap, `exec`, a killed command and a command past the timeout of the client.
  On these paths it does not meet PROCESS-PROFILE.md, section 5, rule 2.
- Since release 0.9.3 it keeps `account_hint` from the token and the refresh answer and prints it in the
  output of its status and login command (`maisecrets/sref_client.py`, lines 237, 241 to 247 and 328;
  `maisecrets/cli.py`, lines 983 to 984 and 1010 to 1011; test
  `test_the_login_keeps_the_masked_account_and_a_refresh_keeps_it`). The coding agent runs that command
  as a tool, so the hint is in a tool result that the model reads, unless the output masking of the host
  replaces it. RESOLVER-PROFILE.md, section 11.2, says that a host MUST NOT give the hint to the model.
  This repository read that in the source and did not run it.
- A process of the same user can open the FIFO of a command before the command does: the FIFO has mode
  0600 in a per-user directory with mode 0700. That process then causes the resolve and reads the value
  (PROFILE-process-1.md, PR20).
- It takes the program name from the first word at white space, without the quoting rules of the shell
  (PR11).
- Its login asks for the display scope also in a client where it draws no value
  (`maisecrets/sref_client.py`, lines 88 to 90). It does not meet DISPLAY-PROFILE.md, section 1, rule 4
  (PROFILE-display-1.md, DS4).

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
| E13 | production, 2026-11-08, observed in one operator run, not independently reproduced | The second host at release 0.9.1 against the reference server at R3. First, a resolve got `409 unresolvable` with the reason `unknown`: the person had signed in to the resolver with one account and had an MCP session with another account. After the person signed in to the resolver with the same account, a click showed the value on the screen (`display-1`). |

E8 to E10 show the profile flow under the known deviation P16. They are no evidence of conformance. E12
shows the same flow without a deviation. No end-to-end run of the process sink against the reference server
is recorded.

## Lessons with limited evidence

The consent-page lessons L-a and L-b come from one operator run in one browser (Google Chrome
155.0.8059.85 on macOS 27.2, arm64). Other browsers were not tested. The `form-action` rule and the
`127.0.0.1` rule of RESOLVER-PROFILE.md, section 9.2, rest on this observation. See
[protocol-package/IMPLEMENTATION-GUIDE.md](protocol-package/IMPLEMENTATION-GUIDE.md#lessons-from-a-production-run-2026-10-26).

## Known gaps

- **E12 and E13 are one run of each step.** Nobody else reproduced them. The automated tests of this
  repository do not run against the reference server.
- **The R3 tests were read, not run.**
- **No end-to-end run of `process-1` against the reference server.** The prototype runs it offline only.
- **The reference host implements Concept 0.7 at demo level, tested offline only** against the prototype
  issuer, not against the reference server. Before commit `65f17e5` it did not read `sinks` and implemented
  neither `process-1` nor `display-1`.
- **The second host is not a supporting host** (no extension, its own session rule).
- **SC-20 "any loopback port" has no reference server test** that this repository read. The prototype
  issuer has one.
- **TM-11.** Browser-side DNS rebinding of the authorization endpoint is a residual risk.
- **MCP SDK 1.x untested.**
- **Single-browser observation** for the consent lessons L-a and L-b.
- No validator checks the refusal schema (SC-12) or the protected-data vectors (SC-11).
- No second independent server and no second supporting host exist.
- No external security review of the protocol text exists.

## Earlier implementation experience

The design also draws on earlier client-side work: maisecrets before release 0.9.0 and its predecessor
design Client-Vault. That work gave evidence for out-of-model resolution, first-sighting
and origin binding, protection against stale references, fail-closed behaviour and separate resolver
authorization. It is not the protocol, and its product mechanics are not core requirements.

## Supporting material

- [protocol-package/SPEC-CHANGES.md](protocol-package/SPEC-CHANGES.md): the problem, evidence and
  compatibility of each SC entry.
- [protocol-package/PROFILE-oauth-resolver-1.md](protocol-package/PROFILE-oauth-resolver-1.md),
  [protocol-package/PROFILE-local-file-1.md](protocol-package/PROFILE-local-file-1.md),
  [protocol-package/PROFILE-process-1.md](protocol-package/PROFILE-process-1.md) and
  [protocol-package/PROFILE-display-1.md](protocol-package/PROFILE-display-1.md): each profile rule with
  its test.
- [protocol-package/THREAT-MODEL.md](protocol-package/THREAT-MODEL.md): TM-1 to TM-12, TM-14 and TM-15 with
  evidence. TM-13 (SECURITY-MODEL.md) has no evidence entry yet.
- [protocol-package/SEP-READINESS.md](protocol-package/SEP-READINESS.md): the state of each SEP item.
- [prototype/M4-FINDINGS.md](prototype/M4-FINDINGS.md): findings F1 to F13.
