"""The prototype issuer of Concept 0.7: authorization server and resolve endpoint (``IssuerServer``).

Offline and without HTTP: the tests call the methods that the HTTP adapter calls.
Each test names the rule of RESOLVER-PROFILE.md, PROCESS-PROFILE.md or
DISPLAY-PROFILE.md that it checks. The mutation probe (``tests/tools/mutation_probe.py``,
round 10) disables each guard once; the guard and its tests are listed there.
"""

from __future__ import annotations

from base64 import urlsafe_b64encode
from hashlib import sha256
import json
from pathlib import Path
import sys
import unittest
from urllib.parse import parse_qs, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from sensitive_references.issuer_server import IssuerServer, account_hint, audit_destination  # noqa: E402
from sensitive_references.sink_profiles import (  # noqa: E402
    DISPLAY,
    DISPLAY_SCOPE,
    LOCAL_FILE,
    PROCESS,
    PROCESS_SCOPE,
    RESOLVE_SCOPE,
)

BASE = "https://issuer.example"
FILE = RESOLVE_SCOPE
ALL = f"{RESOLVE_SCOPE} {PROCESS_SCOPE} {DISPLAY_SCOPE}"
ALICE_VALUE = "alice.value@example.org"


def challenge(verifier: str) -> str:
    return urlsafe_b64encode(sha256(verifier.encode()).digest()).rstrip(b"=").decode()


def query(response) -> dict[str, str]:
    return {k: v[0] for k, v in parse_qs(urlsplit(response.headers["Location"]).query).items()}


class Clock:
    def __init__(self) -> None:
        self.now = 1_800_000_000.0

    def __call__(self) -> float:
        return self.now


class IssuerTestCase(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self.server = IssuerServer(BASE, clock=self.clock)
        for account in ("alice@example.com", "bob@example.com", "root@example.com"):
            self.server.add_account(account, "pw", admin=account.startswith("root"))
        self.client = self.register()
        self.alice_ref = self.server.issue("alice@example.com", "email", ALICE_VALUE)
        self.bob_ref = self.server.issue("bob@example.com", "email", "bob.value@example.org")

    def register(self, port=5000, name="Test host"):
        response = self.server.register({"client_name": name,
                                         "redirect_uris": [f"http://127.0.0.1:{port}/callback"]})
        self.assertEqual(response.status, 201)
        return response.body["client_id"]

    def params(self, scope, client=None, port=5000, verifier="v" * 43):
        return {"response_type": "code", "client_id": client or self.client, "state": "s1",
                "redirect_uri": f"http://127.0.0.1:{port}/callback", "scope": scope,
                "resource": self.server.resource, "code_challenge": challenge(verifier),
                "code_challenge_method": "S256"}

    def sign_in(self, response, account):
        request = query(response)["request"]
        answer, session = self.server.login({"request": request, "account": account, "password": "pw"},
                                            self.server.origin)
        self.assertIsNotNone(session)
        return self.server.resume(request, session), session

    def page(self, scope, account="alice@example.com", session=None, **params):
        response = self.server.authorize(self.params(scope, **params), session)
        if response.status == 302 and "/login" in response.headers["Location"]:
            response, session = self.sign_in(response, account)
        return response, session

    def approve(self, page, session):
        response = self.server.consent(session, {"nonce": page.page["nonce"], "decision": "approve"},
                                       self.server.origin)
        self.assertEqual(response.status, 302)
        self.assertNotIn(page.page["nonce"], self.server.nonces)              # single use
        return query(response)["code"]

    def grant(self, scope, account="alice@example.com", client=None, port=5000):
        page, session = self.page(scope, account, client=client, port=port)
        self.assertEqual(page.status, 200)
        code = self.approve(page, session)
        response = self.server.token({"grant_type": "authorization_code", "code": code, "client_id": client or self.client,
                                      "redirect_uri": f"http://127.0.0.1:{port}/callback", "code_verifier": "v" * 43,
                                      "resource": self.server.resource})
        self.assertEqual(response.status, 200, response.body)
        return response.body

    def resolve(self, token, refs, sink_type="local_file", destination="out.csv"):
        return self.server.resolve(f"Bearer {token}", json.dumps(
            {"references": refs, "sink_type": sink_type, "destination": destination}).encode())


class DiscoveryTests(IssuerTestCase):
    def test_discovery_names_each_sink_with_its_scope_set_and_the_two_sink_scopes(self):
        obj = self.server.protected_resource_metadata()["sensitive_references"]
        self.assertEqual(obj["sink_profiles"], [DISPLAY, LOCAL_FILE, PROCESS])
        self.assertEqual(obj["sinks"], {
            DISPLAY: {"sink_type": "display", "scopes": [RESOLVE_SCOPE, DISPLAY_SCOPE]},
            LOCAL_FILE: {"sink_type": "local_file", "scopes": [RESOLVE_SCOPE]},
            PROCESS: {"sink_type": "process", "scopes": [RESOLVE_SCOPE, PROCESS_SCOPE]}})
        self.assertEqual((obj["process_scope"], obj["display_scope"]), (PROCESS_SCOPE, DISPLAY_SCOPE))
        self.assertNotIn("mcpgate-process-1", json.dumps(obj))

    def test_the_resolve_and_sink_scopes_are_not_in_scopes_supported(self):
        metadata = self.server.protected_resource_metadata()
        self.assertFalse({RESOLVE_SCOPE, PROCESS_SCOPE, DISPLAY_SCOPE} & set(metadata["scopes_supported"]))
        self.assertNotIn("scopes_supported", self.server.authorization_server_metadata())

    def test_a_server_without_a_sink_names_no_scope_for_it(self):
        server = IssuerServer(BASE, sinks=(LOCAL_FILE,))
        obj = server.discovery()
        self.assertEqual(list(obj["sinks"]), [LOCAL_FILE])
        self.assertNotIn("process_scope", obj)
        self.assertNotIn("display_scope", obj)


class ScopeTests(IssuerTestCase):
    """RESOLVER-PROFILE.md, section 5.2."""

    def assert_invalid_scope(self, scope, server=None):
        server = server or self.server
        response = server.authorize(self.params(scope), None)
        self.assertEqual(response.status, 302)
        self.assertEqual(query(response).get("error"), "invalid_scope", scope)
        self.assertEqual(server.pending, {})

    def test_a_sink_scope_without_the_resolve_scope_is_invalid_scope(self):
        for scope in (PROCESS_SCOPE, DISPLAY_SCOPE, f"{PROCESS_SCOPE} {DISPLAY_SCOPE}", ""):
            with self.subTest(scope=scope):
                self.assert_invalid_scope(scope)

    def test_the_resolve_scope_with_an_agent_scope_is_invalid_scope(self):
        for scope in (f"{RESOLVE_SCOPE} mcp", f"{RESOLVE_SCOPE} {PROCESS_SCOPE} mcp", f"{PROCESS_SCOPE} mcp"):
            with self.subTest(scope=scope):
                self.assert_invalid_scope(scope)

    def test_a_sink_scope_that_the_server_does_not_offer_is_invalid_scope(self):
        server = IssuerServer(BASE, sinks=(LOCAL_FILE, DISPLAY))
        server.clients = self.server.clients
        self.assert_invalid_scope(f"{RESOLVE_SCOPE} {PROCESS_SCOPE}", server)

    def test_the_resolve_scope_with_sink_scopes_and_openid_gets_the_consent_page(self):
        for scope in (FILE, ALL, f"openid {RESOLVE_SCOPE} {DISPLAY_SCOPE}"):
            with self.subTest(scope=scope):
                page, _ = self.page(scope)
                self.assertEqual(page.status, 200)

    def test_the_token_carries_exactly_the_granted_set(self):
        self.assertEqual(self.grant(f"{RESOLVE_SCOPE} {PROCESS_SCOPE}")["scope"], f"{RESOLVE_SCOPE} {PROCESS_SCOPE}")
        self.assertEqual(self.grant(FILE)["scope"], RESOLVE_SCOPE)


class InsufficientScopeTests(IssuerTestCase):
    """RESOLVER-PROFILE.md, section 5.4; PROCESS-PROFILE.md and DISPLAY-PROFILE.md, section 6, rule 1."""

    def test_a_file_only_token_gets_insufficient_scope_before_any_lookup_without_a_value_or_an_audit_event(self):
        token = self.grant(FILE)["access_token"]
        cases = ((PROCESS, "process", "psql", f"{RESOLVE_SCOPE} {PROCESS_SCOPE}"),
                 (DISPLAY, "display", "screen", f"{RESOLVE_SCOPE} {DISPLAY_SCOPE}"))
        for profile, sink_type, destination, scope in cases:
            with self.subTest(profile=profile):
                response = self.resolve(token, [self.alice_ref], sink_type, destination)
                self.assertEqual(response.status, 403)
                self.assertEqual(response.body["error"], "insufficient_scope")
                self.assertEqual(response.body["scope"], scope)
                self.assertTrue(response.body["error_description"])
                header = response.headers["WWW-Authenticate"]
                self.assertTrue(header.startswith("Bearer "))
                self.assertIn('error="insufficient_scope"', header)
                self.assertIn(f'scope="{scope}"', header)
                self.assertIn(f'error_description="{response.body["error_description"]}"', header)
                self.assertEqual(response.headers["Cache-Control"], "no-store")
                self.assertNotIn("values", response.body)
                self.assertNotIn(ALICE_VALUE, json.dumps(response.body) + header)
        self.assertEqual(self.server.lookups, 0)
        self.assertEqual(self.server.audit.events, [])

    def test_a_display_token_does_not_resolve_into_a_command_but_into_a_file(self):
        token = self.grant(f"{RESOLVE_SCOPE} {DISPLAY_SCOPE}")["access_token"]
        self.assertEqual(self.resolve(token, [self.alice_ref], "process", "psql").status, 403)
        self.assertEqual(self.resolve(token, [self.alice_ref]).status, 200)

    def test_an_unknown_sink_type_is_ineligible_sink(self):
        token = self.grant(ALL)["access_token"]
        for sink_type in ("Process", "mcpgate-process-1", "process-1", "local-file"):
            with self.subTest(sink_type=sink_type):
                response = self.resolve(token, [self.alice_ref], sink_type)
                self.assertEqual((response.status, response.body["error"]), (403, "ineligible_sink"))


class RefreshTests(IssuerTestCase):
    """RESOLVER-PROFILE.md, sections 5.3 and 11."""

    def refresh(self, token, scope=None, client=None):
        form = {"grant_type": "refresh_token", "refresh_token": token, "client_id": client or self.client}
        if scope is not None:
            form["scope"] = scope
        return self.server.token(form)

    def test_a_refresh_keeps_the_granted_set(self):
        body = self.grant(f"{RESOLVE_SCOPE} {PROCESS_SCOPE}")
        again = self.refresh(body["refresh_token"])
        self.assertEqual(again.body["scope"], body["scope"])
        narrow = self.refresh(again.body["refresh_token"], RESOLVE_SCOPE)
        self.assertEqual(narrow.body["scope"], body["scope"])

    def test_a_refresh_adds_no_scope(self):
        body = self.grant(FILE)
        response = self.refresh(body["refresh_token"], f"{RESOLVE_SCOPE} {PROCESS_SCOPE}")
        self.assertEqual((response.status, response.body["error"]), (400, "invalid_scope"))
        again = self.refresh(body["refresh_token"])
        self.assertEqual(again.body["scope"], RESOLVE_SCOPE)
        self.assertEqual(self.resolve(again.body["access_token"], [self.alice_ref], "process", "psql").status, 403)

    def test_a_refresh_token_rotates_and_is_bound_to_its_client(self):
        body = self.grant(FILE)
        other = self.register(port=5001, name="Other")
        self.assertEqual(self.refresh(body["refresh_token"], client=other).status, 400)
        self.assertEqual(self.refresh(body["refresh_token"]).status, 200)
        self.assertEqual(self.refresh(body["refresh_token"]).status, 400)


class ConsentTests(IssuerTestCase):
    """RESOLVER-PROFILE.md, section 10."""

    def test_every_authorization_request_gets_the_consent_page_also_with_a_live_approval(self):
        page, session = self.page(ALL)
        self.approve(page, session)
        again = self.server.authorize(self.params(ALL), session)
        self.assertEqual(again.status, 200)
        self.assertIsNotNone(again.page)
        self.assertNotIn("Location", again.headers)
        self.assertEqual(self.server.codes.__len__(), 1)

    def test_the_consent_page_names_account_client_loopback_time_resource_and_each_sink_scope(self):
        page, _ = self.page(ALL, port=53124)
        names = page.page
        self.assertEqual(names["account"], "alice@example.com")
        self.assertEqual(names["client"], "Test host")
        self.assertEqual(names["loopback"], "127.0.0.1:53124")
        self.assertEqual(names["requested_at"], "2027-01-15 08:00:00 UTC")
        self.assertEqual(names["resource"], self.server.resource)
        self.assertEqual(len(names["sink_lines"]), 2)
        self.assertIn("commands", names["sink_lines"][1])
        self.assertIn("screen", names["sink_lines"][0])
        for text in ("alice@example.com", "Test host", "127.0.0.1:53124", "2027-01-15 08:00:00 UTC",
                     self.server.resource, "Use another account", *names["sink_lines"]):
            self.assertIn(text, page.body)
        file_only, _ = self.page(FILE)
        self.assertEqual(file_only.page["sink_lines"], [])
        self.assertNotIn("commands", file_only.body)

    def test_the_consent_page_forbids_framing_and_lets_its_form_reach_only_this_loopback_origin(self):
        page, _ = self.page(FILE, port=53124)
        self.assertEqual(page.headers["Content-Security-Policy"],
                         "frame-ancestors 'none'; form-action 'self' http://127.0.0.1:53124")

    def test_use_another_account_ends_the_session_and_returns_to_the_same_request(self):
        page, session = self.page(f"{RESOLVE_SCOPE} {DISPLAY_SCOPE}")
        switched = self.server.switch_account(session, {"nonce": page.page["nonce"]}, self.server.origin)
        self.assertEqual(switched.status, 302)
        self.assertNotIn(page.page["nonce"], self.server.nonces)              # single use
        self.assertIn("/login?request=" + page.page["request"], switched.headers["Location"])
        self.assertNotIn(session, self.server.sessions)
        # The old page grants nothing: its nonce is spent and its session ended.
        old = self.server.consent(session, {"nonce": page.page["nonce"], "decision": "approve"}, self.server.origin)
        self.assertEqual(old.status, 400)
        other, bob = self.sign_in(switched, "bob@example.com")
        self.assertEqual(other.page["account"], "bob@example.com")
        self.assertEqual(other.page["request"], page.page["request"])
        self.assertEqual(other.page["sink_lines"], page.page["sink_lines"])
        self.approve(other, bob)
        self.assertEqual({k[0] for k in self.server.approvals}, {"bob@example.com"})

    def test_a_switch_without_the_nonce_or_from_another_origin_does_nothing(self):
        page, session = self.page(FILE)
        for form, origin in (({}, self.server.origin), ({"nonce": page.page["nonce"]}, "https://evil.example")):
            with self.subTest(origin=origin):
                self.assertEqual(self.server.switch_account(session, form, origin).status, 400)
        self.assertIn(session, self.server.sessions)

    def test_a_consent_post_needs_its_nonce_its_session_and_the_origin_of_the_server(self):
        page, session = self.page(FILE)
        other_page, other_session = self.page(FILE, account="bob@example.com")
        cases = [({"decision": "approve"}, session, self.server.origin),
                 ({"nonce": page.page["nonce"], "decision": "approve"}, session, None),
                 ({"nonce": page.page["nonce"], "decision": "approve"}, session, "https://evil.example"),
                 ({"nonce": other_page.page["nonce"], "decision": "approve"}, session, self.server.origin)]
        for form, used_session, origin in cases:
            with self.subTest(form=sorted(form), origin=origin):
                self.assertEqual(self.server.consent(used_session, form, origin).status, 400)
        self.assertEqual((self.server.codes, self.server.approvals), ({}, {}))

    def test_a_loopback_redirect_uri_takes_any_port_and_nothing_else_changes(self):
        page, _ = self.page(FILE, port=61000)
        self.assertEqual(page.status, 200)
        bad = self.params(FILE)
        for uri in ("http://127.0.0.1:61000/other", "http://localhost:5000/callback",
                    "https://127.0.0.1:5000/callback", "http://127.0.0.1:5000/callback?x=1"):
            with self.subTest(uri=uri):
                self.assertEqual(self.server.authorize({**bad, "redirect_uri": uri}, None).status, 400)

    def test_registration_takes_only_ipv4_loopback_redirect_uris(self):
        for uri in ("https://app.example/callback", "http://[::1]:5000/callback", "http://localhost:5000/cb"):
            with self.subTest(uri=uri):
                self.assertEqual(self.server.register({"redirect_uris": [uri]}).status, 400)


class PerPersonTests(IssuerTestCase):
    """RESOLVER-PROFILE.md, sections 11.2 and 12.2; SC-24."""

    def test_a_reference_of_another_person_is_unresolvable_with_the_reason_unknown(self):
        token = self.grant(FILE, account="bob@example.com")["access_token"]
        response = self.resolve(token, [self.alice_ref])
        self.assertEqual(response.status, 409)
        self.assertEqual(response.body, {"error": "unresolvable", "reasons": {"unknown": 1}})
        self.server.revoke_reference("alice@example.com", self.alice_ref)
        response = self.resolve(token, [self.alice_ref, self.bob_ref])
        self.assertEqual(response.body, {"error": "unresolvable", "reasons": {"unknown": 1}})
        self.assertEqual(self.server.audit.events, [])

    def test_revoked_expired_and_malformed_references_return_no_value(self):
        token = self.grant(FILE)["access_token"]
        expired = self.server.issue("alice@example.com", "email", "old@example.com", expires_at=self.clock.now - 1)
        revoked = self.server.issue("alice@example.com", "email", "gone@example.com")
        self.server.revoke_reference("alice@example.com", revoked)
        response = self.resolve(token, [self.alice_ref, expired, revoked, "⟦sref:email:short⟧"])
        self.assertEqual(response.body, {"error": "unresolvable",
                                         "reasons": {"expired": 1, "revoked": 1, "malformed": 1}})

    def test_the_account_hint_keeps_at_most_three_and_at_most_half_of_the_local_part_and_the_whole_domain(self):
        cases = {"alice@example.com": "al\u2026@example.com", "alison@example.com": "ali\u2026@example.com", "al@example.com": "a\u2026@example.com",
                 "a@example.com": "\u2026@example.com", "abcdefgh@x.example": "abc\u2026@x.example",
                 "abc@example.com": "a\u2026@example.com", "operator": "ope\u2026"}
        for account, hint in cases.items():
            with self.subTest(account=account):
                self.assertEqual(account_hint(account), hint)

    def test_token_and_refresh_answers_carry_the_hint_and_not_the_address(self):
        body = self.grant(FILE)
        self.assertEqual(body["account_hint"], "al\u2026@example.com")
        again = self.server.token({"grant_type": "refresh_token", "refresh_token": body["refresh_token"],
                                   "client_id": self.client}).body
        self.assertEqual(again["account_hint"], "al\u2026@example.com")
        self.assertNotIn("alice@example.com", json.dumps([body, again]))


class AuditTests(IssuerTestCase):
    """RESOLVER-PROFILE.md, section 15; PROCESS-PROFILE.md, section 6, rule 2; DISPLAY-PROFILE.md, section 6."""

    def test_no_value_leaves_without_its_audit_event(self):
        token = self.grant(FILE)["access_token"]
        self.server.audit.fail = True
        response = self.resolve(token, [self.alice_ref])
        self.assertEqual((response.status, response.body), (503, {"error": "audit_unavailable"}))
        self.assertEqual(self.server.used, {})
        self.server.audit.fail = False
        self.assertEqual(self.resolve(token, [self.alice_ref]).body, {"values": {self.alice_ref: ALICE_VALUE}})
        self.assertEqual(len(self.server.audit.events), 1)

    def test_the_audit_event_keeps_a_program_name_or_the_screen_and_no_value_or_reference(self):
        token = self.grant(ALL)["access_token"]
        for sink_type, destination in (("process", "/usr/bin/psql"), ("process", "psql -h db"),
                                       ("display", "screen"), ("local_file", "/home/a/customers.csv")):
            self.assertEqual(self.resolve(token, [self.alice_ref], sink_type, destination).status, 200)
        events = self.server.audit.events
        self.assertEqual([e["destination"] for e in events][:3], ["psql", "other", "screen"])
        self.assertTrue(events[3]["destination"].startswith("sha256:"))
        self.assertEqual([e["sink_profile"] for e in events], [PROCESS, PROCESS, DISPLAY, LOCAL_FILE])
        text = json.dumps(events)
        for secret in (ALICE_VALUE, self.alice_ref, "customers.csv", "-h db"):
            self.assertNotIn(secret, text)

    def test_audit_destination_of_a_program(self):
        cases = {"psql": "psql", "/usr/local/bin/psql": "psql", "C:\\bin\\psql.exe": "psql.exe",
                 "psql --password x": "other", "a/b c": "other", "dir/": "other"}
        for destination, kept in cases.items():
            with self.subTest(destination=destination):
                self.assertEqual(audit_destination(PROCESS, destination), kept)

    def test_a_reveal_counts_toward_the_daily_quota(self):
        self.server.daily_quota = 2
        token = self.grant(ALL)["access_token"]
        self.assertEqual(self.resolve(token, [self.alice_ref], "display", "screen").status, 200)
        self.assertEqual(self.resolve(token, [self.alice_ref], "process", "psql").status, 200)
        response = self.resolve(token, [self.alice_ref])
        self.assertEqual((response.status, response.body["error"]), (429, "quota_exceeded"))


class DisplayRequestTests(IssuerTestCase):
    """DISPLAY-PROFILE.md, section 3."""

    def test_a_display_request_needs_the_screen_and_exactly_one_reference(self):
        token = self.grant(ALL)["access_token"]
        other = self.server.issue("alice@example.com", "email", "second@example.com")
        for refs, destination in (([self.alice_ref], "terminal"), ([self.alice_ref, other], "screen"),
                                  ([self.alice_ref, self.alice_ref], "screen"), ([], "screen")):
            with self.subTest(refs=len(refs), destination=destination):
                response = self.resolve(token, refs, "display", destination)
                self.assertEqual((response.status, response.body["error"]), (400, "invalid_request"))
        self.assertEqual(self.server.lookups, 0)
        self.assertEqual(self.resolve(token, [self.alice_ref], "display", "screen").status, 200)

    def test_other_request_errors(self):
        token = self.grant(FILE)["access_token"]
        self.assertEqual(self.resolve(token, [self.alice_ref], destination="a\nb").status, 400)
        self.assertEqual(self.resolve(token, [self.alice_ref], destination="").status, 400)
        many = [self.server.issue("alice@example.com", "email", f"u{i}@example.com") for i in range(101)]
        self.assertEqual(self.resolve(token, many).status, 413)
        self.assertEqual(self.resolve(token, many[:100] + many[:1]).status, 200)
        self.assertEqual(self.server.resolve(None, b"{}").headers["WWW-Authenticate"], 'Bearer error="invalid_token"')


class DeviceTests(IssuerTestCase):
    """RESOLVER-PROFILE.md, section 10.4; SC-26."""

    def test_a_person_revokes_a_device_and_every_credential_of_it_stops(self):
        body = self.grant(FILE)
        page, session = self.page(FILE)
        unused = self.approve(page, session)
        self.server.revoke_device("alice@example.com", "alice@example.com", self.client)
        self.assertEqual(self.resolve(body["access_token"], [self.alice_ref]).status, 401)
        refresh = self.server.token({"grant_type": "refresh_token", "refresh_token": body["refresh_token"],
                                     "client_id": self.client})
        self.assertEqual(refresh.status, 400)
        code = self.server.token({"grant_type": "authorization_code", "code": unused, "client_id": self.client,
                                  "redirect_uri": "http://127.0.0.1:5000/callback", "code_verifier": "v" * 43})
        self.assertEqual(code.status, 400)
        self.assertEqual(self.server.devices("alice@example.com", "alice@example.com"), [])

    def test_a_revocation_does_not_stop_another_person_on_the_same_client(self):
        alice = self.grant(FILE)
        bob = self.grant(FILE, account="bob@example.com")
        self.server.revoke_device("alice@example.com", "alice@example.com", self.client)
        self.assertEqual(self.resolve(bob["access_token"], [self.bob_ref]).status, 200)
        self.assertEqual(self.resolve(alice["access_token"], [self.alice_ref]).status, 401)

    def test_a_credential_from_before_the_revocation_stays_dead_after_a_new_approval(self):
        body = self.grant(FILE)
        in_flight = dict(self.server.refresh[body["refresh_token"]])   # a refresh that read its record
        code_record = None
        page, session = self.page(FILE)
        code = self.approve(page, session)
        code_record = dict(self.server.codes[code])
        self.server.revoke_device("alice@example.com", "alice@example.com", self.client)
        self.grant(FILE)                                                # a new approval of the same device
        self.assertIsNone(self.server._issue(in_flight))
        self.assertIsNone(self.server._issue(code_record))
        self.server.access["old"] = {**in_flight, "expires_at": self.clock.now + 60}
        self.assertEqual(self.resolve("old", [self.alice_ref]).status, 401)

    def test_an_unreadable_epoch_refuses_the_credential(self):
        body = self.grant(FILE)
        del self.server.epochs[("alice@example.com", self.client)]
        self.assertEqual(self.resolve(body["access_token"], [self.alice_ref]).status, 401)

    def test_only_the_person_or_an_administrator_manages_devices(self):
        self.grant(f"{RESOLVE_SCOPE} {PROCESS_SCOPE}")
        with self.assertRaises(PermissionError):
            self.server.devices("bob@example.com", "alice@example.com")
        with self.assertRaises(PermissionError):
            self.server.revoke_device("bob@example.com", "alice@example.com", self.client)
        rows = self.server.devices("root@example.com", "alice@example.com")
        self.assertEqual(rows, [{"client_id": self.client, "client_name": "Test host", "commands": True,
                                 "screen": False}])
        self.server.revoke_device("root@example.com", "alice@example.com", self.client)
        self.assertEqual(self.server.devices("alice@example.com", "alice@example.com"), [])

    def test_a_withdrawn_or_expired_approval_stops_refresh_and_the_live_token(self):
        body = self.grant(FILE)
        self.server.withdraw_approvals("alice@example.com")
        self.assertEqual(self.resolve(body["access_token"], [self.alice_ref]).status, 401)
        self.assertEqual(self.server.token({"grant_type": "refresh_token", "refresh_token": body["refresh_token"],
                                            "client_id": self.client}).status, 400)
        self.server.access_lifetime = 10 * self.server.approval_lifetime   # only the approval ends
        body = self.grant(FILE)
        self.clock.now += self.server.approval_lifetime + 1
        self.assertEqual(self.resolve(body["access_token"], [self.alice_ref]).status, 401)


if __name__ == "__main__":
    unittest.main()
