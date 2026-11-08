"""Mutation probe for the guards of the test host and the resolver client.

For each mutation the script copies ``prototype/`` into a temporary directory
outside the repository, disables one guard in the copy, runs the test module of
that mutation there (``tests/test_mcp_host_resolve.py`` for rounds 2 to 9), and
reports KILLED (at least one test failed) or SURVIVED. The script never writes
into the repository.

    python prototype/tests/tools/mutation_probe.py [--work DIR] [--only TEXT]

Rounds 2 to 9 of the review (see the docstring of ``test_mcp_host_resolve.py``
and ``protocol-package/CONFORMANCE-RESULTS.md``). The mutations of earlier rounds
are applied to the current text. Round 10 holds the rules of Concept 0.7: the
prototype issuer (``tests/test_issuer_server.py``) and the host sinks, discovery
and scope choice (``tests/test_concept_07_host.py``).
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

PROTOTYPE = Path(__file__).resolve().parents[2]
RC = "src/sensitive_references/resolver_client.py"
HOST = "demo/mcp_host.py"
IS = "src/sensitive_references/issuer_server.py"
PS = "src/sensitive_references/process_sink.py"
DS = "src/sensitive_references/display_sink.py"
OG = "src/sensitive_references/output_guard.py"
T_HOST = "tests/test_mcp_host_resolve.py"
T_IS = "tests/test_issuer_server.py"
T_07 = "tests/test_concept_07_host.py"

#: (name, file, original text, replacement). The original text must occur exactly once.
MUTATIONS = [
    # -- round 2
    ("r2 well-known keeps the query", RC,
     'f"/.well-known/{suffix}{path}", parts.query, ""))', 'f"/.well-known/{suffix}{path}", "", ""))'),
    ("r2 well-known keeps a trailing slash of a resource", RC,
     'path = parts.path.rstrip("/") if strip_slash else ("" if parts.path == "/" else parts.path)',
     'path = parts.path.rstrip("/")'),
    ("r2 challenge before well-known", RC,
     "    if named is not None:\n        document = _metadata_document(require_secure(",
     "    if named is not None and _metadata_document(protected_resource_metadata_url(resource), timeout, "
     "policy) is None:\n        document = _metadata_document(require_secure("),
    ("r2 no challenge for a parent resource", HOST,
     "use_challenge = mcp_url is None or mcp_url == issuer", "use_challenge = True"),
    ("r2 no metadata fails closed", HOST,
     "        if not config.no_metadata:\n            raise", "        if False:\n            raise"),
    ("r2 unreachable fails closed", HOST,
     'if error.code != "unreachable" or not config.no_metadata:', 'if error.code != "unreachable":'),
    ("r2 origin check for a configured endpoint", HOST,
     "    if origin(endpoint) != origin(issuer):",
     "    if config.resolve_endpoint is None and origin(endpoint) != origin(issuer):"),
    ("r2 PKCE S256 required", RC,
     'if not isinstance(methods, list) or "S256" not in methods:', 'if methods is not None and "S256" not in methods:'),
    ("r2 issuer refuses user information and a fragment", HOST,
     '        raise ValueError("the URL holds user information or a fragment")', "        pass"),
    ("r2 issuer keeps the query", HOST,
     "    return url\n\n\ndef public_endpoint", "    return public_endpoint(url)\n\n\ndef public_endpoint"),
    ("r2 resource identifier refuses a fragment", RC, '    if "#" in resource:', "    if False:"),
    ("r2 non-empty resolve_scope and resolve_endpoint", RC,
     "if not isinstance(extra.get(name), str) or not extra[name]:", "if not isinstance(extra.get(name), str):"),
    ("r2 --no-resource-metadata maps to the configuration", HOST,
     "no_metadata=args.no_resource_metadata,", "no_metadata=False,"),
    # -- round 3
    ("r3 fetch policy: no check before a request", RC, '    addresses = policy.targets(url, "request")\n',
     '    addresses = ["127.0.0.1"]\n'),
    ("r3 fetch policy: endpoints of authorization-server metadata not checked", RC,
     "            return policy.check(require_secure(document[name], what), what)",
     "            return require_secure(document[name], what)"),
    ("r3 fetch policy: every target allowed", RC,
     "connects to one of them.\"\"\"\n        addresses =",
     "connects to one of them.\"\"\"\n        return [\"127.0.0.1\"]\n        addresses ="),
    ("r3 fetch policy: host names not resolved", RC, "        return _lookup(host) or None", "        return []"),
    ("r3 fetch policy: an unresolvable name allowed", RC,
     "    except OSError:\n        return None", "    except OSError:\n        return []"),
    ("r3 fetch policy: IPv4-mapped IPv6 not unwrapped", RC,
     "    if ip.ipv4_mapped is not None:\n        return ip.ipv4_mapped",
     "    if False:\n        return ip.ipv4_mapped"),
    ("r3 RFC 8414 keeps a terminating slash of the issuer", RC,
     '_well_known(issuer, "oauth-authorization-server", insert=True, strip_slash=True)',
     '_well_known(issuer, "oauth-authorization-server", insert=True)'),
    ("r3 metadata without the discovery object accepted", HOST,
     "        if not config.no_discovery_object:\n            raise",
     "        if False:\n            raise"),
    ("r3 configuration mode not labelled", HOST, "        report.non_conformant += found\n", ""),
    ("r3 P16 not labelled", HOST,
     "            deviations=parent, policy=policy)", "            deviations=[], policy=policy)"),
    ("r3 --no-discovery-object maps to the configuration", HOST,
     "no_discovery_object=args.no_discovery_object,", "no_discovery_object=False,"),
    ("r3 a challenge URL without a document is no metadata", RC,
     "        if document is None:\n            raise ResolverClientError(\"metadata_unavailable\"",
     "        if False:\n            raise ResolverClientError(\"metadata_unavailable\""),
    # -- round 4
    ("r4 local mode without the operator option", RC,
     "self.local = bool(allow_local and self.mcp_addresses", "self.local = bool(self.mcp_addresses"),
    ("r4 local mode when one MCP address is non-public (mixed records)", RC,
     "and all(non_public_address(a) for a in self.mcp_addresses))",
     "and any(non_public_address(a) for a in self.mcp_addresses))"),
    ("r4 local mode removed", RC, "        if (self.local and addresses is not None", "        if (False and addresses is not None"),
    ("r4 the MCP host resolved again at each check", RC,
     "connects to one of them.\"\"\"\n        addresses =",
     "connects to one of them.\"\"\"\n        self.local =self.local or all(non_public_address(a) "
     "for a in (_addresses(urlsplit(self.protected_resource).hostname) or [\"20.0.0.1\"]))\n        addresses ="),
    ("r4 local mode allows any origin", RC, " and origin(url) in self.local_origins", ""),
    ("r4 local mode allows link-local, unspecified and multicast", RC,
     "                and not any(never_a_target(a) for a in addresses)):", "                ):"),
    ("r4 never-a-target ignores an embedded IPv4 address", RC,
     "               for i in (ip, embedded) if i is not None)", "               for i in (ip,))"),
    ("r4 is_global replaced by is_private", RC, "    return ip.is_global\n", "    return not ip.is_private\n"),
    # -- round 5 (Codex H2: the request connects to the checked address)
    ("r5 http connects to the host name again", RC,
     "    # The base class keeps its audit event and TCP_NODELAY; only the address lookup is replaced.\n    def __init__(self, *args, addresses: Sequence[str], **kwargs) -> None:\n        super().__init__(*args, **kwargs)\n        self._create_connection", "    # The base class keeps its audit event and TCP_NODELAY; only the address lookup is replaced.\n    def __init__(self, *args, addresses: Sequence[str], **kwargs) -> None:\n        super().__init__(*args, **kwargs)\n        self._unused"),
    ("r5 https connects to the host name again", RC,
     "    # TLS verifies the certificate for the host of the URL (``HTTPSConnection.connect``).\n    def __init__(self, *args, addresses: Sequence[str], **kwargs) -> None:\n        super().__init__(*args, **kwargs)\n        self._create_connection", "    # TLS verifies the certificate for the host of the URL (``HTTPSConnection.connect``).\n    def __init__(self, *args, addresses: Sequence[str], **kwargs) -> None:\n        super().__init__(*args, **kwargs)\n        self._unused"),
    ("r5 a request without a checked address is sent", RC,
     '        raise URLError("no checked address for the request")', "        return [req.host.rsplit(':', 1)[0]]"),
    ("r5 the real opener does not pin", RC,
     "_NoRedirect, _PinnedHTTP, _PinnedHTTPS(context=context))", "_NoRedirect)"),
    ("r6 the real opener does not verify certificates", RC,
     "_PinnedHTTPS(context=context))",
     "_PinnedHTTPS(context=context or __import__('ssl')._create_unverified_context()))"),
    ("r7 the pinned TLS connection does not verify", RC,
     "    # TLS verifies the certificate for the host of the URL (``HTTPSConnection.connect``).\n    def __init__(self, *args, addresses: Sequence[str], **kwargs) -> None:\n        super().__init__(*args, **kwargs)\n",
     "    # TLS verifies the certificate for the host of the URL (``HTTPSConnection.connect``).\n    def __init__(self, *args, addresses: Sequence[str], **kwargs) -> None:\n        super().__init__(*args, **kwargs)\n        self._context = __import__('ssl')._create_unverified_context()\n"),
    # -- round 8 (Opus: each checked address, the timeout, three IANA entries)
    ("r8 only the first checked address is tried", RC, "    for address in addresses:\n        try:",
     "    for address in addresses[:1]:\n        try:"),
    ("r8 the connection timeout is dropped", RC,
     "socket.create_connection((address, port), timeout, source_address)",
     "socket.create_connection((address, port), None, source_address)"),
    ("r9 the Dummy IPv6 Prefix counted as public", RC, '"5f00::/16", "100:0:0:1::/64", ', '"5f00::/16", '),
    ("r8 the public IANA correction is dropped", RC, "    if any(ip in n for n in _GLOBAL_ADDED",
     "    if False and any(ip in n for n in _GLOBAL_ADDED"),
    ("r8 the non-public IANA corrections are dropped", RC, "    if any(ip in n for n in _NOT_GLOBAL_ADDED",
     "    if False and any(ip in n for n in _NOT_GLOBAL_ADDED"),
    ("r4 multicast counted as public", RC, "    if not _globally_reachable(ip) or ip.is_multicast or (", "    if not _globally_reachable(ip) or ("),
    ("r4 site-local counted as public", RC,
     "            isinstance(ip, ipaddress.IPv6Address) and ip.is_site_local):", "            False):"),
    ("r4 NAT64 and IPv4-compatible not unwrapped", RC,
     "    if ip in _NAT64 or (ip in _COMPATIBLE and int(ip) > 1):", "    if False:"),
    ("r4 6to4 not unwrapped", RC, "    if ip.sixtofour is not None:", "    if False:"),
    ("r4 the embedded IPv4 address not judged", RC,
     "    return embedded is not None and non_public_address(str(embedded))", "    return False"),
    ("r4 a proxy from the environment", RC,
     "build_opener(ProxyHandler({}), _NoRedirect,", "build_opener(_NoRedirect,"),
    ("r4 redirects followed", RC,
     "build_opener(ProxyHandler({}), _NoRedirect,", "build_opener(ProxyHandler({}),"),
    ("r4 local mode on by default", HOST, "    allow_local: bool = False\n", "    allow_local: bool = True\n"),
    ("r4 --allow-local-targets maps to the configuration", HOST,
     "allow_local=args.allow_local_targets,", "allow_local=False,"),
    ("r4 --local-origin maps to the configuration", HOST,
     "local_origins=tuple(args.local_origin or ()),", "local_origins=(),"),
]

#: Round 10 (Concept 0.7): (name, file, original text, replacement, test module).
MUTATIONS_07 = [
    # -- the issuer: discovery and scopes (RESOLVER-PROFILE.md, sections 4 and 5)
    ("r10 discovery: sinks name the resolve scope only", IS,
     '"scopes": list(scope_set(p))} for p in self.sinks}', '"scopes": [RESOLVE_SCOPE]} for p in self.sinks}', T_IS),
    ("r10 scope: a sink scope without the resolve scope accepted", IS,
     "        if RESOLVE_SCOPE not in requested:\n            return None",
     "        if False:\n            return None", T_IS),
    ("r10 scope: an agent scope next to the resolve scope accepted", IS,
     'if requested - {RESOLVE_SCOPE, "openid"} - set(self.sink_scopes()):', "if False:", T_IS),
    ("r10 scope: a sink scope that the server does not offer accepted", IS,
     '- {RESOLVE_SCOPE, "openid"} - set(self.sink_scopes()):', '- {RESOLVE_SCOPE, "openid"} - {PROCESS_SCOPE, DISPLAY_SCOPE}:',
     T_IS),
    ("r10 insufficient_scope: no sink-scope check", IS,
     "        if not set(scope_set(profile)) <= record[\"scopes\"]:\n            return self._insufficient(profile)",
     "        if False:\n            return self._insufficient(profile)", T_IS),
    ("r10 insufficient_scope: the header names no scope", IS,
     """f'Bearer error="insufficient_scope", scope="{scope}", '""", """f'Bearer error="insufficient_scope", '""", T_IS),
    ("r10 insufficient_scope: the body has no error_description", IS,
     '_error(403, "insufficient_scope", error_description=text, scope=scope)',
     '_error(403, "insufficient_scope", scope=scope)', T_IS),
    ("r10 refresh: a scope added", IS,
     'if "scope" in form and not set(form["scope"].split()) <= record["scopes"]:', "if False:", T_IS),
    ("r10 ineligible_sink: sink_type not compared exactly", IS,
     'SINK_TYPES[p] == body["sink_type"]), None)', 'SINK_TYPES[p] == body["sink_type"].lower()), None)', T_IS),
    # -- consent (section 10)
    ("r10 consent: a stored approval replaces the page", IS,
     "        # Section 10.1: a stored approval never replaces this page.\n",
     "        if any(k[:2] == (subject, request['client_id']) for k in self.approvals):\n"
     "            self.nonces['x'] = (session or '', request_id)\n"
     "            return self.consent(session, {'nonce': 'x', 'decision': 'approve'}, self.origin)\n", T_IS),
    ("r10 consent: the page names no account", IS, '"account": subject,', '"account": "",', T_IS),
    ("r10 consent: the page names no loopback port", IS,
     '"loopback": f"{loopback.hostname}:{loopback.port}",', '"loopback": f"{loopback.hostname}",', T_IS),
    ("r10 consent: no line per sink scope", IS,
     '"sink_lines": [CONSENT_LINES[s] for s in sorted(request["scopes"]) if s in CONSENT_LINES],',
     '"sink_lines": [],', T_IS),
    ("r10 consent: use another account keeps the session", IS,
     '        self.sessions.pop(session or "", None)\n', "        pass\n", T_IS),
    ("r10 consent: the nonce is not single-use", IS,
     "bound = self.nonces.pop(nonce, None) if nonce else None", "bound = self.nonces.get(nonce) if nonce else None",
     T_IS),
    ("r10 consent: no Origin check", IS, "if bound is None or origin != self.origin:", "if bound is None:", T_IS),
    ("r10 consent: the nonce is not bound to the session", IS,
     "if not session or not hmac.compare_digest(bound_session, session) or request_id not in self.pending:",
     "if not session or request_id not in self.pending:", T_IS),
    ("r10 loopback: the path or the query may change with the port", IS,
     "return (a.scheme, a.hostname, a.path, a.query) == (b.scheme, b.hostname, b.path, b.query)",
     "return (a.scheme, a.hostname) == (b.scheme, b.hostname)", T_IS),
    ("r10 registration: a redirect URI that is not loopback", IS,
     "        if not all(_loopback_redirect(u) for u in uris):", "        if False:", T_IS),
    # -- per person, account hint, audit (sections 11.2, 12.2, 15)
    ("r10 per person: a lookup in the records of every person", IS,
     "own = self.records.get(subject, {})",
     "own = {k: v for records in self.records.values() for k, v in records.items()}", T_IS),
    ("r10 account hint: the whole account", IS,
     '"account_hint": account_hint(grant["subject"])', '"account_hint": grant["subject"]', T_IS),
    ("r10 account hint: more than half of the local part", IS,
     "keep = min(3, len(local) // 2)", "keep = min(3, len(local))", T_IS),
    ("r10 audit: values without the audit event", IS,
     '        except AuditUnavailable:\n            return _error(503, "audit_unavailable")',
     "        except AuditUnavailable:\n            pass", T_IS),
    ("r10 audit: the destination of a command kept whole", IS,
     'return last if last and not any(c.isspace() for c in destination) else "other"', "return destination", T_IS),
    ("r10 display: another destination or more than one reference", IS,
     "if profile == DISPLAY and (destination != SCREEN or len(unique) != 1 or len(references) != 1):", "if False:",
     T_IS),
    # -- devices (section 10.4)
    ("r10 devices: no epoch check", IS,
     'return epoch is not None and epoch == record["epoch"] and live', "return live", T_IS),
    ("r10 devices: no live-approval check", IS,
     'return epoch is not None and epoch == record["epoch"] and live',
     'return epoch is not None and epoch == record["epoch"]', T_IS),
    ("r10 devices: a revocation does not raise the epoch", IS,
     "            self.epochs[device] = self.epochs.get(device, 0) + 1\n", "            pass\n", T_IS),
    ("r10 devices: a revocation stops other people on the client", IS,
     'if (r["subject"], r["client_id"]) == device]:', 'if r["client_id"] == client_id]:', T_IS),
    ("r10 devices: anyone manages any device", IS,
     "        if actor != principal and actor not in self.admins:", "        if False:", T_IS),
    # -- the host: discovery and scope choice
    ("r10 host: sinks not required", RC,
     '        raise ResolverClientError("malformed_discovery", "the discovery object has no valid sinks")',
     "        sinks = {}", T_07),
    ("r10 host: a sinks member without the resolve scope", RC,
     ' or extra["resolve_scope"] not in scopes):', "):", T_07),
    ("r10 host: process_scope not compared with sinks", RC,
     "if not isinstance(extra[name], str) or not extra[name] or extra[name] not in named \\",
     "if not isinstance(extra[name], str) or not extra[name] \\", T_07),
    ("r10 host: max_references not checked", RC, "    if type(limit) is not int or limit < MAX_BATCH:",
     "    if False:", T_07),
    ("r10 host: the scope set not taken from sinks", RC,
     "            for scope in self.sinks[profile][1]:", "            for scope in self.sinks[profile][1][:1]:", T_07),
    ("r10 host: a token without the sink scope is sent", RC,
     "        if not needed <= endpoint.credential.granted_scopes():", "        if False:", T_07),
    ("r10 host: a sink that the run did not negotiate is sent", RC,
     "        if needed is None:\n            raise", "        if False:\n            raise", T_07),
    ("r10 host: a display request with two references or another destination", RC,
     "if sink_context.sink_type == SINK_TYPES[DISPLAY] and (len(unique) != 1 or sink_context.destination != SCREEN):",
     "if False:", T_07),
    ("r10 host: process-1 declared where output is not masked", HOST,
     "sinks = [p for p in config.profiles() if p != PROCESS or process_sink.supported()]",
     "sinks = list(config.profiles())", T_07),
    ("r10 host: a negotiated sink without its sinks member", HOST,
     "if profile not in metadata.sinks or metadata.sinks[profile][0] != SINK_TYPES[profile]:", "if False:", T_07),
    ("r10 host: one authorization per resolve (no in-memory token)", RC,
     "                self._memory[key] = entry", "                pass", T_07),
    ("r10 host: run() opens one session per sink", HOST,
     "mcp_url=endpoint, policy=policy))\n            return opened[0]\n",
     "mcp_url=endpoint, policy=policy))\n            return opened.pop()\n", T_07),
    # -- process-1 (PROCESS-PROFILE.md)
    ("r10 process: the command line as destination", PS,
     "context = SinkContext(SINK_TYPES[PROCESS], program, self._principal)",
     "context = SinkContext(SINK_TYPES[PROCESS], command, self._principal)", T_07),
    ("r10 process: assignments not skipped", PS, "        if _ASSIGNMENT.fullmatch(word):\n            continue",
     "        if False:\n            continue", T_07),
    ("r10 process: the whole path as program", PS,
     'name = word.replace("\\\\", "/").rstrip("/").rsplit("/", 1)[-1]', "name = word", T_07),
    ("r10 process: a refused command runs", PS, "        if not approve(program, command):", "        if False:", T_07),
    ("r10 process: resolve before the command reads", PS,
     "        threads = [threading.Thread(target=serve, args=item, daemon=True) for item in pipes]",
     "        with lock:\n            if trusted:\n                resolve_all()\n"
     "        threads = [threading.Thread(target=serve, args=item, daemon=True) for item in pipes]", T_07),
    ("r10 process: a failed resolve does not stop the command", PS,
     "                _kill(process)\n                return\n            self._mask.release(values)",
     "                return\n            self._mask.release(values)", T_07),
    ("r10 process: output not masked", PS, "            result.model_output = self._mask.mask(text)",
     "            result.model_output = text", T_07),
    ("r10 process: base64 and percent forms not masked", OG,
     "    for encoded in (b64encode(raw).decode(), urlsafe_b64encode(raw).decode()):", "    for encoded in ():", T_07),
    ("r10 process: an unobserved reference sent", PS,
     "        trusted = {t: issuer for t, issuer in trusted.items() if issuer is not None}",
     "        trusted = {t: issuer or 'x' for t, issuer in trusted.items()}", T_07),
    ("r10 process: no pipe platform check", PS, "        if not supported():\n", "        if False:\n", T_07),
    # -- display-1 (DISPLAY-PROFILE.md)
    ("r10 display: no user action needed", DS,
     "        if not isinstance(action, UserAction) or action.kind != kind:", "        if False:", T_07),
    ("r10 display: an action used twice", DS, "        if action.used:", "        if False:", T_07),
    ("r10 display: another destination than the screen", DS,
     "SinkContext(SINK_TYPES[DISPLAY], SCREEN,", 'SinkContext(SINK_TYPES[DISPLAY], "terminal",', T_07),
    ("r10 display: a held value resolved again", DS,
     "        held = self._mask.held(reference)\n        if held is None:\n            if self.requests",
     "        held = None\n        if held is None:\n            if self.requests", T_07),
    ("r10 display: a copy without a reveal", DS,
     "if reference not in self._shown or held is None or self._clipboard is None:",
     "if held is None or self._clipboard is None:", T_07),
    ("r10 display: no session limit", DS, "            if self.requests >= self._limit:", "            if False:", T_07),
    ("r10 display: an untrusted reference resolved", DS,
     "            issuer = self._provenance.issuer_for(reference)", '            issuer = "x"', T_07),
    ("r10 display: the value not kept for the session", DS,
     "            self._mask.release(values)\n            held = values[reference]",
     "            held = values[reference]", T_07),
]


def run(work: Path, only: str | None) -> int:
    survived = 0
    mutations = [(*m, T_HOST) for m in MUTATIONS] + MUTATIONS_07
    for name, relative, original, replacement, tests in mutations:
        if only and only not in name:
            continue
        copy = work / "prototype"
        if copy.exists():
            shutil.rmtree(copy)
        shutil.copytree(PROTOTYPE, copy, ignore=shutil.ignore_patterns("__pycache__", ".DS_Store", "output"))
        target = copy / relative
        text = target.read_text(encoding="utf-8")
        if text.count(original) != 1:
            print(f"STALE    {name} | the original text occurs {text.count(original)} times")
            survived += 1
            continue
        target.write_text(text.replace(original, replacement), encoding="utf-8")
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", tests],
            cwd=copy, env={**os.environ, "PYTHONPATH": "src", "PYTHONDONTWRITEBYTECODE": "1"},
            capture_output=True, text=True, timeout=600)
        failed = sorted({line.split(" ")[1].split("::")[-1] for line in result.stdout.splitlines()
                         if line.startswith(("FAILED", "SUBFAIL", "ERROR"))})
        if result.returncode:
            print(f"KILLED   {name} | {', '.join(failed)}")
        else:
            survived += 1
            print(f"SURVIVED {name}")
    print(f"{len(mutations) - survived if not only else '-'} killed, {survived} survived or stale")
    return 1 if survived else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--work", type=Path, help="a directory outside the repository (default: a new temporary one)")
    parser.add_argument("--only", help="run only the mutations whose name holds this text")
    args = parser.parse_args()
    work = args.work or Path(tempfile.mkdtemp(prefix="sref-mutation-"))
    if work.resolve().is_relative_to(PROTOTYPE.parent):
        parser.error("the work directory must be outside the repository")
    work.mkdir(parents=True, exist_ok=True)
    try:
        return run(work, args.only)
    finally:
        if args.work is None:
            shutil.rmtree(work, ignore_errors=True)
        else:
            shutil.rmtree(work / "prototype", ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
