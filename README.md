# Sensitive References for MCP

> **Status: Concept 0.6 draft (not an MCP standard, not an accepted SEP).**
>
> This repository describes a possible optional MCP extension for opaque references to server-held
> sensitive data. It is not affiliated with the Model Context Protocol project.

An MCP server can hold a customer email, an API key, a health identifier or another sensitive value. An
agent can need that value in a later action without the need to read it.

Sensitive References give another option:

```text
email = ⟦sref:email:01JCK7KF9X4Y3M4N6Q6YB2D8P0⟧
```

The model can carry, sort, format and route the reference. An authorized non-model resolver can later put
the plaintext into an eligible sink when an action needs it. The plaintext never goes back into
model-visible text. The short goal is: **referencable but not visible**.

## Problem

Today, a server often shows plaintext when an agent must use a value later. Redaction can make the
requested file, document or action impossible. This extension separates the reference from the plaintext,
and the possession of a reference from the authority to resolve it.

## Core properties

- A Sensitive Reference is an opaque string that a server issues in place of a sensitive value. It is not
  an authorization grant. Possession alone does not authorize resolution.
- A host trusts a reference only if it observed it in an authenticated MCP result of a negotiated server,
  and recorded it outside model text. On loss or ambiguity of that record, the host fails closed.
- A separately authorized resolver resolves references into an eligible sink. The model-facing result
  keeps the references.

## Documents

Normative core:

| Document | Content |
|---|---|
| [SPEC-DRAFT.md](SPEC-DRAFT.md) | Terms, negotiation, issuer rules, host rules, resolution, protected data |
| [WIRE-REPRESENTATION.md](WIRE-REPRESENTATION.md) | Canonical form, test vectors, settings object, refusal result |
| [HOST-INTEGRATION.md](HOST-INTEGRATION.md) | Issuer identity, provenance store, observation point, sink input point |
| [SECURITY-MODEL.md](SECURITY-MODEL.md) | Trust boundaries, required controls, threats, limits |

Normative profiles:

| Document | Profile |
|---|---|
| [RESOLVER-PROFILE.md](RESOLVER-PROFILE.md) | `oauth-resolver-1`: a separate OAuth resolver client |
| [LOCAL-FILE-PROFILE.md](LOCAL-FILE-PROFILE.md) | `local-file-1`: resolution into one local file |

Not normative:

| Document | Content |
|---|---|
| [OPEN-QUESTIONS.md](OPEN-QUESTIONS.md) | Remaining design decisions, with options and provisional choices |
| [DESIGN-DECISIONS.md](DESIGN-DECISIONS.md) | The decisions that the normative text applies |
| [CHANGELOG.md](CHANGELOG.md) | Every change from Concept 0.5 to 0.6, with its source |
| [IMPLEMENTATION-EVIDENCE.md](IMPLEMENTATION-EVIDENCE.md) | The two implementations, the evidence and the known gaps |
| [STATUS.md](STATUS.md) | The current state |
| [PRIOR-ART.md](PRIOR-ART.md) | Adjacent mechanisms |
| [protocol-package/](protocol-package/) | Supporting rationale, implementation evidence and history (SC-01 to SC-20) |
| [prototype/](prototype/) | The reference host and the feasibility prototype |

## Implementations

- **Reference server: MCPGate.** It issues references, implements `oauth-resolver-1` and accepts
  `local-file-1`. Its source is not public. Since 2026-10-27, its challenge names the metadata of its
  MCP URL (P16 fixed; one operator check, E12).
- **Reference host: [prototype/demo/mcp_host.py](prototype/demo/mcp_host.py).** An independent MCP host.
  It negotiates the extension, records provenance, gets its own resolver token and writes a local file.
  133 tests passed on 2026-10-27 in the tested configuration.

**Known gaps.** The run of the reference host against the reference server without a deviation option
(E12) is one operator run of each step and is not independently reproduced. SC-20 has no automated test. Browser-side DNS rebinding remains a residual risk (TM-11). MCP
SDK 1.x was not tested. The consent lessons come from one browser. See
[IMPLEMENTATION-EVIDENCE.md](IMPLEMENTATION-EVIDENCE.md).

## Run the prototype

```bash
cd prototype
python3 -m pip install -e '.[mcp-demo,resolver-http-demo]'
PYTHONPATH=src python3 -m unittest discover -s tests
```

## Versions

- **Concept 0.5** is the git tag `concept-0.5`:
  <https://github.com/Sprinterli/mcp-sensitive-references/tree/concept-0.5>.
- **Concept 0.6** is the current text in this repository. [CHANGELOG.md](CHANGELOG.md) lists the changes.

## Out of scope

This extension does not define sensitive-data classification, DLP, NER, user interfaces, databases,
generic filesystem policy, cross-server redemption, delegation or a new MCP `ContentBlock` type. It does not
use `_meta` as a secrecy boundary.

## Community discussion

[COMMUNITY-DISCUSSION.md](COMMUNITY-DISCUSSION.md) is a discussion draft. Feedback on host provenance,
protected sinks, the resolver profile and the remaining design decisions is welcome.

## Disclaimer

This repository is independent design work. It does not imply endorsement by any AI vendor, by the MCP
maintainers or by an MCP working group.

## License

[Apache-2.0](LICENSE)
