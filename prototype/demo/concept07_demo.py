"""Concept 0.7 demo: one authorization, three sinks, against the prototype issuer on loopback.

Stdlib only. The script starts ``IssuerHttp`` on 127.0.0.1, issues two synthetic
references to the demo account, and runs the host functions of ``mcp_host``:

1. ``local-file-1``: writes ``demo/output/concept07.txt`` (the content is not printed);
2. ``process-1``: runs ``printf`` with the values through pipes and prints the masked
   output, which holds references only (POSIX);
3. ``display-1``: with ``--reveal``, asks on the terminal before each reveal and draws
   the value on the terminal (``/dev/tty``), never on stdout.

The consent page opens in the system browser (account ``demo@example.com``, password
``demo``). ``--headless`` uses the scripted browser instead.

    PYTHONPATH=src python3 demo/concept07_demo.py [--headless] [--reveal]
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
import webbrowser

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import mcp_host  # noqa: E402
from scripted_browser import ScriptedBrowser  # noqa: E402
from sensitive_references import ProvenanceStore, process_sink  # noqa: E402
from sensitive_references.capabilities import NegotiatedSensitiveReferences  # noqa: E402
from sensitive_references.issuer_server import IssuerHttp  # noqa: E402
from sensitive_references.sink_profiles import DISPLAY, LOCAL_FILE, PROCESS  # noqa: E402

ACCOUNT, PASSWORD = "demo@example.com", "demo"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--headless", action="store_true", help="approve with the scripted browser")
    parser.add_argument("--reveal", action="store_true", help="offer each reference for a reveal on the terminal")
    args = parser.parse_args()

    http = IssuerHttp()
    issuer = http.issuer
    issuer.add_account(ACCOUNT, PASSWORD)
    refs = [issuer.issue(ACCOUNT, "email", "alice@example.com"), issuer.issue(ACCOUNT, "password", "pa55-demo")]
    store = ProvenanceStore()
    store.observe_mcp_result(issuer.resource, extension_negotiated=True, result=refs)
    sinks = [LOCAL_FILE, PROCESS] + ([DISPLAY] if args.reveal else [])
    agreed = NegotiatedSensitiveReferences("1", frozenset({"oauth-resolver-1"}), frozenset(sinks))
    browser = ScriptedBrowser(ACCOUNT, PASSWORD) if args.headless else webbrowser.open
    destination = Path(__file__).parent / "output" / "concept07.csv"
    config = mcp_host.ResolveConfig(
        destination=str(destination), open_browser=browser, allow_local=True, timeout=10,
        command="printf 'command saw: %s\\n' {ref}", approve=lambda program, command: True,
        reveal=args.reveal, click=mcp_host._tty_click if args.reveal else None,
        screen=mcp_host._tty_screen if args.reveal else None)
    profiles = tuple(p for p in sinks if p != PROCESS or process_sink.supported())
    opened: list = []

    def factory():
        if not opened:
            opened.append(mcp_host.open_resolve_session(issuer=issuer.resource, config=config, profiles=profiles,
                                                        agent_token=None, mcp_url=issuer.resource))
        return opened[0]

    try:
        print(f"Issuer: {issuer.resource}")
        print("Model-visible references:", " ".join(refs))
        file_report = mcp_host.materialize(issuer=issuer.resource, references=refs, provenance=store, agreed=agreed,
                                           config=config, sentinels=[], agent_token=None, session=factory())
        print(f"local-file-1: materialized={file_report.materialized} file={destination} "
              f"failure={file_report.failure}")
        transcript: list[str] = []
        process = mcp_host.run_command(references=refs, provenance=store, agreed=agreed, config=config,
                                       sentinels=[], session_factory=factory, transcript=transcript)
        print(f"process-1: program={process.program} exit={process.exit_status} failure={process.failure}")
        for text in transcript:
            print("  model-visible output:", text.strip().replace("\n", " | "))
        if args.reveal:
            display = mcp_host.reveal_references(references=refs, provenance=store, agreed=agreed, config=config,
                                                 sentinels=[], session_factory=factory, transcript=transcript)
            print(f"display-1: revealed={display.revealed} failure={display.failure}")
        if opened and opened[0].credential.account_hint:
            print(f"The resolver token belongs to {opened[0].credential.account_hint}.")
        print("Audit events:", [(e["sink_profile"], e["destination"], e["values"]) for e in issuer.audit.events])
    finally:
        http.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
