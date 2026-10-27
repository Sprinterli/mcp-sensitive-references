# Wire representation

**Status: Concept 0.6 draft, normative core.** The conventions and terms of
[SPEC-DRAFT.md](SPEC-DRAFT.md#1-conventions) apply.

## 1. Canonical form of a reference

Version 1 uses one canonical text form in ordinary MCP text content and in string values of
`structuredContent`:

```text
⟦sref:email:01JCK7KF9X4Y3M4N6Q6YB2D8P0⟧
```

The grammar is:

```text
reference = %x27E6 "sref:" kind ":" id %x27E7
kind      = 1*32( ALPHA / DIGIT / "_" / "-" )
id        = 20*128( ALPHA / DIGIT / "_" / "-" )
```

`%x27E6` is MATHEMATICAL LEFT WHITE SQUARE BRACKET (U+27E6). `%x27E7` is MATHEMATICAL RIGHT WHITE SQUARE
BRACKET (U+27E7). `ALPHA` and `DIGIT` are ASCII (RFC 5234).

- `kind` is advisory. It MUST NOT decide identity, issuer or authorization.
- `id` is opaque and random (SPEC-DRAFT.md, section 5.1).
- A reference MUST NOT contain plaintext, a resolver URL, an issuer identity or a subject identifier.

A host MUST match references as exact Unicode code points. A host MUST NOT normalize, case-fold, trim or
rebuild a reference before it compares two references.

The text form keeps existing string schemas. It survives text, JSON, CSV, document and tool-argument flows.
Version 1 does not need a new MCP `ContentBlock` type. Version 1 does not use `_meta` as a secrecy
boundary.

## 2. Test vectors

| Input | Result |
|---|---|
| `⟦sref:email:AbCdEfGhIjKlMnOpQrStUvWx1234⟧` | valid reference |
| `⟦sref:email:short⟧` | invalid: the identifier is too short |
| `⟦sref:email:AbCdEfGhIjKlMnOpQrStUvWx1234⟧` followed by a space | not an exact reference identity |
| `［sref:email:AbCdEfGhIjKlMnOpQrStUvWx1234］` (U+FF3B, U+FF3D) | invalid: lookalike brackets |
| the same valid reference from two authenticated issuers | ambiguous: do not resolve |
| the same valid reference in a local file without a trusted observation | ordinary text: do not resolve |

## 3. Extension settings

A client and a server put a settings object under the extension identifier in the MCP `extensions` map:

```json
{
  "extensions": {
    "org.example/sensitive-references": {
      "versions": ["1"],
      "resolver_profiles": ["oauth-resolver-1"],
      "sink_profiles": ["local-file-1"]
    }
  }
}
```

The identifier `org.example/sensitive-references` is an example (SPEC-DRAFT.md, section 4). The settings
object MUST follow this schema:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "additionalProperties": false,
  "required": ["versions"],
  "properties": {
    "versions": {
      "type": "array", "minItems": 1, "uniqueItems": true,
      "items": {"type": "string", "pattern": "^[1-9][0-9]*$"}
    },
    "resolver_profiles": {
      "type": "array", "uniqueItems": true,
      "items": {"type": "string", "pattern": "^[a-z0-9][a-z0-9-]{0,63}$"}
    },
    "sink_profiles": {
      "type": "array", "uniqueItems": true,
      "items": {"type": "string", "pattern": "^[a-z0-9][a-z0-9-]{0,63}$"}
    }
  }
}
```

The negotiated version is a version that both sides list. The negotiated profiles are the intersection of
the profiles that both sides list. If no version is common, the extension is not negotiated.

The settings object carries no resolver endpoint and no limit. A resolver profile defines where a host
finds them. For `oauth-resolver-1`, see [RESOLVER-PROFILE.md](RESOLVER-PROFILE.md#4-discovery-object).

## 4. Issuer identity and display text

The host derives the issuer identity from the authenticated connection
([HOST-INTEGRATION.md](HOST-INTEGRATION.md#2-issuer-identity)). The host stores it outside model-visible
text. Reference-shaped text has no authority until a supporting host observes it in a negotiated,
authenticated MCP result. A model can copy a known reference. A model cannot create its provenance.

If one reference has more than one trusted issuer, the host MUST mark it ambiguous and MUST NOT resolve it.

Masked display text MUST NOT decide identity, issuer or authorization.

**Provisional (OQ-2).** A server puts no display text on the wire next to a reference. A host renders a
display from its own metadata.

## 5. Refusal result

SPEC-DRAFT.md, section 5.7, requires `isError: true` when a server refuses a tool call because a reference
does not resolve. If the result has `structuredContent`, the object MUST follow these rules:

- `error_code` (required): one of `reference_malformed`, `reference_unknown`, `reference_revoked` or
  `reference_expired`. If the refused references have more than one reason, `error_code` names the first
  reason in this order: malformed, unknown, revoked, expired.
- `reasons` (required): an object. Its keys are a subset of `malformed`, `unknown`, `revoked` and
  `expired`. Each value is an integer of 1 or more: the number of refused references with that reason.
  The object MUST have the key that is `error_code` without the prefix `reference_`. It MUST NOT have other
  keys.
- The object MAY have other members. Another member MUST NOT contain protected data (SPEC-DRAFT.md,
  section 8).

```json
{
  "type": "object",
  "required": ["error_code", "reasons"],
  "properties": {
    "error_code": {"enum": ["reference_malformed", "reference_unknown", "reference_revoked", "reference_expired"]},
    "reasons": {
      "type": "object",
      "minProperties": 1,
      "additionalProperties": false,
      "properties": {
        "malformed": {"type": "integer", "minimum": 1},
        "unknown": {"type": "integer", "minimum": 1},
        "revoked": {"type": "integer", "minimum": 1},
        "expired": {"type": "integer", "minimum": 1}
      }
    }
  }
}
```

The schema cannot express the key rule and the order rule. These two rules stay in the text above.

| `structuredContent` | Result |
|---|---|
| `{"error_code": "reference_malformed", "reasons": {"malformed": 1}}` | allowed |
| `{"error_code": "reference_unknown", "reasons": {"unknown": 1}, "hint": "Ask the user for a new reference."}` | allowed |
| `{"error_code": "reference_revoked", "reasons": {"revoked": 2, "expired": 1}}` | allowed |
| `{"error_code": "reference_unknown", "reasons": {"revoked": 1}}` | refused: no key `unknown` |
| `{"error_code": "reference_unknown", "reasons": {"reference_unknown": 1}}` | refused: the key keeps the prefix |
| `{"error_code": "reference_revoked", "reasons": {"unknown": 1, "revoked": 2}}` | refused: the order names `unknown` first |
| `{"error_code": "reference_unknown", "reasons": {"unknown": 0}}` | refused: a count below 1 |
| `{"error_code": "reference_unknown", "reasons": {"unknown": 1}, "detail": "no value for alice@example.com"}` | refused: protected data, item 1 |

**Note.** No validator and no test in this repository checks this schema
([IMPLEMENTATION-EVIDENCE.md](IMPLEMENTATION-EVIDENCE.md#known-gaps)).
