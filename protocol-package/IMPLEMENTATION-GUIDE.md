# Implementation guide

**Status: experimental.** This guide derives from the findings F1 to F13 and P1 to P16. Each item names
its source. The rules in SPEC-CHANGES.md are proposals. This guide does not make them normative.

## For a server implementer

### Do

1. Render canonical tokens only for a session that declared the extension with a common version. Keep the
   legacy output byte for byte for every other session (SC-16; plan section 6, M3).
2. Give each binding a random id of at least 20 characters from `[A-Za-z0-9_-]`. Never bind an id to
   another value (`WIRE-REPRESENTATION.md`; plan section 4, G3, G8).
3. Store bindings with integrity protection, and bind each record to its principal (SC-14, P4).
4. Keep revocations outside the binding record, so that a replayed record does not undo a revocation
   (plan section 6, M2).
5. Publish the `sensitive_references` object in every RFC 9728 metadata document while the profile is on.
   Remove it while the profile is off (SC-02).
6. Name the resolve scope in the discovery object only. Keep it out of `scopes_supported` (SC-03, F13, P15).
7. Refuse an authorization request that mixes the resolve scope with other scopes (SC-03).
8. Show a consent page for the first authorization of each pair of user and client. Protect it against
   framing and cross-site request forgery (SC-06).
9. Check the consent on every refresh and on every resolve (SC-06; plan section 6, Gate A finding HIGH).
10. Issue resolver tokens as their own class. Refuse them on every MCP path, also on a path that looks up
    a bearer by its suffix (SC-05, TM-3).
11. Rotate refresh tokens and bind them to the client (SC-07).
12. Resolve the whole batch or return one error without a value, a reference or an id (SC-11).
13. Return `Cache-Control: no-store` on every resolve answer (reference server test
    `test_a_consented_resolver_resolves_its_users_reference`).
14. Use `isError: true` when a tool call fails because a reference does not resolve (SC-12, P14).
15. Publish RFC 9728 metadata whose `resource` value is identical to the MCP URL. That value is the
    issuer identity (SC-01). Do not publish only a parent resource of the MCP URL: the reference server
    does that, and it is not conformant (P16).

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

## For a host implementer

### Do

1. Declare the extension and both profiles only if the host can verify the negotiated capabilities and the
   authenticated issuer of each result (SC-19, P11).
2. Record an observation only from a negotiated, authenticated tool result. Inspect text content and every
   string in `structuredContent` (`prototype/EXTENSION-PROFILE-DRAFT.md`, "Candidate host hooks").
3. Record the issuer as the RFC 9728 `resource` value. Compare it as an exact string. Require that the
   `resource` value is identical to the MCP URL (SC-01, F3, F12, RFC 9728 section 3.3). If you add an
   operator option for a server that deviates, as the test host does with `--resource`, mark it as
   non-conformant.
4. Resolve only a reference with exactly one trusted issuer, and only at the endpoint of that issuer
   (`local-file-1`, L5, L6).
5. Use a separate resolver client with Authorization Code, PKCE S256, the `resource` parameter and the
   resolve scope alone (SC-08).
6. Check `state`, the RFC 9207 `iss` parameter and the RFC 8414 issuer (SC-08, F10).
7. Refuse a token response that does not grant the resolve scope (SC-03, F2).
8. Keep the resolver token in a file that only the user can read. Refuse a file that others can read
   (SC-07, F6).
9. After a 401, get one new token and try once. After a second 401, stop (SC-07, F6).
10. Resolve every batch before you write. Write a temporary file, then replace the destination
    atomically (`local-file-1`, L9 to L11).
11. Accept a 200 answer only if its keys are exactly the references of the batch (`local-file-1`, L13).
12. Return the reference-bearing content to the model. Report counts and codes only (`local-file-1`, L14,
    L15).

### Do not

1. Do not resolve token-shaped text that you did not observe, also not from a file that you read (SC-19, P6).
2. Do not send the agent token to the resolve endpoint (SC-05).
3. Do not follow a redirect from the resolve endpoint or the token endpoint (SC-04, F4).
4. Do not accept a discovered resolve endpoint on another origin (SC-04, F4).
5. Do not select one of several authorization servers automatically (SC-08, F11).
6. Do not let the model choose the destination or the content template (`local-file-1`, L3, L4).
7. Do not show a server message to the model. Report the error code only (SC-11, F9).
8. Do not send an absolute path as `destination` if a label is enough (SC-10, F8).
9. Do not register a new client for each authorization if you can keep one client, because each new client
   causes a new consent page (SC-06, F5).
