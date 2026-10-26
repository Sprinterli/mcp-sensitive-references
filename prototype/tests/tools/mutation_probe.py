"""Mutation probe for the guards of the test host and the resolver client.

For each mutation the script copies ``prototype/`` into a temporary directory
outside the repository, disables one guard in the copy, runs
``tests/test_mcp_host_resolve.py`` there, and reports KILLED (at least one
test failed) or SURVIVED. The script never writes into the repository.

    python prototype/tests/tools/mutation_probe.py [--work DIR] [--only TEXT]

Rounds 2 and 3 of the review (see the docstring of ``test_mcp_host_resolve.py``
and ``protocol-package/CONFORMANCE-RESULTS.md``). The round 2 mutations here
are the round 2 guards on the text of round 3.
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
    ("r3 fetch policy: no check before a request", RC, '    policy.check(url, "request")\n', ""),
    ("r3 fetch policy: endpoints of authorization-server metadata not checked", RC,
     "            return policy.check(require_secure(document[name], what), what)",
     "            return require_secure(document[name], what)"),
    ("r3 fetch policy: every target allowed", RC,
     "    def check(self, url: str, what: str) -> str:\n        if self.local:",
     "    def check(self, url: str, what: str) -> str:\n        if True:"),
    ("r3 fetch policy: no exception for a local MCP URL", RC,
     "    def check(self, url: str, what: str) -> str:\n        if self.local:",
     "    def check(self, url: str, what: str) -> str:\n        if False:"),
    ("r3 fetch policy: host names not resolved", RC,
     "        return not addresses or any(non_public_address(a) for a in addresses)", "        return False"),
    ("r3 fetch policy: an unresolvable name allowed", RC,
     "        except OSError:\n            return unresolvable", "        except OSError:\n            return False"),
    ("r3 fetch policy: IPv4-mapped IPv6 not unwrapped", RC,
     "    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:",
     "    if False:"),
    ("r3 fetch policy: RFC 4193 range removed", RC, '"fc00::/7", ', ""),
    ("r3 RFC 8414 keeps a terminating slash of the issuer", RC,
     '_well_known(issuer, "oauth-authorization-server", insert=True, strip_slash=True)',
     '_well_known(issuer, "oauth-authorization-server", insert=True)'),
    ("r3 metadata without the discovery object accepted", HOST,
     "        if not config.no_discovery_object:\n            raise",
     "        if False:\n            raise"),
    ("r3 configuration mode not labelled", HOST, "        report.non_conformant += found\n", ""),
    ("r3 P16 not labelled", HOST,
     "            deviations=parent)", "            deviations=[])"),
    ("r3 --no-discovery-object maps to the configuration", HOST,
     "no_discovery_object=args.no_discovery_object,", "no_discovery_object=False,"),
    ("r3 a challenge URL without a document is no metadata", RC,
     "        if document is None:\n            raise ResolverClientError(\"metadata_unavailable\"",
     "        if False:\n            raise ResolverClientError(\"metadata_unavailable\""),
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
