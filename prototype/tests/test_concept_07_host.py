"""The host side of Concept 0.7: discovery with ``sinks``, the scope choice, ``process-1`` and ``display-1``.

The unit tests use a stub resolver. The end-to-end tests run the host functions of
``demo/mcp_host.py`` against the prototype issuer on a loopback HTTP server
(``IssuerHttp``), with the scripted browser of ``demo/scripted_browser.py``.
The mutation probe (``tests/tools/mutation_probe.py``, round 10) disables each guard once.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "demo"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import mcp_host  # noqa: E402
from scripted_browser import ScriptedBrowser  # noqa: E402
from sensitive_references import ProvenanceStore  # noqa: E402
from sensitive_references import process_sink  # noqa: E402
from sensitive_references.capabilities import NegotiatedSensitiveReferences  # noqa: E402
from sensitive_references.display_sink import DisplayRefused, DisplaySink, UserAction  # noqa: E402
from sensitive_references.issuer_server import IssuerHttp  # noqa: E402
from sensitive_references.output_guard import SessionMask  # noqa: E402
from sensitive_references.process_sink import EXIT_RESOLVE_FAILED, ProcessSink, program_name  # noqa: E402
from sensitive_references.reference import make_token  # noqa: E402
from sensitive_references.resolver import ResolutionError  # noqa: E402
from sensitive_references.resolver_client import (  # noqa: E402
    OAuthHttpResolver,
    ResolveEndpoint,
    ResolverClientError,
    _discovery_object,
)
from sensitive_references.sink_profiles import (  # noqa: E402
    DISPLAY,
    DISPLAY_SCOPE,
    LOCAL_FILE,
    PROCESS,
    PROCESS_SCOPE,
    RESOLVE_SCOPE,
)

ISSUER = "https://issuer.example/mcp"
VALUE = "s3cret-value-41"
OTHER = "another-value-42"


def discovery(**members):
    obj = {"resolve_endpoint": "https://issuer.example/r", "resolve_scope": RESOLVE_SCOPE,
           "resolver_profiles": ["oauth-resolver-1"], "sink_profiles": [DISPLAY, LOCAL_FILE, PROCESS],
           "process_scope": PROCESS_SCOPE, "display_scope": DISPLAY_SCOPE,
           "sinks": {LOCAL_FILE: {"sink_type": "local_file", "scopes": [RESOLVE_SCOPE]},
                     PROCESS: {"sink_type": "process", "scopes": [RESOLVE_SCOPE, PROCESS_SCOPE]},
                     DISPLAY: {"sink_type": "display", "scopes": [RESOLVE_SCOPE, DISPLAY_SCOPE]}}}
    obj.update(members)
    return {"sensitive_references": {k: v for k, v in obj.items() if v is not None}}


class StubResolver:
    """Records each call. ``fail`` raises like a refused resolve."""

    def __init__(self, values, fail=False):
        self.values = values
        self.fail = fail
        self.calls = []

    def resolve(self, issuer, references, context):
        self.calls.append((issuer, list(references), context))
        if self.fail:
            raise ResolverClientError("unresolvable", "refused")
        return {r: self.values[r] for r in references}


# ---------------------------------------------------------------- discovery and scopes


class DiscoveryTests(unittest.TestCase):
    """RESOLVER-PROFILE.md, section 4: the host refuses an object without valid ``sinks``."""

    def refused(self, document):
        with self.assertRaises(ResolverClientError) as caught:
            _discovery_object(document)
        self.assertEqual(caught.exception.code, "malformed_discovery")

    def test_a_complete_object_is_accepted(self):
        self.assertIsNotNone(_discovery_object(discovery()))

    def test_an_object_without_sinks_or_with_a_bad_member_is_refused(self):
        file_only = {"sink_profiles": [LOCAL_FILE], "process_scope": None, "display_scope": None}
        for sinks in (None, []):
            with self.subTest(sinks=sinks):
                self.refused(discovery(sinks=sinks))
                self.refused(discovery(sinks=sinks, **file_only))
        bad_entries = [{"sink_type": "local_file"}, {"sink_type": "", "scopes": [RESOLVE_SCOPE]},
                       {"sink_type": "local_file", "scopes": []},
                       {"sink_type": "local_file", "scopes": ["other.scope"]},
                       {"sink_type": "local_file", "scopes": RESOLVE_SCOPE}, "local_file"]
        for entry in bad_entries:
            with self.subTest(entry=entry):
                sinks = dict(discovery()["sensitive_references"]["sinks"])
                sinks[LOCAL_FILE] = entry
                self.refused(discovery(sinks=sinks))

    def test_a_sink_scope_member_must_be_the_scope_that_sinks_names(self):
        for members in ({"process_scope": "x.process"}, {"display_scope": PROCESS_SCOPE},
                        {"process_scope": RESOLVE_SCOPE}, {"process_scope": None}, {"display_scope": None},
                        {"display_scope": ""}):
            with self.subTest(members=members):
                self.refused(discovery(**members))

    def test_max_references_must_be_an_integer_of_100_or_more(self):
        for value in (99, "200", 150.0, True):
            with self.subTest(value=value):
                self.refused(discovery(max_references=value))
        self.assertEqual(_discovery_object(discovery(max_references=250))["max_references"], 250)

    def test_the_host_takes_the_scope_set_from_sinks(self):
        from sensitive_references.resolver_client import ProtectedResource
        obj = discovery()["sensitive_references"]
        meta = ProtectedResource(resource=ISSUER, authorization_servers=(), discovery=True,
                                 resolve_scope=RESOLVE_SCOPE,
                                 sinks={k: (v["sink_type"], tuple(v["scopes"])) for k, v in obj["sinks"].items()})
        self.assertEqual(meta.scopes_for([LOCAL_FILE]), RESOLVE_SCOPE)
        self.assertEqual(meta.scopes_for([LOCAL_FILE, PROCESS]), f"{RESOLVE_SCOPE} {PROCESS_SCOPE}")
        self.assertEqual(meta.scopes_for([DISPLAY, PROCESS, LOCAL_FILE]),
                         f"{RESOLVE_SCOPE} {DISPLAY_SCOPE} {PROCESS_SCOPE}")
        self.assertEqual(meta.scopes_for([PROCESS], "custom.resolve"), f"custom.resolve {PROCESS_SCOPE}")


class FakeCredential:
    def __init__(self, granted):
        self.granted = frozenset(granted)
        self.policy = None

    def access_token(self):
        return "rt"

    def granted_scopes(self):
        return self.granted


class ResolverSinkScopeTests(unittest.TestCase):
    """RESOLVER-PROFILE.md, section 5.3, and DISPLAY-PROFILE.md, section 3, on the host side."""

    def resolver(self, granted, sink_scopes):
        return OAuthHttpResolver({ISSUER: ResolveEndpoint("https://issuer.example/r", FakeCredential(granted))},
                                 sink_scopes=sink_scopes)

    def test_a_token_without_the_sink_scope_is_not_sent(self):
        from sensitive_references.resolver import SinkContext
        resolver = self.resolver({RESOLVE_SCOPE}, {"process": frozenset({RESOLVE_SCOPE, PROCESS_SCOPE})})
        with self.assertRaises(ResolverClientError) as caught:
            resolver.resolve(ISSUER, [make_token("email").token], SinkContext("process", "psql", "p"))
        self.assertEqual((caught.exception.code, resolver.requests), ("insufficient_scope", 0))

    def test_a_sink_that_the_run_did_not_negotiate_is_not_sent(self):
        from sensitive_references.resolver import SinkContext
        resolver = self.resolver({RESOLVE_SCOPE, DISPLAY_SCOPE}, {"local_file": frozenset({RESOLVE_SCOPE})})
        with self.assertRaises(ResolverClientError) as caught:
            resolver.resolve(ISSUER, [make_token("email").token], SinkContext("display", "screen", "p"))
        self.assertEqual((caught.exception.code, resolver.requests), ("ineligible_sink", 0))

    def test_a_display_request_holds_one_reference_for_the_screen(self):
        from sensitive_references.resolver import SinkContext
        scopes = {"display": frozenset({RESOLVE_SCOPE, DISPLAY_SCOPE})}
        resolver = self.resolver({RESOLVE_SCOPE, DISPLAY_SCOPE}, scopes)
        a, b = make_token("email").token, make_token("email").token
        for refs, destination in (([a, b], "screen"), ([a], "terminal")):
            with self.subTest(refs=len(refs), destination=destination):
                with self.assertRaises(ResolverClientError) as caught:
                    resolver.resolve(ISSUER, refs, SinkContext("display", destination, "p"))
                self.assertEqual(caught.exception.code, "invalid_request")
        self.assertEqual(resolver.requests, 0)


class HostSettingsTests(unittest.TestCase):
    def test_the_host_declares_the_sinks_of_the_run_and_process_only_where_it_masks_output(self):
        config = mcp_host.ResolveConfig(destination="out.txt", command="psql {ref}", reveal=True)
        with mock.patch.object(process_sink, "supported", return_value=True):
            self.assertEqual(mcp_host.resolving_host_settings(config)["sink_profiles"], [DISPLAY, LOCAL_FILE, PROCESS])
        with mock.patch.object(process_sink, "supported", return_value=False):
            self.assertEqual(mcp_host.resolving_host_settings(config)["sink_profiles"], [DISPLAY, LOCAL_FILE])
        file_only = mcp_host.ResolveConfig(destination="out.txt")
        self.assertEqual(mcp_host.resolving_host_settings(file_only)["sink_profiles"], [LOCAL_FILE])

    def test_the_sink_options_map_to_the_configuration(self):
        args = mcp_host.parse_args(["--url", "https://s.example/mcp", "--extension-id", "x/y", "--tool", "t",
                                    "--run-command", "psql {ref}", "--yes", "--reveal", "--process-timeout", "5"])
        with mock.patch.object(mcp_host, "_has_tty", return_value=False):
            config = mcp_host.resolve_config(args)
        self.assertEqual((config.command, config.reveal, config.process_timeout, config.destination),
                         ("psql {ref}", True, 5.0, None))
        self.assertTrue(config.approve("psql", "psql x"))
        # Without a terminal there is no explicit action of the person: no click, no screen.
        self.assertIsNone(config.click)
        self.assertIsNone(config.screen)
        self.assertEqual(config.profiles(), (PROCESS, DISPLAY))
        no_yes = mcp_host.parse_args(["--url", "https://s.example/mcp", "--extension-id", "x/y", "--tool", "t",
                                      "--run-command", "psql {ref}"])
        with mock.patch.object(mcp_host, "_has_tty", return_value=False):
            self.assertFalse(mcp_host.resolve_config(no_yes).approve("psql", "psql x"))


# ---------------------------------------------------------------- process-1


@unittest.skipUnless(process_sink.supported(), "process-1 needs POSIX named pipes")
class ProcessSinkTests(unittest.TestCase):
    """PROCESS-PROFILE.md, sections 2 to 5."""

    def setUp(self):
        self.ref = make_token("password").token
        self.other = make_token("password").token
        self.store = ProvenanceStore()
        self.store.observe_mcp_result(ISSUER, extension_negotiated=True, result=[self.ref, self.other])
        self.resolver = StubResolver({self.ref: VALUE, self.other: OTHER})
        self.mask = SessionMask()
        self.dir = Path(tempfile.mkdtemp(prefix="sref-process-test-"))

    def sink(self, resolver=None, timeout=10.0):
        return ProcessSink(self.store, resolver or self.resolver, mask=self.mask, timeout=timeout)

    def test_the_program_name_is_the_first_word_after_assignments_and_its_last_path_part(self):
        cases = {"psql -h db": "psql", "PGPASSWORD=x /usr/bin/psql -c 'select 1'": "psql",
                 "A=1 B=2": "sh", "./tool --x": "tool", "'/opt/my tool/run' a": "run", "": "sh"}
        for command, program in cases.items():
            with self.subTest(command=command):
                self.assertEqual(program_name(command), program)

    def test_the_destination_is_the_program_name_and_never_the_command_line(self):
        result = self.sink().run(f"MODE=1 /usr/bin/printf '%s' {self.ref} >/dev/null")
        self.assertIsNone(result.failure)
        (_, refs, context), = self.resolver.calls
        self.assertEqual((context.sink_type, context.destination), ("process", "printf"))
        self.assertNotIn(self.ref, context.destination)

    def test_the_value_reaches_the_command_through_a_pipe_and_not_the_command_line_of_the_shell(self):
        seen = []
        real = subprocess.Popen

        def spy(args, **kwargs):
            seen.append(list(args))
            return real(args, **kwargs)

        target = self.dir / "out"
        with mock.patch.object(process_sink.subprocess, "Popen", spy):
            result = self.sink().run(f"printf '%s' {self.ref} > {target}")
        self.assertEqual(target.read_text(), VALUE)
        self.assertEqual(result.exit_status, 0)
        self.assertNotIn(VALUE, json.dumps(seen))
        self.assertNotIn(self.ref, json.dumps(seen))

    def test_a_refused_command_costs_no_resolve(self):
        result = self.sink().run(f"printf '%s' {self.ref}", approve=lambda program, command: False)
        self.assertTrue(result.refused)
        self.assertEqual((self.resolver.calls, result.exit_status), ([], None))

    def test_a_command_that_never_reads_the_value_costs_no_resolve(self):
        result = self.sink().run(f"exit 3; printf '%s' {self.ref}")
        self.assertEqual((self.resolver.calls, result.exit_status, result.resolved), ([], 3, False))

    def test_the_approval_sees_the_program_and_the_command_with_references_only(self):
        asked = []
        self.sink().run(f"printf '%s' {self.ref} >/dev/null", approve=lambda p, c: asked.append((p, c)) or True)
        self.assertEqual(asked, [("printf", f"printf '%s' {self.ref} >/dev/null")])

    def test_all_references_of_a_command_resolve_in_one_step_before_any_value(self):
        result = self.sink().run(f"printf '%s %s' {self.ref} {self.other}")
        self.assertEqual(len(self.resolver.calls), 1)
        self.assertEqual(sorted(self.resolver.calls[0][1]), sorted([self.ref, self.other]))
        self.assertEqual(result.model_output, f"{self.ref} {self.other}")

    def test_a_failed_resolve_stops_the_command_and_gives_it_no_value(self):
        target = self.dir / "out"
        result = self.sink(StubResolver({}, fail=True)).run(f"printf '%s' {self.ref} > {target}; echo after")
        self.assertEqual(result.exit_status, EXIT_RESOLVE_FAILED)
        self.assertEqual(result.failure, "resolution failed: unresolvable")
        self.assertFalse(target.exists() and target.read_text())
        self.assertNotIn("after", result.model_output)

    def test_the_output_is_masked_before_the_model_sees_it(self):
        result = self.sink().run(f"echo {self.ref}; printf '%s' {self.ref} | base64; echo {self.ref} >&2")
        self.assertNotIn(VALUE, result.model_output)
        self.assertEqual(result.model_output.count(self.ref), 3)

    def test_the_output_is_masked_on_the_failure_paths(self):
        cases = [(f"echo {self.ref}; exit 4", 4, False), (f"echo {self.ref}; kill -9 $$", -9, False),
                 (f"echo {self.ref}; sleep 5", None, True)]
        for command, status, timed_out in cases:
            with self.subTest(command=command.split(";")[1]):
                result = self.sink(timeout=1.0).run(command)
                self.assertNotIn(VALUE, result.model_output)
                self.assertIn(self.ref, result.model_output)
                self.assertEqual(result.timed_out, timed_out)
                if status is not None:
                    self.assertEqual(result.exit_status, status)

    def test_an_unobserved_reference_stays_text_and_is_not_sent(self):
        forged = make_token("password").token
        result = self.sink().run(f"printf '%s|%s' {self.ref} {forged}")
        self.assertEqual(self.resolver.calls[0][1], [self.ref])
        self.assertEqual((result.references, result.references_withheld), (1, 1))
        self.assertEqual(result.model_output, f"{self.ref}|{forged}")

    def test_a_released_value_is_masked_in_later_tool_output(self):
        self.sink().run(f"printf '%s' {self.ref} >/dev/null")
        self.assertEqual(self.mask.mask(f"later: {VALUE}"), f"later: {self.ref}")

    def test_without_named_pipes_the_host_runs_nothing(self):
        with mock.patch.object(process_sink, "supported", return_value=False):
            result = self.sink().run(f"printf '%s' {self.ref}")
        self.assertEqual((result.failure, self.resolver.calls), ("this platform cannot mask command output", []))


# ---------------------------------------------------------------- display-1


class DisplaySinkTests(unittest.TestCase):
    """DISPLAY-PROFILE.md, sections 2 to 5."""

    def setUp(self):
        self.ref = make_token("email").token
        self.store = ProvenanceStore()
        self.store.observe_mcp_result(ISSUER, extension_negotiated=True, result=[self.ref])
        self.resolver = StubResolver({self.ref: VALUE})
        self.mask = SessionMask()
        self.screen = []
        self.clipboard = []

    def sink(self, limit=20):
        return DisplaySink(self.store, self.resolver, mask=self.mask, screen=lambda r, v: self.screen.append((r, v)),
                           clipboard=self.clipboard.append, limit=limit)

    def refused(self, call, code):
        with self.assertRaises(DisplayRefused) as caught:
            call()
        self.assertEqual(caught.exception.code, code)

    def test_a_reveal_needs_an_explicit_action_of_the_person(self):
        sink = self.sink()
        for action in (self.ref, {"reference": self.ref}, UserAction(self.ref, "copy")):
            with self.subTest(action=type(action).__name__):
                self.refused(lambda: sink.reveal(action), "no_user_action")
        self.assertEqual((self.resolver.calls, self.screen), ([], []))

    def test_one_action_resolves_one_reference_once(self):
        sink = self.sink()
        action = UserAction(self.ref)
        self.assertIsNone(sink.reveal(action))
        self.refused(lambda: sink.reveal(action), "action_used")
        self.assertEqual(len(self.resolver.calls), 1)

    def test_the_wire_values_are_display_screen_and_one_reference(self):
        self.sink().reveal(UserAction(self.ref))
        (_, refs, context), = self.resolver.calls
        self.assertEqual((refs, context.sink_type, context.destination), ([self.ref], "display", "screen"))

    def test_the_value_goes_to_the_screen_only(self):
        sink = self.sink()
        returned = sink.reveal(UserAction(self.ref))
        self.assertIsNone(returned)
        self.assertEqual(self.screen, [(self.ref, VALUE)])
        self.assertEqual(self.mask.mask(f"pasted {VALUE}"), f"pasted {self.ref}")

    def test_a_second_action_on_a_held_value_sends_no_request(self):
        sink = self.sink()
        sink.reveal(UserAction(self.ref))
        sink.reveal(UserAction(self.ref))
        self.assertEqual((len(self.resolver.calls), len(self.screen)), (1, 2))

    def test_a_copy_needs_a_second_action_after_the_reveal(self):
        sink = self.sink()
        self.refused(lambda: sink.copy(UserAction(self.ref, "copy")), "not_shown")
        self.mask.release({self.ref: VALUE})          # held for another sink, but not shown on the screen
        self.refused(lambda: sink.copy(UserAction(self.ref, "copy")), "not_shown")
        self.refused(lambda: sink.copy(UserAction(self.ref)), "no_user_action")
        sink.reveal(UserAction(self.ref))
        sink.copy(UserAction(self.ref, "copy"))
        self.assertEqual(self.clipboard, [VALUE])

    def test_an_untrusted_or_malformed_reference_is_not_resolved(self):
        sink = self.sink()
        for reference in (make_token("email").token, "⟦sref:email:short⟧", "plain text"):
            with self.subTest(reference=reference[:12]):
                self.refused(lambda: sink.reveal(UserAction(reference)), "untrusted_reference")
        self.assertEqual(self.resolver.calls, [])

    def test_the_session_limit(self):
        refs = [make_token("email").token for _ in range(3)]
        self.store.observe_mcp_result(ISSUER, extension_negotiated=True, result=refs)
        self.resolver.values.update({r: f"v{i}" for i, r in enumerate(refs)})
        sink = self.sink(limit=2)
        sink.reveal(UserAction(refs[0]))
        sink.reveal(UserAction(refs[1]))
        self.refused(lambda: sink.reveal(UserAction(refs[2])), "session_limit")
        self.assertEqual(len(self.resolver.calls), 2)

    def test_a_refused_resolve_shows_nothing(self):
        self.resolver.fail = True
        self.refused(lambda: self.sink().reveal(UserAction(self.ref)), "unresolvable")
        self.assertEqual(self.screen, [])


# ---------------------------------------------------------------- end to end against the prototype issuer


AGREED_ALL = NegotiatedSensitiveReferences("1", frozenset({"oauth-resolver-1"}),
                                           frozenset({LOCAL_FILE, PROCESS, DISPLAY}))


class EndToEndTests(unittest.TestCase):
    """The host functions of ``mcp_host`` against ``IssuerHttp`` with real HTTP, PKCE and a consent page."""

    def setUp(self):
        self.http = IssuerHttp()
        self.addCleanup(self.http.close)
        self.issuer = self.http.issuer
        self.issuer.add_account("alice@example.com", "pw-a")
        self.issuer.add_account("bob@example.com", "pw-b")
        self.refs = [self.issuer.issue("alice@example.com", "email", v) for v in (VALUE, OTHER)]
        self.store = ProvenanceStore()
        self.store.observe_mcp_result(self.issuer.resource, extension_negotiated=True, result=self.refs)
        self.dir = Path(tempfile.mkdtemp(prefix="sref-07-e2e-"))
        self.screen = []

    def config(self, browser, **overrides):
        values = dict(destination=None, token_cache=None, open_browser=browser, authorization_timeout=10,
                      timeout=5, allow_local=True, click=lambda index, total: True,
                      screen=lambda r, v: self.screen.append((r, v)))
        values.update(overrides)
        return mcp_host.ResolveConfig(**values)

    def session_factory(self, config, profiles):
        opened = []

        def factory():
            if not opened:
                opened.append(mcp_host.open_resolve_session(issuer=self.issuer.resource, config=config,
                                                            profiles=profiles, agent_token="agent-token",
                                                            mcp_url=self.issuer.resource))
            return opened[0]
        return factory, opened

    def test_one_authorization_serves_a_file_a_command_and_the_screen(self):
        browser = ScriptedBrowser("alice@example.com", "pw-a")
        dest = self.dir / "out.txt"
        config = self.config(browser, destination=str(dest), command="printf '%s\\n' {ref}", reveal=True)
        factory, opened = self.session_factory(config, (LOCAL_FILE, PROCESS, DISPLAY))
        transcript = []
        file_report = mcp_host.materialize(issuer=self.issuer.resource, references=self.refs, provenance=self.store,
                                           agreed=AGREED_ALL, config=config, sentinels=[VALUE, OTHER],
                                           agent_token="agent-token", session=factory())
        self.assertTrue(file_report.materialized, file_report.failure)
        self.assertEqual(dest.read_text(), f"{VALUE}\n{OTHER}\n")
        reports = []
        if process_sink.supported():
            reports.append(mcp_host.run_command(references=self.refs, provenance=self.store, agreed=AGREED_ALL,
                                                config=config, sentinels=[VALUE, OTHER], session_factory=factory,
                                                transcript=transcript))
            self.assertIsNone(reports[0].failure)
            self.assertEqual((reports[0].program, reports[0].exit_status, reports[0].sentinels_in_model_output),
                             ("printf", 0, 0))
            self.assertEqual(transcript, [f"{self.refs[0]}\n{self.refs[1]}\n"])
        display = mcp_host.reveal_references(references=self.refs, provenance=self.store, agreed=AGREED_ALL,
                                             config=config, sentinels=[VALUE, OTHER], session_factory=factory,
                                             transcript=transcript)
        self.assertEqual((display.revealed, display.resolve_requests, display.sentinels_in_transcript, display.failure),
                         (2, 0 if process_sink.supported() else 2, 0, None))
        self.assertEqual(self.screen, list(zip(self.refs, (VALUE, OTHER))))
        # One consent page for the whole run, with one line per sink scope.
        self.assertEqual(len(browser.pages), 1)
        self.assertIn("commands that it runs on this computer", browser.pages[0])
        self.assertIn("on your screen", browser.pages[0])
        self.assertEqual({k[3] for k in self.issuer.approvals},
                         {frozenset({RESOLVE_SCOPE, PROCESS_SCOPE, DISPLAY_SCOPE})})
        self.assertEqual(opened[0].credential.account_hint, "al…@example.com")
        profiles = [e["sink_profile"] for e in self.issuer.audit.events]
        self.assertEqual(profiles[0], LOCAL_FILE)
        if process_sink.supported():
            self.assertEqual(profiles[1], PROCESS)
            self.assertEqual(self.issuer.audit.events[1]["destination"], "printf")
        for report in (file_report, display, *reports):
            text = json.dumps(report.__dict__, default=str)
            for secret in (VALUE, OTHER, *self.refs):
                self.assertNotIn(secret, text)

    def test_a_file_only_run_asks_for_the_resolve_scope_only_and_cannot_reach_a_command(self):
        browser = ScriptedBrowser("alice@example.com", "pw-a")
        config = self.config(browser, destination=str(self.dir / "out.txt"))
        report = mcp_host.materialize(issuer=self.issuer.resource, references=self.refs, provenance=self.store,
                                      agreed=AGREED_ALL, config=config, sentinels=[], agent_token="agent-token")
        self.assertTrue(report.materialized, report.failure)
        self.assertEqual({k[3] for k in self.issuer.approvals}, {frozenset({RESOLVE_SCOPE})})
        self.assertNotIn("commands that it runs", browser.pages[0])

    def test_a_reference_of_another_account_is_unknown_and_nothing_is_written(self):
        browser = ScriptedBrowser("bob@example.com", "pw-b")
        dest = self.dir / "out.txt"
        report = mcp_host.materialize(issuer=self.issuer.resource, references=self.refs, provenance=self.store,
                                      agreed=AGREED_ALL, config=self.config(browser, destination=str(dest)),
                                      sentinels=[], agent_token="agent-token")
        self.assertEqual(report.failure, "resolution failed: unresolvable")
        self.assertFalse(dest.exists())

    def test_use_another_account_on_the_page_signs_in_the_other_account(self):
        browser = ScriptedBrowser("bob@example.com", "pw-b", switch_to=("alice@example.com", "pw-a"))
        dest = self.dir / "out.txt"
        report = mcp_host.materialize(issuer=self.issuer.resource, references=self.refs, provenance=self.store,
                                      agreed=AGREED_ALL, config=self.config(browser, destination=str(dest)),
                                      sentinels=[], agent_token="agent-token")
        self.assertTrue(report.materialized, report.failure)
        self.assertEqual(len(browser.pages), 2)
        self.assertIn("bob@example.com", browser.pages[0])
        self.assertIn("alice@example.com", browser.pages[1])

    def test_each_authorization_shows_the_consent_page_again(self):
        browser = ScriptedBrowser("alice@example.com", "pw-a")
        for _ in range(2):
            report = mcp_host.materialize(issuer=self.issuer.resource, references=self.refs, provenance=self.store,
                                          agreed=AGREED_ALL, sentinels=[], agent_token="agent-token",
                                          config=self.config(browser, destination=str(self.dir / "out.txt")))
            self.assertTrue(report.materialized, report.failure)
        self.assertEqual(len(browser.pages), 2)

    def test_a_server_without_the_process_sink_stops_a_process_run_before_the_authorization(self):
        self.issuer.sinks = (LOCAL_FILE,)
        browser = ScriptedBrowser("alice@example.com", "pw-a")
        config = self.config(browser, command="printf '%s' {ref}")
        factory, _ = self.session_factory(config, (PROCESS,))
        with mock.patch.object(process_sink, "supported", return_value=True):
            report = mcp_host.run_command(references=self.refs, provenance=self.store, agreed=AGREED_ALL,
                                          config=config, sentinels=[], session_factory=factory, transcript=[])
        self.assertEqual(report.failure, "resolution failed: profile_not_offered")
        self.assertEqual(browser.pages, [])

    def test_a_negotiated_sink_without_a_valid_sinks_member_stops_the_host(self):
        original = self.issuer.discovery
        changes = {"no member": lambda sinks: sinks.pop(LOCAL_FILE),
                   "another sink_type": lambda sinks: sinks[LOCAL_FILE].update(sink_type="file")}
        for name, change in changes.items():
            with self.subTest(change=name):
                def changed():
                    obj = original()
                    change(obj["sinks"])
                    return obj

                self.issuer.discovery = changed
                browser = ScriptedBrowser("alice@example.com", "pw-a")
                dest = self.dir / "out.txt"
                report = mcp_host.materialize(issuer=self.issuer.resource, references=self.refs,
                                              provenance=self.store, agreed=AGREED_ALL, sentinels=[],
                                              agent_token="agent-token",
                                              config=self.config(browser, destination=str(dest)))
                self.assertEqual(report.failure, "resolution failed: malformed_discovery")
                self.assertEqual(browser.pages, [])
                self.assertFalse(dest.exists())

    def test_the_audit_store_down_releases_no_value(self):
        self.issuer.audit.fail = True
        browser = ScriptedBrowser("alice@example.com", "pw-a")
        dest = self.dir / "out.txt"
        report = mcp_host.materialize(issuer=self.issuer.resource, references=self.refs, provenance=self.store,
                                      agreed=AGREED_ALL, config=self.config(browser, destination=str(dest)),
                                      sentinels=[], agent_token="agent-token")
        self.assertEqual(report.failure, "resolution failed: audit_unavailable")
        self.assertFalse(dest.exists())


if __name__ == "__main__":
    unittest.main()


try:
    import mcp.server.extension  # noqa: F401
    import uvicorn  # noqa: F401
    HAVE_SDK2 = True
except ImportError:
    HAVE_SDK2 = False


@unittest.skipUnless(HAVE_SDK2 and process_sink.supported(), "needs the MCP SDK 2.x, uvicorn and POSIX pipes")
class McpHostRunTests(unittest.TestCase):
    """``mcp_host.main`` against a real MCP SDK 2.x server in front of the prototype issuer: all three sinks."""

    SETTINGS = {"versions": ["1"], "resolver_profiles": ["oauth-resolver-1"],
                "sink_profiles": [DISPLAY, LOCAL_FILE, PROCESS]}

    def test_the_host_fills_a_file_runs_a_command_and_reveals_on_a_click_with_one_consent(self):
        from test_mcp_host_resolve import _serve_mcp
        from sensitive_references.issuer_server import IssuerServer, Record
        http = IssuerHttp()
        self.addCleanup(http.close)
        refs = [make_token("email").token, make_token("email").token]
        runner, url = _serve_mcp(f"mail {refs[0]} and {refs[1]}", self.SETTINGS, http.base)
        self.addCleanup(setattr, runner, "should_exit", True)
        # The issuer answers on the origin of the MCP URL; the MCP server forwards every other path to it.
        server = IssuerServer(url.rsplit("/", 1)[0])
        server.add_account("alice@example.com", "pw-a")
        server.records["alice@example.com"] = {refs[0]: Record(VALUE), refs[1]: Record(OTHER)}
        http.issuer = server
        dest = Path(tempfile.mkdtemp(prefix="sref-07-run-")) / "out.txt"
        browser = ScriptedBrowser("alice@example.com", "pw-a")
        screen = []
        printed = []
        import builtins
        saved = (mcp_host.open_browser, mcp_host._has_tty, mcp_host._tty_click, mcp_host._tty_screen,
                 os.environ.get("SREF_SENTINELS"), builtins.print)
        mcp_host.open_browser = browser
        mcp_host._has_tty = lambda: True
        mcp_host._tty_click = lambda index, total: True
        mcp_host._tty_screen = lambda reference, value: screen.append((reference, value))
        os.environ["SREF_SENTINELS"] = f"{VALUE},{OTHER}"
        builtins.print = lambda *a, **k: printed.append(" ".join(map(str, a))) if "file" not in k else None
        try:
            code = mcp_host.main([
                "--url", url, "--extension-id", "org.example/sensitive-references", "--tool", "read",
                "--expect-negotiation", "--resolve-into", str(dest), "--run-command", "printf '%s\\n' {ref}",
                "--yes", "--reveal", "--timeout", "10", "--allow-local-targets"])
        finally:
            (mcp_host.open_browser, mcp_host._has_tty, mcp_host._tty_click, mcp_host._tty_screen) = saved[:4]
            builtins.print = saved[5]
            if saved[4] is None:
                os.environ.pop("SREF_SENTINELS", None)
            else:
                os.environ["SREF_SENTINELS"] = saved[4]
        report = json.loads("\n".join(printed))
        self.assertEqual(code, 0, report["failures"])
        self.assertEqual(dest.read_text(), f"{VALUE}\n{OTHER}\n")
        self.assertEqual((report["process"]["program"], report["process"]["exit_status"],
                          report["process"]["sentinels_in_model_output"]), ("printf", 0, 0))
        self.assertEqual((report["display"]["revealed"], report["display"]["sentinels_in_transcript"]), (2, 0))
        self.assertEqual(screen, list(zip(refs, (VALUE, OTHER))))
        self.assertEqual(len(browser.pages), 1)
        self.assertEqual({k[3] for k in server.approvals},
                         {frozenset({RESOLVE_SCOPE, PROCESS_SCOPE, DISPLAY_SCOPE})})
        text = json.dumps(report)
        for secret in (VALUE, OTHER, *refs):
            self.assertNotIn(secret, text)
