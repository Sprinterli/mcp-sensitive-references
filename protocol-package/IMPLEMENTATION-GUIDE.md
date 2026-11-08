# Implementation guide

**Status: experimental.** This guide derives from the findings F1 to F13 and P1 to P16, from the
lessons of one production run on 2026-10-26 (last section), and from the implementations of Concept 0.7
(SC-21 to SC-26). Each item names its source. The rules in
SPEC-CHANGES.md are proposals. This guide does not make them normative. The guide names one product: the
browser of the tests in lessons L-a and L-b. The normative text stays browser-neutral.

## For a server implementer

### Do

1. Render canonical tokens only for a session that declared the extension with a common version. Keep the
   legacy output byte for byte for every other session (SC-16; plan section 6, M3).
2. Give each binding a random id of at least 20 characters from `[A-Za-z0-9_-]`. Never bind an id to
   another value (`WIRE-REPRESENTATION.md`; plan section 4, G3, G8).
3. Store bindings with integrity protection, and bind each record to its principal (SC-14, P4).
4. Keep revocations outside the binding record, so that a replayed record does not undo a revocation
   (plan section 6, M2).
5. Publish the complete `sensitive_references` object (all four mandatory members) in every RFC 9728
   metadata document of a resource that offers the profile, while the profile is on. Remove it while the
   profile is off (SC-02).
6. Name the resolve scope and the scope set of each sink profile in the discovery object only (`sinks`,
   and `process_scope` and `display_scope`). Keep them out of `scopes_supported` (SC-03, SC-21, F13, P15).
7. Accept only the resolve scope plus sink scopes of your discovery object, plus `openid`. Answer every
   other set with `invalid_scope`, also a sink scope without the resolve scope (SC-03, SC-21).
8. Show a consent page at every authorization request, also when a live approval exists. Name the
   account with a button to use another account, the client, the loopback host and port, the time of the
   request and one line per requested sink scope. Store the approval for subject, client, resource and the
   granted scope set. Send `frame-ancestors 'none'`, and require a single-use nonce and a same-origin
   `Origin` header on the consent post and on the account switch (SC-06).
9. Check the consent on every refresh and on every resolve (SC-06; plan section 6, Gate A finding HIGH).
10. Issue resolver tokens as their own class. Refuse them on every MCP path, also on a path that looks up
    a bearer by its suffix (SC-05, TM-3).
11. Rotate refresh tokens and bind them to the client (SC-07).
12. Resolve the whole batch or return one error without a value, a reference or an id (SC-11).
13. Return `Cache-Control: no-store` on every resolve answer (reference server test
    `test_a_consented_resolver_resolves_its_users_reference`).
14. Use `isError: true` when a tool call fails because a reference does not resolve (SC-12, P14).
15. Publish RFC 9728 metadata whose `resource` value is identical to the MCP URL. That value is the
    issuer identity (SC-01). Do not publish only a parent resource of the MCP URL (P16).
16. Check the sink scope before any lookup. Answer a missing one with `403 insufficient_scope`, the whole
    scope set in the header and the body, and an `error_description` that tells the person to sign in
    again (SC-21).
17. Keep the granted scope set on refresh. Never add a scope at a refresh (SC-21).
18. Look up a reference only in the records of the token principal. Report a reference of another person
    as `unknown` (SC-24). Send `account_hint` in the token answer and in the refresh answer, so a host can
    show the account (SC-24).
19. Write the audit event before you send a value. If the write fails, answer `503 audit_unavailable`
    (SC-25).
20. Let a person and an administrator revoke a device. Give each pair of principal and client an epoch,
    and check it in the same atomic step as each write of a credential (SC-26).
21. For `process-1`, keep only the program name in the audit, else `other`. For `display-1`, accept only
    the destination `screen` and one reference, and count each reveal in the quota (SC-22, SC-23).

### Do not

1. Do not let the agent token resolve a reference toward the host or the model (`SPEC-DRAFT.md`).
2. Do not put an example in the reference shape into a notice or an instruction text (SC-17, P9).
3. Do not return a value, a reference, an id or the destination in an error (SC-11).
4. Do not use `destination` for anything but audit (SC-10, F8).
5. Do not put the resolve endpoint on another origin than the resource (SC-04).
6. Do not issue a resolver code on the basis of a browser session alone (SC-06).
7. Do not advertise `oauth-resolver-1` or `local-file-1` before the resolve endpoint works (plan section 6,
   M4, "Server settings").
8. Do not resolve a reference into an issuer-side sink because the caller has it. Resolve it only after
   the authorization decision for the tool execution: the authenticated principal, the authorized tool and
   action, and the owner of the reference (SC-18).
9. Do not match the port of a loopback IP redirect URI. Match every other part of a redirect URI as an
   exact string (SC-20, lesson L-c).
10. Do not copy the raw redirect URI text into a Content Security Policy (lesson L-a).

## For a host implementer

### Do

1. Declare the extension and both profiles only if the host can verify the negotiated capabilities and the
   authenticated issuer of each result (SC-19, P11).
2. Record an observation only from a negotiated, authenticated tool result. Inspect text content and every
   string in `structuredContent` (`prototype/EXTENSION-PROFILE-DRAFT.md`, "Candidate host hooks").
3. Record the issuer as the RFC 9728 `resource` value. Keep the string as given, and compare it as an
   exact string. Require that the `resource` value is identical to the MCP URL (SC-01, F3, F12, RFC 9728
   section 3.3). Keep the query of the MCP URL. Get the metadata first from the `resource_metadata` URL of a
   `WWW-Authenticate` answer of the MCP URL. If the answer names none, use the path-inserted well-known URL,
   with the path and the query. Do not try the origin root. If no metadata comes back, or the server does
   not answer, do not resolve. If you add an operator option for a server that deviates, as the test host
   does with `--resource`, `--no-resource-metadata` or `--no-discovery-object`, mark the run as
   non-conformant in its report.
4. Resolve only a reference with exactly one trusted issuer, and only at the endpoint of that issuer
   (`local-file-1`, L5, L6).
5. Use a separate resolver client with Authorization Code, PKCE S256 and the `resource` parameter. Ask
   for the resolve scope and the sink scopes of the profiles that you can honour, in one request, and
   optionally `openid` (SC-03, SC-08, SC-21). Take the scope set of each sink from `sinks`.
6. Check `state`, the RFC 9207 `iss` parameter and the RFC 8414 issuer. If the server advertises
   `authorization_response_iss_parameter_supported`, refuse a response without `iss` (SC-08, F10).
7. Refuse a token response that does not grant the resolve scope (SC-03, F2).
8. Keep the resolver token in a file that only the user can read. Refuse a file that others can read
   (SC-07, F6).
9. After a 401, get one new token and try once. After a second 401, stop (SC-07, F6).
10. Resolve every batch before you write. Write a temporary file, then replace the destination
    atomically (`local-file-1`, L9 to L11).
11. Accept a 200 answer only if its keys are exactly the references of the batch (`local-file-1`, L13).
12. Return the reference-bearing content to the model. Report counts and codes only (`local-file-1`, L14,
    L15).
13. On `403 insufficient_scope`, tell the person to sign in again and allow the sink. Do not retry with the
    same token (SC-21).
14. Show the `account_hint` to the person when every reference is `unknown`. Two accounts are a common
    cause (SC-24, run E13).
15. For `process-1`: mask the command output before the model sees it, also when the command fails, is
    killed or times out. Resolve only when the command reads the value, for example through a pipe that
    the command opens. Send the program name, never the command line (SC-22).
16. For `display-1`: resolve one reference per click of the person, never while you draw. Keep the value
    out of the transcript and the export, mask a paste of it, and copy only on a second click. Make sure
    that a link the model writes cannot copy (SC-23).

### Do not

1. Do not resolve token-shaped text that you did not observe, also not from a file that you read (SC-19, P6).
2. Do not send the agent token to the resolve endpoint (SC-05).
3. Do not follow a redirect from the resolve endpoint or the token endpoint (SC-04, F4).
4. Do not accept a resolve endpoint on another origin, also not a configured one (SC-04, F4).
5. Do not select one of several authorization servers automatically (SC-08, F11).
6. Do not let the model choose the destination or the content template (`local-file-1`, L3, L4).
7. Do not show a server message to the model. Report the error code only (SC-11, F9).
8. Do not send an absolute path as `destination` if a label is enough (SC-10, F8).
9. Do not register a new client for each authorization if you can keep one client (SC-06, F5).
10. Do not use `[::1]` for the loopback redirect URI. Use `127.0.0.1` (SC-20, lesson L-b).
11. Do not accept a discovery object without all mandatory members or without the negotiated
    profiles. Do not fill a missing member from a default or from configuration (SC-02).
12. If the metadata exists but has no discovery object, stop as for an incomplete object. Use operator
    configuration only after an explicit operator statement, and label the run as not conformant (SC-02).
13. Before each request to a URL that a server supplied, resolve the host name and refuse an address
    that is not globally reachable (SC-01, fetch policy; THREAT-MODEL.md, TM-11). Do not make an
    automatic exception for a local MCP URL. Allow local targets only after an explicit operator option,
    and only for the MCP origin and configured origins. For the requests of your own HTTP client, do not
    follow redirects, do not use a proxy from the environment, connect to the checked address, and do
    not resolve the name again for the connection (SC-01). The browser that opens the authorization
    endpoint is outside this control.
14. Build the RFC 8414 well-known URL of an authorization server without a terminating "/" of the issuer
    path (RFC 8414 section 3.1). Keep a trailing slash of a longer path for the RFC 9728 URL (SC-01).
15. Do not ask for a sink scope that you cannot honour, for example the process scope on a platform where
    you cannot mask the command output (SC-21, SC-22).

## Lessons from a production run (2026-10-26)

**Status: observed (one operator run, not independently reproduced).** The operator ran the test host
against the reference server in production with synthetic data. The six lessons below came from that
run. Each lesson says whether it is guidance only or whether SC-20 makes a part of it normative. Normative
text exists only where two independent implementations must agree on the behaviour, so that they
interoperate. A rule that only one side must follow, and that the other side cannot see, stays guidance.

### L-a. The page policy of the consent page must allow the redirect to the loopback client

The consent page posts a form. The server answers the post with a 302 redirect to the loopback redirect
URI of the client. A page Content Security Policy `form-action 'self'` blocks that redirect, because the
browser checks `form-action` also on the redirect after the form post.

Observed browser behaviour. The tested browser was Google Chrome 155.0.8059.85 on macOS 27.2 (arm64). A
form POST from a page with the policy `form-action 'self'`, answered with a 302 to
`http://127.0.0.1:<port>/callback`, was blocked. The console showed: "Sending form data to '<consent
URL>' violates the following Content Security Policy directive: "form-action 'self'". The request has
been blocked." The operator saw this interactively. Headless Chrome of the same version reproduced it.
Other browsers were not tested.

- Server: list in `form-action` the loopback origin of this authorization request, and no other loopback
  origin. `'self'` can stay (the SC-20 example has `form-action 'self' http://127.0.0.1:53124`). Build the
  origin again from the parsed host and port of the redirect URI of this request, after
  that URI matched a registered one (SC-20). Never copy the raw redirect URI text into the policy: user
  information or other characters in the URI text can inject policy text.
- Security recommendation (not normative, because the host does not depend on it): give the consent
  page a `form-action` directive, and list in it no other loopback origin. Then a page that an attacker
  changes cannot post the consent decision to another origin.
- Normative part: if the consent page has a `form-action` directive, SC-20 requires that it permits the
  exact origin of the validated loopback redirect URI. A test can check this in the response headers. Whether a browser then delivers the redirect stays guidance, because
  only one browser was tested. The way to build the policy text also stays guidance.

### L-b. A browser can ignore an IPv6 literal as a policy source

Observed browser behaviour. In headless Google Chrome 155.0.8059.85 on macOS 27.2 (arm64), a consent
page with the policy `form-action 'self' http://[::1]:<port>` still blocked the redirect to
`http://[::1]:<port>`. With `form-action 'self' http://127.0.0.1:<port>`, the redirect to `127.0.0.1` went
through. This package did not find the cause. Other browsers were not tested. A server that lists the
client origin in `form-action` therefore cannot serve a client with the redirect URI
`http://[::1]:port` in this browser. The reference server refuses `[::1]` for the resolver client.

- Host: use `127.0.0.1` for the loopback redirect URI.
- Server: list exactly the loopback origin of this request in `form-action`, built from the parsed host
  and port (lesson L-a). Accept `127.0.0.1`. Refuse `[::1]` before the consent page, at registration or at
  the authorization request, with a clear error.
- Normative part: SC-20 requires that a server accepts `127.0.0.1` and recommends that a host uses it. A
  host and a server must agree on one loopback literal, so this is an interoperability rule. The
  permission to refuse `[::1]` restricts RFC 8252 section 7.3. Known limit: a device with only an IPv6
  loopback interface cannot complete the flow at such a server.

### L-c. A loopback redirect URI can use any port

RFC 8252 section 7.3 requires that the authorization server accepts a loopback redirect URI with any port.
Exact port matching breaks a host that reuses a registration with a new ephemeral port: the registered
redirect URI holds an earlier port. A new registration with the new redirect URI is not affected.

- Server: compare the redirect URI with the registered one as an exact string (RFC 3986 section 6.2.1).
  For a loopback IP redirect URI, accept any port. Every other part, also the query, must match exactly
  (RFC 8252 section 7.3, RFC 9700 section 2.1).
- Host: keep one client, and use a new free port for each authorization.
- Normative part: SC-20 repeats the RFC 8252 rule for the resolver client. A host that keeps one client
  depends on it (see OQ-4).

### L-d. The consent step must check the browser session as fully as every other step

The consent step must validate the browser session in the same way as every other browser request of the
server, with the same access control. The presence of a session cookie is not enough. In the run, two
parts of the server wrote the session with different field names. One part did not accept the session of
the other part, and the result was a login loop.

- Server: use one session check for every browser request, also for the consent page and the consent
  post. Use one session format and one writer, or one reader that accepts every writer.
- Guidance only. The host cannot see the session of the browser. SC-06 already says that a browser
  session alone issues no code.

### L-e. The consent nonce is single-use, so block a second submit

The consent nonce is single-use (PROFILE-oauth-resolver-1.md, C3). A double click sends the form twice.
The first post succeeds. The second post fails, and the user sees an error after a successful consent.

- Server: block a second submit on the page, for example disable the button after the first submit. Keep
  the nonce single-use.
- Guidance only. The behaviour is inside the page of the server.

### L-f. Refresh renews the resolver token without a new consent page

A cached resolver token expired. The host renewed it through the refresh token. No consent page appeared.
This is the expected behaviour: a refresh grant is no authorization request and has no user interaction
(RFC 6749 section 6). It keeps the granted scope set (SC-21). A new authorization request always shows the
page (SC-06).

- Host: try the refresh token before an interactive authorization. With `--no-interactive`, a host can
  still renew through refresh.
- Server: check the consent on each refresh (Do item 9), but do not ask for it again while it is valid.
- Guidance only. SC-06 and SC-07 already cover it.
