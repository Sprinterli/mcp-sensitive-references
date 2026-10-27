"""Mutation probe for the guards of the test host and the resolver client.

For each mutation the script copies ``prototype/`` into a temporary directory
outside the repository, disables one guard in the copy, runs
``tests/test_mcp_host_resolve.py`` there, and reports KILLED (at least one
test failed) or SURVIVED. The script never writes into the repository.

    python prototype/tests/tools/mutation_probe.py [--work DIR] [--only TEXT]

Rounds 2 to 6 of the review (see the docstring of ``test_mcp_host_resolve.py``
and ``protocol-package/CONFORMANCE-RESULTS.md``). The mutations of earlier rounds
are applied to the current text.
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
    ("r4 is_global replaced by is_private", RC, "    if not ip.is_global or ip.is_multicast", "    if ip.is_private or ip.is_multicast"),
    # -- round 5 (Codex H2: the request connects to the checked address)
    ("r5 http connects to the host name again", RC,
     "        self.sock = socket.create_connection((self._address, self.port), self.timeout)\n",
     "        self.sock = socket.create_connection((self.host, self.port), self.timeout)\n"),
    ("r5 https connects to the host name again", RC,
     "        sock = socket.create_connection((self._address, self.port), self.timeout)\n",
     "        sock = socket.create_connection((self.host, self.port), self.timeout)\n"),
    ("r5 https verifies the address instead of the host name", RC,
     "server_hostname=self.host)", "server_hostname=self._address)"),
    ("r5 a request without a checked address is sent", RC,
     '        raise URLError("no checked address for the request")', "        return req.host.split(':')[0]"),
    ("r5 the real opener does not pin", RC,
     "_NoRedirect, _PinnedHTTP, _PinnedHTTPS)", "_NoRedirect)"),
    ("r6 the real opener does not verify certificates", RC,
     "_NoRedirect, _PinnedHTTP, _PinnedHTTPS)",
     "_NoRedirect, _PinnedHTTP, _PinnedHTTPS(context=__import__('ssl')._create_unverified_context()))"),
    ("r6 the pinned TLS connection does not verify", RC,
     "        self.sock = self._context.wrap_socket(sock, server_hostname=self.host)",
     "        self.sock = __import__('ssl')._create_unverified_context().wrap_socket(sock, server_hostname=self.host)"),
    ("r4 multicast counted as public", RC, "    if not ip.is_global or ip.is_multicast or", "    if not ip.is_global or"),
    ("r4 site-local counted as public", RC,
     " or (isinstance(ip, ipaddress.IPv6Address) and ip.is_site_local):", ":"),
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


def run(work: Path, only: str | None) -> int:
    survived = 0
    for name, relative, original, replacement in MUTATIONS:
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
            [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests/test_mcp_host_resolve.py"],
            cwd=copy, env={**os.environ, "PYTHONPATH": "src"}, capture_output=True, text=True, timeout=600)
        failed = sorted({line.split(" ")[1].split("::")[-1] for line in result.stdout.splitlines()
                         if line.startswith(("FAILED", "SUBFAIL", "ERROR"))})
        if result.returncode:
            print(f"KILLED   {name} | {', '.join(failed)}")
        else:
            survived += 1
            print(f"SURVIVED {name}")
    print(f"{len(MUTATIONS) - survived if not only else '-'} killed, {survived} survived or stale")
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
