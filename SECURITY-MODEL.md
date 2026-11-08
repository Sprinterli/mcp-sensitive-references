# Security model

**Status: Concept 0.7 draft, normative core.** The conventions and terms of
[SPEC-DRAFT.md](SPEC-DRAFT.md#1-conventions) apply. The full threat analysis with its evidence is in
[protocol-package/THREAT-MODEL.md](protocol-package/THREAT-MODEL.md). That file is supporting rationale.

## 1. Objective

Sensitive References avoid putting a server-classified sensitive value into model-visible content only
because an authorized later action needs that value.

## 2. Trust boundaries

- The issuer controls the plaintext and the lifecycle of each reference.
- The model is untrusted with plaintext, with resolver credentials and with the selection of an issuer.
- The resolver authenticates as a stable principal. The issuer authorizes each resolution.
- The host keeps trusted provenance and protects the input of an eligible sink.

## 3. Required controls

These controls are the core of the design. They bind every profile. A profile cannot relax them.

1. **Trusted provenance.** A host trusts a reference only if it observed the reference in an
   authenticated MCP result of a negotiated server, and recorded it outside model text. The issuer comes
   from the authenticated connection, not from reference text or model text (HOST-INTEGRATION.md,
   sections 2 and 3).
2. **Fail closed on loss or ambiguity.** At the host, an unobserved or ambiguous reference fails. At the
   issuer, an unknown, revoked, expired, wrong-principal or unauthorized reference fails. Loss of trustworthy provenance fails closed.
3. **Authorization separate from possession.** A reference has no bearer authority. The issuer authorizes
   each resolution independently from possession of the reference. The ordinary agent token does not
   automatically grant plaintext resolution rights (SPEC-DRAFT.md, section 5.2).
4. **No rebinding.** An issuer does not bind an identifier to another value generation. The issuer
   registry is integrity-protected and bound to its principal (SPEC-DRAFT.md, section 5.4).
5. **Out-of-model resolution.** A sink does not return resolved plaintext in an ordinary model-facing
   result. No result that the model can read contains a resolved value. Resolve-endpoint answers, refusal
   results, sink reports as the sink profile sets them, and host error texts and logs contain no protected data (SPEC-DRAFT.md,
   section 8). Ordinary issuer results and the model-facing sink result carry references by design.
6. **All or nothing.** A sink resolves every reference of one write, or leaves the destination unchanged.
7. **Separate credentials.** A resolver token does not authorize an MCP request. An agent token does not
   authorize a resolve request (RESOLVER-PROFILE.md, section 8).

## 4. Assets added by the profiles

- The resolver access token and the resolver refresh token.
- The consent record: one approval for one subject, one resolver client, one resource and one granted
  scope set (the resolve scope and the sink scopes that the user allowed).
- The sink scopes. A token with a sink scope releases values into a command or onto a screen.
- The resolve endpoint, which returns plaintext to a program outside the model.
- The token cache of the host.
- The destination: the local file that receives plaintext and its path, the command that reads a value,
  or the screen that shows it.
- The audit events of the resolve endpoint.

## 5. Threats and controls

| Id | Threat | Control | Residual risk |
|---|---|---|---|
| TM-1 | A local program that can open the browser of the user gets a resolver token silently, or reuses a stored approval. | A consent page at every authorization request; no stored approval and no browser session alone issues a code. The page names the account (with an action to use another account), the client, the loopback host and port, the time of the request and each requested sink scope. No framing, single-use nonce, same-origin `Origin` (RESOLVER-PROFILE.md, section 10). Revocation per device (section 10.4). | A user can approve a malicious client with a plausible name, also when the page names the time and the port. The page does not show the destination. |
| TM-2 | A resolver token works as an agent token, or the reverse. | Separate token classes (RESOLVER-PROFILE.md, section 8). | A new agent-token reader in a server must keep the refusal. |
| TM-3 | An agent-token reader accepts a bearer by its suffix. | The classes differ by more than the scope (RESOLVER-PROFILE.md, section 8). | A server without such a separation needs another control. |
| TM-4 | One request mixes the resolve scope with agent scopes, or gets a sink scope without the resolve scope. | The authorization server accepts only the resolve scope with sink scopes of its discovery object (and `openid`); every other set is `invalid_scope`. The scopes are not in `scopes_supported` (RESOLVER-PROFILE.md, section 5). | A host learns the scopes from the discovery object (TM-5). |
| TM-5 | The host records the wrong issuer, or resolves at the wrong endpoint (mix-up, redirect, cross-origin endpoint). | Exact issuer identity, RFC 9728 `resource` identical to the MCP URL, endpoint on the resource origin, no redirects, RFC 8414 and RFC 9207 checks (RESOLVER-PROFILE.md, sections 3 to 9). | The issuer identity is a URL, not a cryptographic identity. |
| TM-6 | The sink writes partial output, or the server releases values that the host then discards. | All-or-nothing write (LOCAL-FILE-PROFILE.md, section 4). | With split batches, the server releases the values of each successful request. A crash between the temporary write and the replace can leave a temporary file with plaintext. |
| TM-7 | The destination path tells the server the layout of the local file system. | The host sends a label. The server uses the destination for audit only (RESOLVER-PROFILE.md, section 12). | A host that sends an absolute path discloses it. |
| TM-8 | Another user or process reads the token cache. | Owner-only cache, rotating refresh tokens bound to the client (RESOLVER-PROFILE.md, section 11). | A process of the same user can read the cache. The tokens are not sender-constrained (OQ-5). |
| TM-9 | A host that cannot verify negotiation resolves reference-shaped text from a file or a page. | Such a host is not a supporting host (SPEC-DRAFT.md, section 6.2). | A server cannot tell a false declaration. A false declaration gives references but no plaintext. |
| TM-10 | A copied reference of another principal is used inside the issuer (issuer-side use). | Interim floor until OQ-3 is decided: possession is not authorization, the owner must be the authenticated principal, the reference must be exact and current, one failure refuses the whole call, and the issuer puts the reference back in every model-visible result (SPEC-DRAFT.md, section 6.4). | An injected instruction can still move a value of the same principal between tools that this principal may use. OQ-3 stays open. |
| TM-11 | A server names a URL that makes the host send a request into a private network (SSRF). | Fetch policy with a connection to the checked address (RESOLVER-PROFILE.md, section 7). | The browser opens the authorization endpoint and resolves its name again. A DNS server can then give the browser a non-public address (DNS rebinding of the browser). The fetch policy need not cover the MCP URL, which the operator gives, and an MCP client library can resolve that name again for the session. |
| TM-12 | A credential in the query of the MCP URL reaches the authorization server and the token cache. | A server SHOULD NOT put a credential into the query (HOST-INTEGRATION.md, section 2). | A host cannot tell a credential from a tenant name. |
| TM-13 | A model or a local process plants an observation in a durable provenance store, so that a forged reference gets an issuer. | The host checks each stored observation for integrity and origin. The model cannot read or use the integrity key (HOST-INTEGRATION.md, section 3). | No integrity mechanism is defined (OQ-7). A process with the privileges of the host can plant provenance. |
| TM-14 | A command that receives a value prints it, and the model reads the output. | `process-1`: the destination is the program name; the host masks the command output before the model sees it, also on the failure path; the host resolves only when the command reads the value; a separate sink scope that a person can leave out (PROCESS-PROFILE.md). | Any local process of the person that holds a token with the process scope gets the full value. The server trusts the program name that the host sends, not what the program does. A masking that fails on a path of the host shows the value. |
| TM-15 | A value on the screen of the person reaches the model, a transcript, an export or a person who sees the screen. | `display-1`: destination `screen`, one reference per request, only on a click of the person, never while the host draws; the value never goes to the model, a transcript or an export; a paste of it is masked back; copy only on a second click; one audit event per reveal, counted in the quota; a separate sink scope (DISPLAY-PROFILE.md). | Any local process of the person that holds a token with the display scope gets the full value. Anyone who sees the screen sees the value. A copied value is in the clipboard of the system. |

## 6. Limits

This design does not protect plaintext after an authorized sink receives it. It does not protect against a
malicious process with the same operating-system privileges as the resolver, or against a compromised host
runtime. Generic shell safety, filesystem policy, output echo control, quotas, audit and sender constraint
belong to profiles or to the integration.

The browser path of an interactive authorization is outside the fetch policy of the host (TM-11). A host
cannot pin the address that the browser connects to.

An echo guard can recognize a resolved value in known encodings. It does not prove absence. A transformed
echo passes.
