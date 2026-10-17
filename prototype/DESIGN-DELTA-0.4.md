# Design delta against Sensitive References 0.4

This is a change list for Concept 0.5. It does not modify the 0.4 source package.

## KEEP

- **Canonical text token in ordinary strings.** Keep the preferred v1 representation in
  `WIRE-REPRESENTATION.md` and the 0.4 update in `HANDOFF.md`. The prototype and FastMCP probe show
  that string-valued structured output preserves schema shape. Keep the text form as the first wire
  representation; do not introduce a `ContentBlock` type.
- **Reference is not authorization.** Keep D2 in `DECISION-LOG.md` and §§7/13/15 of `SPEC-DRAFT.md`.
  The resolver tests show possession alone can be rejected when authorization is separate.
- **Host-derived issuer provenance.** Keep D6 and `WIRE-REPRESENTATION.md` “Trusted observation”. The
  prototype confirms that a token need not embed an issuer to be copied safely, and that ambiguity can
  fail closed.
- **Out-of-model protected sinks.** Keep D4 and `SPEC-DRAFT.md` §§7–9. The file-sink test demonstrates
  the intended separation for one sink profile.
- **Generation-safe opaque IDs and no silent remapping.** Keep D5 and
  `WIRE-REPRESENTATION.md` “Canonical token”. Immutable random IDs work in the reference registry.
- **Extension negotiation, no `_meta` secrecy dependency, and no v1 delegation.** Keep D7, D9–D12,
  `CURRENT-MCP-FIT.md`, and `CORE-VS-PROFILES.md`. No prototype finding contradicts them.

## CHANGE

- **Reword the OAuth Resolver Profile status.** In `SPEC-DRAFT.md` §13,
  `RESOLVER-BINDING.md`, `CORE-VS-PROFILES.md`, and the 0.4 `HANDOFF.md` update, replace language that
  can read as a settled “leading portable profile” with: “validated as a viable resolver profile
  candidate.” Keycloak validates feasibility, not cross-AS or host interoperability.
- **Make host provenance requirements concrete.** D6 is semantically decided but its operational
  boundary needs one short normative host subsection: authenticated negotiated result observation;
  exact token lookup at an eligible sink; unknown and multi-issuer ambiguity fail closed; provenance
  is never selected by model content. Cite `WIRE-REPRESENTATION.md` “Trusted observation” and
  `SPEC-DRAFT.md` §§6–9.
- **Promote all-or-nothing behavior for the first file-sink profile.** `SPEC-DRAFT.md` §9 currently
  says a profile “SHOULD specify” it. Define it as a MUST for `local-file-1`: resolve all issuer
  batches before replacing the destination. This is directly exercised by the prototype; filesystem
  crash durability remains profile-scoped.
- **Require a stable subject claim in the OAuth profile.** `RESOLVER-BINDING.md` and
  `SPEC-DRAFT.md` §13 should say the resource server verifies a deployment-declared stable subject
  claim, with `sub` as the default. The Keycloak probe had to configure a mapper and safely rejected
  absent subject identity; no display-name inference is acceptable.

## CLARIFY

- **State lifecycle scope precisely.** D5/§8 should distinguish immutable reference IDs (proven in
  memory) from durable revocation, expiry, persistence, and recovery (not proven).
- **State the host-restart result.** Add to `WIRE-REPRESENTATION.md` that a host which has lost trusted
  observation state MUST fail closed or obtain a new trusted observation. Cross-session persistence
  is a host/profile choice requiring integrity and retention rules.
- **Define what receives provenance observation.** `SPEC-DRAFT.md` §§5–6 should name decoded text
  content and recursive string values in `structuredContent` as v1 inputs, after negotiation and
  authentication. It should avoid requiring arbitrary model-output rewriting.
- **Clarify the ordinary-agent-token rule.** `SPEC-DRAFT.md` §13 should make clear that an agent token
  can resolve only after separate explicit grant of resolve privilege; the prototype did not test a
  production MCP agent token.
- **Narrow the external-AS statement.** `CURRENT-MCP-FIT.md` should say MCP’s model permits separate
  resource and authorization servers, while the profile’s interoperability was validated only with
  Keycloak plus a local resolver resource-server surface.

## DEFER

- **Resolver endpoint discovery.** Keep open as in `RESOLVER-BINDING.md` and `SPEC-DRAFT.md` §16:
  Protected Resource Metadata versus extension settings needs external-review evidence.
- **Final extension identifier and settings schema.** Keep D11 and `CURRENT-MCP-FIT.md` provisional
  during incubation.
- **Sender constraint, OAuth consent/recovery, durable token storage, audit, and rate limits.** Keep
  profile work as described in `SECURITY-MODEL.md` T5–T6; the prototype uses ephemeral test state.
- **Cross-server delegation.** Keep D7 and `SCOPE-AND-NONGOALS.md`: no v1 mechanism was tested.
- **A universal sink or output-echo guarantee.** Keep `SECURITY-MODEL.md` T7–T8 profile-specific. The
  prototype validates one local-file path and a narrow current-operation output guard only.
