# Security model

## Objective

Sensitive References aim to avoid putting a server-classified sensitive value into model-visible content
only because an authorized later action needs that value.

## Trust boundaries

- The issuer controls the plaintext and reference lifecycle.
- The model is untrusted with plaintext, resolver credentials, and issuer selection.
- The resolver authenticates as a stable principal and authorizes resolution.
- The host retains provenance and protects eligible sink input.

## Required controls

- A reference has no bearer authority.
- The issuer comes from authenticated transport context, not token or model text.
- Unknown, ambiguous, revoked, expired, stale, wrong-principal, and unauthorized references fail closed.
- An issuer must not silently bind an old identifier to another value generation.
- A resolver must authorize each batch independently from ordinary reference possession.
- A sink must not return resolved plaintext in an ordinary model-facing result.
- `local-file-1` must materialize a whole batch or leave the destination unchanged.

## Limits

This design does not protect plaintext after an authorized sink receives it. It does not protect against a
malicious process with the same operating-system privileges as the resolver or a compromised host runtime.
Generic shell safety, filesystem policy, output echo control, quotas, audit, and sender constraint belong
to integration or resolver profiles.
