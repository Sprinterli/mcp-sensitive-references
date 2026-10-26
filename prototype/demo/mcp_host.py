"""An independent test host for Sensitive References over a real MCP connection.

It connects to any MCP server by URL with the MCP SDK client, declares the
extension (or, with ``--legacy``, declares nothing), and checks what a model
would be handed: every tool result is read as the host receives it, before any
model sees it.

What it checks, per tool call:

* negotiation: the server advertised the extension with a version the host
  declared, and the host records observations only then;
* provenance: each canonical token is recorded with its issuer and the time it
  was first seen. The issuer is the server URL the host connected to, exactly
  as given (a URL with user information or a fragment is refused). The report
  shows it without query. This identity is experimental: it is a
  locator, not an independently verified issuer identity (a TLS origin at best).
  Which identity a host should record is open; the resource identifier of
  RFC 9728 is one candidate;
* representation: every reference-shaped string in the model-visible texts is a
  canonical token, and no configured sentinel value appears anywhere in the
  serialized result;
* legacy: a host that declared nothing sees no canonical token at all;
* with ``--expect-success``: a call fails the run when it returns ``isError``
  or when a structured field (``error_code``, ``code``, ``error``) of its result
  names a reference failure. Concept 0.5 lets a server report a failed
  resolution inside a successful result, so ``isError`` alone does not say that
  an operation happened.

A follow-up call may pass a reference the host observed (``{ref}`` in
``--then-arguments``); the host sends only a reference with exactly one trusted
issuer, and checks the result the same way.

With ``--resolve-into PATH`` the host also materializes: after the MCP
session it writes ``--materialize-template`` (default ``{ref}`` and a newline)
once for each reference of the first call that has exactly one trusted issuer.
It writes through ``ProtectedFileSink`` and resolves through the resolve
endpoint of that issuer (``oauth-resolver-1``, ``local-file-1``):

* it resolves only when both profiles are in the negotiated intersection;
* the resolve endpoint comes from ``--resolve-endpoint`` or from the
  ``sensitive_references`` field of the RFC 9728 protected-resource metadata
  (a provisional name). A discovered or configured endpoint must be on the
  resource origin. A present field must hold all four members and both
  profiles, else the host stops. The metadata comes first from the
  ``resource_metadata`` URL of the 401 answer of the MCP URL, else from the
  path-inserted well-known URL; never from the origin root. Without metadata
  the host stops, unless ``--no-resource-metadata`` says that the server has
  none (configuration mode, not SC-01 or SC-02 conformant);
* the resolver token is a second credential: a cached token (mode 0600), a
  refreshed one, or a new Authorization Code + PKCE S256 authorization with
  dynamic client registration and a 127.0.0.1 loopback redirect. The agent
  token never goes to the resolve endpoint;
* a batch writes all or nothing. The report holds counts and verdicts only.

Nothing here is specific to one server. The extension identifier is not fixed
by concept 0.5, so it is configuration (``--extension-id``). Sentinel values are
read from the environment and never printed; the report holds counts and
verdicts only.

    SREF_SENTINELS="a@example.com,b@example.com" MCP_TOKEN=... \\
    python mcp_host.py --url https://server.example/mcp --extension-id <id> \\
        --tool <read tool> --arguments '{"...": "..."}' \\
        --then-tool <write tool> --then-arguments '{"text": "to {ref}"}'
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sensitive_references import ProvenanceStore  # noqa: E402
from sensitive_references.capabilities import (  # noqa: E402
    CapabilitySettingsError,
    SensitiveReferencesCapabilities,
    negotiate,
)
from sensitive_references.provenance import AmbiguousReference, UnknownReference  # noqa: E402
from sensitive_references.reference import _TOKEN_RE as CANONICAL_TOKEN  # noqa: E402
from sensitive_references.reference import find_tokens  # noqa: E402
from sensitive_references.resolver import ResolutionError  # noqa: E402
from sensitive_references.resolver_client import (  # noqa: E402
    RESOLVER_PROFILE,
    SINK_PROFILE,
    OAuthHttpResolver,
    OAuthResolverCredential,
    ResolveEndpoint,
    ResolverClientError,
    TokenCache,
    discover_protected_resource,
    origin,
    require_secure,
)
from sensitive_references.oauth_profile import RESOLVE_SCOPE  # noqa: E402
from sensitive_references.sink import ProtectedFileSink  # noqa: E402

#: Anything that starts like a reference; a canonical token must match exactly.
_REFERENCE_LIKE = re.compile(r"(?i)sref\s*:")
HOST_SETTINGS = {"versions": ["1"]}
#: The settings a host declares when it can resolve into a local file.
RESOLVING_HOST_SETTINGS = {"versions": ["1"], "resolver_profiles": [RESOLVER_PROFILE], "sink_profiles": [SINK_PROFILE]}

#: A structured failure code that names one of the failure reasons of concept
#: 0.5 for a reference (``PII_REFERENCE_UNKNOWN``, ``reference_revoked``).
DEFAULT_REFUSAL = r"(?i)reference.{0,3}(malformed|unknown|revoked|expired|stale|ambiguous|unauthori[sz]ed)"
_REFUSAL_FIELDS = ("error_code", "code", "error")


def issuer_identity(url: str) -> str:
    """The issuer for ``url``: the URL exactly as given (SC-01, RFC 9728 section 3.3).

    The host does not change the case, a default port, a trailing slash or the
    query. A URL with user information or a fragment cannot be a resource
    identifier, so the host refuses it.
    """
    parts = urlsplit(url)
    if "#" in url or parts.username is not None or parts.password is not None:
        raise ValueError("the URL holds user information or a fragment")
    return url


def public_endpoint(url: str) -> str:
    """The URL as a report may hold it: no user information, no query and no
    fragment, where a token or a password can sit. Not an issuer identity.

    Every other character stays as given.
    """
    head = url.split("#", 1)[0].split("?", 1)[0]
    scheme, separator, rest = head.partition("://")
    if not separator:
        return head
    authority, slash, path = rest.partition("/")
    return f"{scheme}://{authority.rpartition('@')[2]}{slash}{path}"


@dataclass
class CallReport:
    tool: str
    is_error: bool
    canonical_tokens: int = 0
    distinct_tokens: int = 0
    non_canonical_reference_like: int = 0
    sentinel_hits: int = 0
    observed_with_provenance: int = 0
    refused: bool = False


@dataclass
class HostReport:
    server: str
    declared: bool
    advertised: bool = False
    negotiated_version: str | None = None
    calls: list[CallReport] = field(default_factory=list)
    materialization: "MaterializeReport | None" = None
    failures: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.failures


def _strings(value: Any):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for nested in value.values():
            yield from _strings(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from _strings(nested)


def model_visible(result: Any) -> list[str]:
    """The texts of a tool result as a host passes them to a model: the text
    content blocks and every string of the structured content."""
    data = result.model_dump(by_alias=True, mode="json", exclude_none=True) if hasattr(result, "model_dump") else result
    texts = [block.get("text", "") for block in data.get("content", []) if block.get("type") == "text"]
    texts += list(_strings(data.get("structuredContent", {})))
    return texts


def _structured(data: dict, texts: list[str]):
    """The objects of a result: its structured content and every text block
    that is a JSON object."""
    if isinstance(data.get("structuredContent"), dict):
        yield data["structuredContent"]
    for text in texts:
        try:
            value = json.loads(text)
        except ValueError:
            continue
        if isinstance(value, dict):
            yield value


def refused(data: dict, texts: list[str], pattern: str = DEFAULT_REFUSAL) -> bool:
    """True when a structured field of the result names a reference failure."""
    matcher = re.compile(pattern)
    return any(isinstance(obj.get(name), str) and matcher.search(obj[name])
               for obj in _structured(data, texts) for name in _REFUSAL_FIELDS)


def inspect_result(tool: str, result: Any, *, issuer: str, negotiated: bool,
                   provenance: ProvenanceStore, sentinels: list[str],
                   refusal_pattern: str = DEFAULT_REFUSAL) -> CallReport:
    texts = model_visible(result)
    data = result.model_dump(by_alias=True, mode="json", exclude_none=True) if hasattr(result, "model_dump") else result
    report = CallReport(tool=tool, is_error=bool(data.get("isError")),
                        refused=refused(data, texts, refusal_pattern))
    tokens = [ref.token for text in texts for ref in find_tokens(text)]
    report.canonical_tokens = len(tokens)
    report.distinct_tokens = len(set(tokens))
    for text in texts:
        # A marker is canonical only right behind the opening bracket of a canonical token.
        canonical = {m.start() + 1 for m in CANONICAL_TOKEN.finditer(text)}
        report.non_canonical_reference_like += sum(
            1 for like in _REFERENCE_LIKE.finditer(text) if like.start() not in canonical)
    # Sentinels anywhere a client could pass on: every block, _meta, an error's data.
    serialized = json.dumps(data, ensure_ascii=False)
    report.sentinel_hits = sum(serialized.count(value) for value in sentinels if value)
    provenance.observe_mcp_result(issuer, extension_negotiated=negotiated, result={"texts": texts})
    report.observed_with_provenance = sum(1 for token in set(tokens) if _trusted(provenance, token))
    return report


def _trusted(provenance: ProvenanceStore, token: str) -> bool:
    try:
        provenance.issuer_for(token)
        return True
    except (UnknownReference, AmbiguousReference):
        return False


def _check(report: HostReport, call: CallReport, *, expect_success: bool = False) -> None:
    if expect_success and call.is_error:
        report.failures.append(f"{call.tool}: the call failed")
    if expect_success and call.refused:
        report.failures.append(f"{call.tool}: the call was refused")
    if call.sentinel_hits:
        report.failures.append(f"{call.tool}: a sentinel value reached the model-visible result")
    if report.negotiated_version:
        if call.non_canonical_reference_like:
            report.failures.append(f"{call.tool}: a reference-like string is not a canonical token")
        if call.observed_with_provenance != call.distinct_tokens:
            report.failures.append(f"{call.tool}: a token has no single trusted issuer")
    elif call.canonical_tokens:
        report.failures.append(f"{call.tool}: canonical tokens without negotiation")


@dataclass
class ResolveConfig:
    """What ``--resolve-into`` needs. Every server-specific value is optional."""

    destination: str
    template: str = "{ref}\n"
    resolve_endpoint: str | None = None
    resolve_scope: str | None = None
    authorization_server: str | None = None
    client_id: str | None = None
    token_cache: str | None = None
    interactive: bool = True
    #: The operator says that the server publishes no RFC 9728 metadata. Only then
    #: does the host go on without metadata (configuration mode, not SC-01 or SC-02 conformant).
    no_metadata: bool = False
    open_browser: Any = None
    authorization_timeout: float = 300.0
    timeout: float = 30.0


@dataclass
class MaterializeReport:
    """Counts and verdicts only: never a token, a value or a credential."""

    destination: str
    materialized: bool = False
    references_sent: int = 0
    references_withheld: int = 0
    resolve_requests: int = 0
    resolver_token_source: str | None = None
    sentinels_in_file: int | None = None
    model_content_keeps_reference: bool | None = None
    sentinels_in_model_content: int | None = None
    failure: str | None = None


def resolution_negotiated(agreed: Any) -> bool:
    """Both profiles are in the negotiated intersection."""
    return (agreed is not None and RESOLVER_PROFILE in agreed.resolver_profiles
            and SINK_PROFILE in agreed.sink_profiles)


def _resolver_setup(issuer: str, config: ResolveConfig, mcp_url: str | None = None) -> tuple[str, str, str]:
    """The resolve endpoint, the authorization server and the resolve scope for ``issuer``.

    If the metadata holds the discovery object, the object must be complete and
    must offer both profiles (SC-02); a configured value can then replace the
    endpoint or the scope, but never excuses a bad object. Without the object,
    only configuration mode is left: the endpoint must be configured, and the
    scope comes from configuration, else the default. Configuration mode does
    not claim SC-02 conformance. Without metadata (none found, or the server
    did not answer) the host stops, unless ``config.no_metadata`` is set; then
    SC-01 is not checked either. The endpoint, discovered or configured, must
    be on the origin of the protected resource (SC-04); the metadata must name
    ``issuer`` itself.
    """
    # The WWW-Authenticate mechanism names metadata for the URL the request went to,
    # so it applies only when the issuer is the MCP URL itself.
    use_challenge = mcp_url is None or mcp_url == issuer
    try:
        metadata = discover_protected_resource(issuer, use_challenge=use_challenge, timeout=config.timeout)
    except ResolverClientError as error:
        # An unreachable server is not a server without metadata: fail closed.
        if error.code != "unreachable" or not config.no_metadata:
            raise
        metadata = None
    if metadata is None and not config.no_metadata:
        raise ResolverClientError("no_metadata", "no protected-resource metadata; set --no-resource-metadata "
                                                 "only for a server that publishes none")
    discovered = metadata is not None and metadata.discovery
    if discovered:
        if RESOLVER_PROFILE not in metadata.resolver_profiles:
            raise ResolverClientError("profile_not_offered", "the metadata does not offer the resolver profile")
        if SINK_PROFILE not in metadata.sink_profiles:
            raise ResolverClientError("profile_not_offered", "the metadata does not offer the sink profile")
    endpoint = config.resolve_endpoint
    if endpoint is None:
        if not discovered:
            raise ResolverClientError("no_resolve_endpoint", "no resolve endpoint configured or discovered")
        endpoint = metadata.resolve_endpoint
    # The resolver token has the resource as audience: it goes to no other origin (SC-04).
    if origin(endpoint) != origin(issuer):
        raise ResolverClientError("cross_origin_endpoint",
                                  "the resolve endpoint is not on the origin of the protected resource")
    require_secure(endpoint, "resolve endpoint")
    server = config.authorization_server
    if server is None:
        servers = metadata.authorization_servers if metadata else ()
        if len(servers) != 1:
            raise ResolverClientError("authorization_server",
                                      "zero or several authorization servers; set --authorization-server")
        server = servers[0]
    if config.resolve_scope:
        scope = config.resolve_scope
    elif discovered:
        scope = metadata.resolve_scope
    else:
        scope = RESOLVE_SCOPE
    return endpoint, server, scope


def materialize(*, issuer: str, references: list[str], provenance: ProvenanceStore, agreed: Any,
                config: ResolveConfig, sentinels: list[str], agent_token: str | None,
                mcp_url: str | None = None) -> MaterializeReport:
    """Write ``config.template`` once per trusted reference through the protected sink.

    Only references with exactly one trusted issuer go into the content. The sink
    resolves the whole content before it writes, so a failure leaves the
    destination as it was.
    """
    destination = Path(config.destination).expanduser().resolve()
    report = MaterializeReport(destination=str(destination))
    usable = [r for r in dict.fromkeys(references) if _trusted(provenance, r)]
    report.references_withheld = len(set(references)) - len(usable)
    if not resolution_negotiated(agreed):
        report.failure = "the resolver and sink profiles were not negotiated"
        return report
    if "{ref}" not in config.template:
        report.failure = "the template holds no {ref}"
        return report
    if not usable:
        report.failure = "no reference with exactly one trusted issuer"
        return report
    content = "".join(config.template.replace("{ref}", ref) for ref in usable)
    resolver = None
    credential = None
    try:
        endpoint, server, scope = _resolver_setup(issuer, config, mcp_url)
        credential = OAuthResolverCredential(
            resource=issuer, authorization_server=server, scope=scope, cache=TokenCache(config.token_cache),
            open_browser=config.open_browser, interactive=config.interactive, client_id=config.client_id,
            authorization_timeout=config.authorization_timeout, timeout=config.timeout)
        # The endpoint belongs to this issuer only; a reference from another issuer finds none.
        resolver = OAuthHttpResolver({issuer: ResolveEndpoint(endpoint, credential)},
                                     agent_token=agent_token, timeout=config.timeout)
        sink = ProtectedFileSink(provenance, resolver, principal="resolver-token-subject")
        result = sink.write(destination, content)
    except ResolverClientError as error:
        report.failure = f"resolution failed: {error.code}"
    except (UnknownReference, AmbiguousReference):
        report.failure = "the content holds a reference without exactly one trusted issuer"
    except ResolutionError:
        report.failure = "resolution failed"
    except OSError as error:
        report.failure = f"the file was not written: {type(error).__name__}"
    else:
        report.materialized = True
        report.references_sent = len({ref.token for ref in find_tokens(content)})
        written = destination.read_text(encoding="utf-8")
        report.sentinels_in_file = sum(written.count(v) for v in sentinels if v)
        report.model_content_keeps_reference = all(ref in result.model_facing_content for ref in usable)
        report.sentinels_in_model_content = sum(result.model_facing_content.count(v) for v in sentinels if v)
    finally:
        if resolver is not None:
            report.resolve_requests = resolver.requests
        if credential is not None:
            report.resolver_token_source = credential.source
    return report


def _check_materialization(report: HostReport, m: MaterializeReport) -> None:
    if m.failure:
        report.failures.append(f"materialize: {m.failure}")
        return
    if not m.model_content_keeps_reference:
        report.failures.append("materialize: the model-facing content lost a reference")
    if m.sentinels_in_model_content:
        report.failures.append("materialize: a sentinel value reached the model-facing content")


async def run(args: argparse.Namespace) -> HostReport:
    import httpx2
    from mcp import ClientSession
    from mcp.client.streamable_http import streamable_http_client

    token = os.environ.get(args.token_env, "")
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    sentinels = [v.strip() for v in os.environ.get(args.sentinels_env, "").split(",") if v.strip()]
    declared = not args.legacy
    # The report holds the public part of the URL only.
    report = HostReport(server=public_endpoint(args.url), declared=declared)
    # The issuer is the protected resource. By default that is the MCP URL as
    # given; a server that publishes its RFC 9728 metadata for a parent
    # resource is named with --resource, and the MCP URL must lie under it.
    try:
        endpoint = issuer_identity(args.url)
        issuer = issuer_identity(args.resource) if getattr(args, "resource", None) else endpoint
    except ValueError:
        report.failures.append("the MCP URL or the resource holds user information or a fragment")
        return report
    if issuer != endpoint:
        if not _within(endpoint, issuer):
            report.failures.append("the MCP URL is not under the configured resource")
            return report
    provenance = ProvenanceStore()
    resolving = bool(getattr(args, "resolve_into", None))
    host_settings = dict(RESOLVING_HOST_SETTINGS if resolving else HOST_SETTINGS)
    extensions = {args.extension_id: host_settings} if declared else {}
    agreed = None
    first_references: list[str] = []

    async with httpx2.AsyncClient(headers=headers, timeout=args.timeout) as http:
        async with streamable_http_client(args.url, http_client=http) as (read, write, *_):
            async with ClientSession(read, write, extensions=extensions) as session:
                discovered = await session.discover()
                server_ext = (discovered.capabilities.extensions or {}).get(args.extension_id)
                report.advertised = server_ext is not None
                if declared and server_ext is not None:
                    try:
                        agreed = negotiate(SensitiveReferencesCapabilities.from_settings(host_settings),
                                           SensitiveReferencesCapabilities.from_settings(server_ext))
                    except CapabilitySettingsError:
                        report.failures.append("server settings rejected")
                        agreed = None
                    report.negotiated_version = agreed.version if agreed else None
                negotiated = report.negotiated_version is not None

                first = await session.call_tool(args.tool, json.loads(args.arguments))
                call = inspect_result(args.tool, first, issuer=issuer, negotiated=negotiated,
                                      provenance=provenance, sentinels=sentinels,
                                      refusal_pattern=args.refusal_pattern)
                report.calls.append(call)
                _check(report, call, expect_success=args.expect_success)
                first_references = [ref.token for text in model_visible(first) for ref in find_tokens(text)]

                if args.then_tool:
                    references = sorted({ref.token for text in model_visible(first) for ref in find_tokens(text)})
                    usable = [r for r in references if _trusted(provenance, r)]
                    template = args.then_arguments
                    if "{ref}" in template and not usable:
                        # Nothing to fill in: a literal placeholder is not sent.
                        if negotiated:
                            report.failures.append("no observed reference to pass on")
                    else:
                        filled = template.replace("{ref}", usable[0]) if usable else template
                        second = await session.call_tool(args.then_tool, json.loads(filled))
                        call = inspect_result(args.then_tool, second, issuer=issuer, negotiated=negotiated,
                                              provenance=provenance, sentinels=sentinels,
                                              refusal_pattern=args.refusal_pattern)
                        report.calls.append(call)
                        _check(report, call, expect_success=args.expect_success)
    if declared and args.expect_negotiation and not report.negotiated_version:
        report.failures.append("the extension was not negotiated")
    if resolving:
        # After the MCP session: an interactive authorization can take minutes.
        report.materialization = materialize(
            issuer=issuer, references=first_references, provenance=provenance, agreed=agreed,
            config=resolve_config(args), sentinels=sentinels, agent_token=token or None, mcp_url=endpoint)
        _check_materialization(report, report.materialization)
    return report


def _within(url: str, resource: str) -> bool:
    """``url`` is ``resource`` or a path below it, on the same origin."""
    a, b = urlsplit(url), urlsplit(resource)
    if (a.scheme, a.netloc) != (b.scheme, b.netloc):
        return False
    base = b.path.rstrip("/")
    return a.path == b.path or a.path.startswith(base + "/")


def _open_browser(url: str) -> None:
    import webbrowser

    # The URL holds no secret (PKCE sends only the challenge); stderr keeps it out of the report.
    print(f"Open this page to authorize the resolver: {url}", file=sys.stderr)
    webbrowser.open(url)


def _print_url(url: str) -> None:
    print(f"Open this page to authorize the resolver: {url}", file=sys.stderr)


def resolve_config(args: argparse.Namespace) -> ResolveConfig:
    return ResolveConfig(
        destination=args.resolve_into, template=args.materialize_template,
        resolve_endpoint=args.resolve_endpoint, resolve_scope=args.resolve_scope,
        authorization_server=args.authorization_server, client_id=args.resolver_client_id,
        token_cache=args.resolver_token_cache, interactive=not args.no_interactive,
        no_metadata=args.no_resource_metadata, open_browser=_print_url if args.no_browser else open_browser,
        authorization_timeout=args.authorization_timeout, timeout=args.timeout)


#: Replaced in tests; a real run opens the system browser.
open_browser = _open_browser


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--url", required=True, help="the MCP endpoint")
    parser.add_argument("--extension-id", required=True,
                        help="the extension identifier the server uses (not fixed by concept 0.5)")
    parser.add_argument("--tool", required=True)
    parser.add_argument("--arguments", default="{}")
    parser.add_argument("--then-tool", help="a second call that passes an observed reference")
    parser.add_argument("--then-arguments", default="{}", help="JSON; {ref} is replaced by a reference")
    parser.add_argument("--legacy", action="store_true", help="declare nothing (a host without the extension)")
    parser.add_argument("--expect-negotiation", action="store_true")
    parser.add_argument("--expect-success", action="store_true",
                        help="fail when a call returns isError or a structured reference refusal")
    parser.add_argument("--refusal-pattern", default=DEFAULT_REFUSAL,
                        help="regular expression for a structured error code that means 'refused'")
    parser.add_argument("--token-env", default="MCP_TOKEN", help="environment variable with the bearer token")
    parser.add_argument("--sentinels-env", default="SREF_SENTINELS",
                        help="environment variable with comma-separated values that must not appear")
    parser.add_argument("--timeout", type=float, default=30.0)
    resolve = parser.add_argument_group("materialization (oauth-resolver-1 and local-file-1)")
    resolve.add_argument("--resolve-into", metavar="PATH",
                         help="after the first call, write the template for each observed reference to this file")
    resolve.add_argument("--materialize-template", default="{ref}\n",
                         help="text written once per reference; {ref} is replaced by the reference")
    resolve.add_argument("--resolve-endpoint", help="the resolve endpoint (default: protected-resource metadata)")
    resolve.add_argument("--resource", help="the protected-resource identifier (RFC 9728) when the server publishes "
                                            "its metadata for a parent of the MCP URL; default: the MCP URL")
    resolve.add_argument("--no-resource-metadata", action="store_true",
                         help="the server publishes no RFC 9728 metadata: go on with --resolve-endpoint and "
                              "--authorization-server (configuration mode, not SC-01 or SC-02 conformant)")
    resolve.add_argument("--resolve-scope", help="the resolve scope (default: the discovery object; without "
                                                 f"one, configuration mode: {RESOLVE_SCOPE})")
    resolve.add_argument("--authorization-server",
                         help="the authorization server issuer (default: the only one in the metadata)")
    resolve.add_argument("--resolver-client-id", help="a registered client; without it the host uses dynamic registration")
    resolve.add_argument("--resolver-token-cache", metavar="PATH",
                         help="file for the resolver token (mode 0600); without it the token is not kept")
    resolve.add_argument("--no-interactive", action="store_true",
                         help="use only a cached or refreshed resolver token; never open an authorization page")
    resolve.add_argument("--no-browser", action="store_true",
                         help="print the authorization page URL to stderr instead of opening a browser")
    resolve.add_argument("--authorization-timeout", type=float, default=300.0)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        report = asyncio.run(run(args))
    except Exception as e:  # noqa: BLE001 — a transport message can quote the full URL
        report = HostReport(server=public_endpoint(args.url), declared=not args.legacy)
        report.failures.append(f"the run failed: {type(e).__name__}")
    out = asdict(report)
    out["ok"] = report.ok
    print(json.dumps(out, indent=2))
    return 0 if report.ok else 1


if __name__ == "__main__":
    sys.exit(main())
