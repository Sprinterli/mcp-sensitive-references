# Host integration

**Status: Concept 0.6 draft, normative core.** The conventions and terms of
[SPEC-DRAFT.md](SPEC-DRAFT.md#1-conventions) apply.

This extension needs a supporting host. A server cannot create trusted provenance through text alone.

## 1. Supporting host

A supporting host MUST be able to do all of these steps:

1. Negotiate the extension with an MCP server (SPEC-DRAFT.md, section 4).
2. Get the issuer identity of the server from the authenticated MCP connection (section 2).
3. Inspect references in the text content and in every string value of `structuredContent` of an
   authenticated tool result.
4. Store observations outside model-visible text (section 3).
5. Inspect the input of an eligible sink before the sink runs (section 5).
6. Resolve only observed references with exactly one trusted issuer, through a non-model resolver.
7. Return reference-only content through the ordinary model-facing result path.
8. Fail closed if provenance, authorization or sink isolation is not available.

A host that cannot do steps 1 and 2 is not a supporting host. It MUST NOT declare the extension
(SPEC-DRAFT.md, section 6.2).

**Note.** The host does not need to rewrite arbitrary model output. It needs only the observation point and
the sink input point. The model can copy a known reference through intermediate text, because the host
looks up the exact reference in its trusted state.

## 2. Issuer identity

For an MCP server over HTTP, the issuer identity is the URL of the MCP endpoint exactly as the host
connects to it, with its query if it has one.

- A URL with user information or a fragment MUST NOT be an issuer identity. A host MUST NOT connect to such
  a URL for this extension.
- A host MUST keep the issuer identity as given. A host MUST NOT normalize case, a trailing slash, a
  default port or a percent-encoding.
- A host MUST compare two issuer identities as exact strings.
- A host MUST NOT take the issuer identity from a reference, from model text or from a server message.
- If the MCP connection follows an HTTP redirect, the host MUST NOT record observations from that
  connection.

A resolver profile can require that the server confirms this identity. `oauth-resolver-1` requires that
the RFC 9728 `resource` value is identical to the issuer identity
([RESOLVER-PROFILE.md](RESOLVER-PROFILE.md#3-issuer-identity-and-protected-resource-metadata)).

A server SHOULD NOT put a credential into the query of its MCP URL. The query is part of the issuer
identity. A host stores it with each observation, and a resolver profile can send it to other parties.

**Note.** Over HTTP with a bearer token, a URL is a locator and a TLS origin. It is not a cryptographic
identity. An attacker who controls DNS and a valid TLS certificate for the origin controls the issuer.

**Open (OQ-12).** This version defines no issuer identity for a transport other than HTTP, for example
stdio. A host MUST NOT record an observation for such a transport unless a later version or profile defines
the identity.

## 3. Observations and the provenance store

A host MUST record an observation only from an authenticated MCP result (SPEC-DRAFT.md, section 2) of a
server with which it negotiated the extension. The observation holds `(reference, issuer identity, first_observed, optional
metadata)`.

- If one reference has trusted observations from more than one issuer, the host MUST mark it ambiguous.
  The host MUST NOT choose an issuer automatically.
- If a reference has no trusted observation, it is ordinary text.
- Optional metadata MUST NOT decide identity, issuer or authorization.

A host MAY keep observations in memory only. After a restart, such a host needs a new observation before
it resolves a reference.

**Provisional (OQ-7).** A host MAY keep observations in a durable store.

The following rules apply to every host with a durable store. They are not provisional.

- The host MUST check, before it uses a stored observation, that the observation is intact and comes from
  its own store. If the check fails, or the host cannot make it, the host MUST treat the reference as not
  observed and MUST NOT resolve it. (not testable on the wire)
- Loss of trustworthy provenance MUST fail closed.
- If the host protects the store with a key, a tool, a file or a process that the model can reach MUST NOT
  be able to read or use that key. A model that can write the store and also has the key can plant
  provenance. (not testable on the wire)

This version defines no integrity mechanism and no freshness rule for a durable store (OQ-7).

## 4. Resolution path

Before a host resolves, all these conditions MUST be true:

1. The negotiated intersection holds a resolver profile and a sink profile that the host supports.
2. Each reference has exactly one trusted issuer.
3. The host sends each reference only to the resolver endpoint of its own issuer.

A host MUST NOT send the agent token to a resolver endpoint. The resolver profile defines the resolver
credential.

## 5. Sink input point

A host MUST inspect the input of an eligible sink before the sink runs. The host MUST extract the exact
references from that input. The host MUST resolve only references that pass section 4. The host MUST NOT
change the destination of the sink before every reference of that write resolved. The sink profile defines
the destination and the content rules.

## 6. Model-facing output

- The model-facing result of a sink MUST keep the references. It MUST NOT contain a resolved value.
- An error text or a log of the host that the model can read MUST NOT contain protected data
  (SPEC-DRAFT.md, section 8). The sink profile sets the rule for the report of a sink.
- A host MUST NOT show a server error message of a resolver endpoint to the model. It MAY report the error
  code.
- If a later action echoes a value that the host resolved in the current operation, the host MAY put the
  reference back in place of the value. This is not a general redaction guarantee.

## 7. Restart and ambiguity

If a host loses its provenance store, it MUST fail closed or get a new trusted observation. If one
reference maps to two issuers, the host MUST NOT choose one. A host MUST NOT infer provenance from the
content of a reference.

## 8. Evidence

**Note.** The reference host `prototype/demo/mcp_host.py` keeps observations in memory. It loses them on
restart and then fails closed. Its limits are in [IMPLEMENTATION-EVIDENCE.md](IMPLEMENTATION-EVIDENCE.md).
The host checklist with its evidence is in
[protocol-package/IMPLEMENTATION-GUIDE.md](protocol-package/IMPLEMENTATION-GUIDE.md).
