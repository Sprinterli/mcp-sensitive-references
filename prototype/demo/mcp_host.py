"""An independent test host for Sensitive References over a real MCP connection.

It connects to any MCP server by URL with the MCP SDK client, declares the
extension (or, with ``--legacy``, declares nothing), and checks what a model
would be handed: every tool result is read as the host receives it, before any
model sees it.

What it checks, per tool call:

* negotiation: the server advertised the extension with a version the host
  declared, and the host records observations only then;
* provenance: each canonical token is recorded with its issuer and the time it
  was first seen. The issuer is the server URL the host connected to, without
  credentials, query or fragment. This identity is experimental: it is a
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
from urllib.parse import urlsplit, urlunsplit

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

#: Anything that starts like a reference; a canonical token must match exactly.
_REFERENCE_LIKE = re.compile(r"(?i)sref\s*:")
HOST_SETTINGS = {"versions": ["1"]}

#: A structured failure code that names one of the failure reasons of concept
#: 0.5 for a reference (``PII_REFERENCE_UNKNOWN``, ``reference_revoked``).
DEFAULT_REFUSAL = r"(?i)reference.{0,3}(malformed|unknown|revoked|expired|stale|ambiguous|unauthori[sz]ed)"
_REFUSAL_FIELDS = ("error_code", "code", "error")


def public_endpoint(url: str) -> str:
    """The URL as a report and an issuer may hold it: no user information, no
    query and no fragment, where a token or a password can sit."""
    parts = urlsplit(url)
    host = parts.hostname or ""
    if parts.port:
        host = f"{host}:{parts.port}"
    return urlunsplit((parts.scheme, host, parts.path, "", ""))


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


async def run(args: argparse.Namespace) -> HostReport:
    import httpx2
    from mcp import ClientSession
    from mcp.client.streamable_http import streamable_http_client

    token = os.environ.get(args.token_env, "")
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    sentinels = [v.strip() for v in os.environ.get(args.sentinels_env, "").split(",") if v.strip()]
    declared = not args.legacy
    # Only the public part of the URL leaves this function: in the report and as the issuer.
    endpoint = public_endpoint(args.url)
    report = HostReport(server=endpoint, declared=declared)
    provenance = ProvenanceStore()
    extensions = {args.extension_id: dict(HOST_SETTINGS)} if declared else {}

    async with httpx2.AsyncClient(headers=headers, timeout=args.timeout) as http:
        async with streamable_http_client(args.url, http_client=http) as (read, write, *_):
            async with ClientSession(read, write, extensions=extensions) as session:
                discovered = await session.discover()
                server_ext = (discovered.capabilities.extensions or {}).get(args.extension_id)
                report.advertised = server_ext is not None
                if declared and server_ext is not None:
                    try:
                        agreed = negotiate(SensitiveReferencesCapabilities.from_settings(HOST_SETTINGS),
                                           SensitiveReferencesCapabilities.from_settings(server_ext))
                    except CapabilitySettingsError:
                        report.failures.append("server settings rejected")
                        agreed = None
                    report.negotiated_version = agreed.version if agreed else None
                negotiated = report.negotiated_version is not None

                first = await session.call_tool(args.tool, json.loads(args.arguments))
                call = inspect_result(args.tool, first, issuer=endpoint, negotiated=negotiated,
                                      provenance=provenance, sentinels=sentinels,
                                      refusal_pattern=args.refusal_pattern)
                report.calls.append(call)
                _check(report, call, expect_success=args.expect_success)

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
                        call = inspect_result(args.then_tool, second, issuer=endpoint, negotiated=negotiated,
                                              provenance=provenance, sentinels=sentinels,
                                              refusal_pattern=args.refusal_pattern)
                        report.calls.append(call)
                        _check(report, call, expect_success=args.expect_success)
    if declared and args.expect_negotiation and not report.negotiated_version:
        report.failures.append("the extension was not negotiated")
    return report


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
