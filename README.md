# Sensitive References for MCP

> **Status: Concept 0.7 draft (not an MCP standard, not an accepted SEP).**
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
- References are per person. A reference of one person never resolves for another.
- Each sink that hands a value to a local process or a screen needs its own scope, which a person can
  leave out on the consent page.

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
| [PROCESS-PROFILE.md](PROCESS-PROFILE.md) | `process-1`: resolution into a command that the host runs |
| [DISPLAY-PROFILE.md](DISPLAY-PROFILE.md) | `display-1`: one value on the screen of the person, after a click |

Not normative:

| Document | Content |
|---|---|
| [OPEN-QUESTIONS.md](OPEN-QUESTIONS.md) | Remaining design decisions, with options and provisional choices |
| [DESIGN-DECISIONS.md](DESIGN-DECISIONS.md) | The decisions that the normative text applies |
| [CHANGELOG.md](CHANGELOG.md) | Every change of Concept 0.6 and 0.7, with its source |
| [IMPLEMENTATION-EVIDENCE.md](IMPLEMENTATION-EVIDENCE.md) | The two implementations, the evidence and the known gaps |
| [STATUS.md](STATUS.md) | The current state |
| [PRIOR-ART.md](PRIOR-ART.md) | Adjacent mechanisms |
| [protocol-package/](protocol-package/) | Supporting rationale, implementation evidence and history (SC-01 to SC-26) |
| [prototype/](prototype/) | The reference host and the feasibility prototype |

## Changes in this revision

Concept 0.7 describes what runs and has proven itself in the implementations. [CHANGELOG.md](CHANGELOG.md)
lists every change with its source.

1. **Sink scopes.** A sink profile can require its own scope. The discovery object names the scope set of
   each sink profile, and its name `sensitive_references` is fixed. The host asks for the resolve scope
   and the sink scopes it can honour, in one request. A missing sink scope gives `403 insufficient_scope`
   before any lookup. A refresh keeps the granted set.
2. **Two new sink profiles.** `process-1` gives a value to a command and masks the command output.
   `display-1` shows one value on the screen after a click of the person.
3. **Consent at every authorization request.** No stored approval replaces the decision. The page names
   the account, the client, the loopback host and port, the time and each sink scope.
4. **References per person.** A reference of person A never resolves for person B. An optional
   `account_hint` shows which account a token belongs to.
5. **No value without its audit event** (`503 audit_unavailable` otherwise).
6. **Revocation per device**, by the person and by an administrator.

## Implementations

- **Reference server: MCPGate.** It issues references, implements `oauth-resolver-1` and accepts
  `local-file-1`, `display-1` and the process profile (as `mcpgate-process-1`, see OQ-21). Revision R3
  (versions 2.0.3824 and 2.0.3826, 2026-11-08) implements every change of Concept 0.7. Its source is not
  public.
- **Reference host: [prototype/demo/mcp_host.py](prototype/demo/mcp_host.py).** An independent MCP host.
  It negotiates the extension, records provenance, gets its own resolver token and writes a local file.
  133 tests passed on 2026-10-27 in the tested configuration. It implements `local-file-1` only.
- **Second host: [maisecrets](https://github.com/Mcpgate-de/maisecrets)** (releases 0.9.0 and 0.9.1). A
  plugin for coding agents. It resolves into files, commands and the screen. It declares no extension, so
  it is not a supporting host (SPEC-DRAFT.md, section 6.2).

**Known gaps.** The reference server tests of R3 were read, not run by this repository. The display run
E13 (2026-11-08) is one operator run, not independently reproduced. No end-to-end run of the process
profile is recorded against the reference server. The reference host implements Concept 0.7. The prototype
issuer in `prototype/` implements the server rules of Concept 0.7. Both are demo level, and no run against
R3 is recorded. Run E12
(2026-10-27) is one operator run of each step. Browser-side DNS rebinding remains a residual risk (TM-11).
MCP SDK 1.x was not tested. See [IMPLEMENTATION-EVIDENCE.md](IMPLEMENTATION-EVIDENCE.md).

## Run the prototype

```bash
cd prototype
python3 -m pip install -e '.[mcp-demo,resolver-http-demo]'
PYTHONPATH=src python3 -m unittest discover -s tests
```

## Versions

- **Concept 0.5** is the git tag `concept-0.5`:
  <https://github.com/Sprinterli/mcp-sensitive-references/tree/concept-0.5>.
- **Concept 0.6** is the git tag `concept-0.6`:
  <https://github.com/Sprinterli/mcp-sensitive-references/tree/concept-0.6>.
- **Concept 0.7** is the current text in this repository. [CHANGELOG.md](CHANGELOG.md) lists the changes.

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
