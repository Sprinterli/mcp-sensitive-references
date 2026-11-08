# Sink profile `display-1`

**Status: Concept 0.7 draft, normative profile.** The conventions and terms of
[SPEC-DRAFT.md](SPEC-DRAFT.md#1-conventions) apply. This profile builds on the core documents and on
[RESOLVER-PROFILE.md](RESOLVER-PROFILE.md). It does not need any other document.

The sink shows the plaintext value of one reference on the screen of the person, after the person clicks
the reference. The value never goes to the model. The evidence for each rule is in
[protocol-package/PROFILE-display-1.md](protocol-package/PROFILE-display-1.md).

## 1. Preconditions

1. The host MUST resolve only if the negotiated intersection holds `display-1` and a resolver profile that
   the host supports. Version 1 defines one resolver profile, `oauth-resolver-1`.
2. The discovery object of the resolver profile MUST list `display-1` in `sink_profiles` and in `sinks`
   (RESOLVER-PROFILE.md, section 4). Else the host MUST NOT resolve.
3. `display-1` requires a sink scope, the *display scope*. The discovery object names it in
   `sinks.display-1.scopes` and in `display_scope`. The host MUST resolve for this profile only with a
   resolver token that holds the resolve scope and the display scope.
4. The host MUST ask for the display scope only where it meets sections 4 and 5: where it draws the value
   locally and keeps it out of every text that the model, a transcript or an export can read.

## 2. Which references the sink resolves

1. The sink MUST resolve a reference only if the host observed it in a negotiated, authenticated result,
   and only if it has exactly one trusted issuer (HOST-INTEGRATION.md, section 3).
2. The sink MUST send a reference only to the resolve endpoint of its own issuer.
3. The sink MUST match references by exact code points.

## 3. Wire values

1. The sink MUST send `sink_type` with the value `display`.
2. The sink MUST send `destination` with the exact value `screen`.
3. A request MUST hold exactly one reference.

A server MUST answer a `display` request with another `destination`, or with not exactly one reference,
with `400 invalid_request`.

## 4. When the sink resolves

1. The host MUST resolve a reference only after an explicit action of the person on that reference, for
   example a click. One action resolves one reference.
2. The host MUST NOT resolve while it draws text, while it scrolls, or for text that is not on the screen.
3. A model, a tool result or a text that the model wrote MUST NOT be able to start a resolve.
4. The host SHOULD limit the number of resolve requests of this profile per session.

## 5. Output boundary

1. The host MUST show the value on the screen only. It MUST NOT put the value into model-visible content,
   a transcript, a log, an export or a file.
2. The host MUST keep the released value for the session, so that a paste of it into a prompt or a tool
   output is masked back to the reference before the model sees it.
3. The host MUST copy the value to the clipboard only after a second, separate action of the person on the
   shown value. A link or an action that the model wrote MUST NOT copy a value.
4. The host MUST NOT resolve the same reference again for a second action in the same session if it still
   holds the value.

## 6. Server rules

1. The server MUST refuse `display` for a token without the display scope with `403 insufficient_scope`,
   before any lookup (RESOLVER-PROFILE.md, section 5.4).
2. The server MUST write one audit event for each released value (each reveal). The value counts toward the
   quota of the principal (RESOLVER-PROFILE.md, section 15).
3. The consent page MUST name the display scope in one line that says that the program can show real values
   on the screen of the person, and that the program says it never gives them to the AI
   (RESOLVER-PROFILE.md, section 10.2).

**Note.** Pseudonymization protects a value from the model, not from the person. A person who may hold a
reference of an issuer may see its value. The deployment decides who may use the issuer at all.

## 7. Limit

Any local process of the person that holds a resolver token with the display scope can get the full value
of every reference of that person. The server cannot check that a value reaches a screen. This is the
reason why the display scope is a separate scope that a person can leave out on the consent page.

Anyone who sees the screen sees the value, also through a screen share, a screenshot or a recording. A
copied value is in the clipboard of the system, where other programs can read it.

## 8. Not in this profile

- A display of more than one value per action.
- A display without an action of the person.
- Protection of the screen against a person or a camera.

## 9. Evidence

**Note.** The reference server accepts this profile. The second host implements it in the drawing of a
coding-agent client. The reference host does not implement it. See
[IMPLEMENTATION-EVIDENCE.md](IMPLEMENTATION-EVIDENCE.md).
