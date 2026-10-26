"""The test host's materialization through oauth-resolver-1 and local-file-1.

Offline: one local stdlib HTTP server plays the protected resource metadata, the
authorization server (metadata, dynamic client registration, Authorization Code
+ PKCE S256, rotating refresh tokens) and the resolve endpoint. The browser is a
function that follows the authorization redirect to the host's loopback port.

Mutation check. Each guard below was disabled once and at least one test here
failed (the test that failed is in brackets). The script replaced the guard
condition with ``False`` (or ``True``), ran this module, and restored the file:

* ``OAuthHttpResolver``: the agent-token comparison [test_the_agent_token_is_never_sent];
  the exact key-set check of a 200 batch [test_an_incomplete_or_extra_batch_writes_nothing];
  the status check for a non-200 answer [test_a_revoked_reference_in_a_batch_writes_nothing];
  one renewal only after a 401 (``if status == 401:``) [test_an_expired_token_is_refreshed_once_then_the_run_fails
  does not end: the host refreshes without limit; the run timed out];
  the issuer lookup returning the only endpoint for any issuer [test_a_reference_from_another_issuer_is_not_sent];
  ``require_secure`` returning the URL unchanged [test_an_insecure_resolve_endpoint_is_refused];
  the batch split at 100 [test_more_than_100_references_go_in_batches_of_100];
* ``_NoRedirect`` removed from the opener [test_a_redirect_from_the_resolve_endpoint_is_not_followed];
* ``discover_protected_resource``: the resource equality [test_metadata_for_another_resource_is_refused];
* ``_resolver_setup``: the origin check of a discovered endpoint [test_a_discovered_cross_origin_endpoint_is_refused];
* ``OAuthResolverCredential``: the cache expiry check [test_an_expired_token_is_refreshed_and_rotated];
  the state comparison [test_a_callback_with_another_state_is_refused];
  the ``iss`` comparison [test_a_callback_from_another_issuer_is_refused];
  the granted-scope check [test_a_token_without_the_resolve_scope_is_refused];
  ``interactive`` ignored in ``renew`` [test_without_a_token_and_without_interaction_nothing_is_written];
* ``TokenCache``: mode 0600 on write, set to 0644 [test_interactive_authorization_materializes_and_reports_no_secret
  and every test that reads the cache again];
  the permission check on read [test_a_cache_file_that_others_can_read_is_refused];
* ``materialize``: the profile check [test_without_the_negotiated_profiles_nothing_is_sent,
  test_without_advertised_profiles_the_host_does_not_resolve];
  the trusted-issuer filter [test_an_ambiguous_reference_is_not_sent];
"""

from __future__ import annotations

from base64 import urlsafe_b64encode
from hashlib import sha256
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import secrets
import sys
import tempfile
import threading
import time
import unittest
from urllib.parse import parse_qs, urlencode, urlsplit
from urllib.request import urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "demo"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import mcp_host  # noqa: E402
from mcp_host import HostReport, ResolveConfig, _check_materialization, materialize  # noqa: E402
from sensitive_references import ProvenanceStore  # noqa: E402
from sensitive_references.capabilities import NegotiatedSensitiveReferences  # noqa: E402
from sensitive_references.reference import make_token  # noqa: E402
from sensitive_references.resolver import SinkContext  # noqa: E402
from sensitive_references.resolver_client import (  # noqa: E402
    OAuthHttpResolver,
    OAuthResolverCredential,
    ResolveEndpoint,
    ResolverClientError,
    TokenCache,
)

SCOPE = "sensitive-references.resolve"
AGENT_TOKEN = "agent-" + "token-for-the-mcp-endpoint-only"
AGREED = NegotiatedSensitiveReferences("1", frozenset({"oauth-resolver-1"}), frozenset({"local-file-1"}))


class FakeServer:
    """Protected resource metadata, authorization server and resolve endpoint on one origin."""

    def __init__(self) -> None:
        self.values: dict[str, str] = {}          # token -> value for the signed-in user
        self.revoked: set[str] = set()
        self.foreign: set[str] = set()            # tokens of another user
        self.access: dict[str, float] = {}        # access token -> expiry
        self.refresh: dict[str, str] = {}         # refresh token -> client_id
        self.clients: dict[str, list[str]] = {}
        self.codes: dict[str, dict] = {}
        self.authorization_headers: list[str] = []
        self.resolve_batches: list[list[str]] = []
        self.authorize_requests: list[dict] = []
        self.refresh_calls = 0
        self.mode: set[str] = set()
        self.elsewhere: list = []
        self.prm_extra: dict | None = None
        self.prm_resource: str | None = None
        self.expires_in = 3600
        self._server = ThreadingHTTPServer(("127.0.0.1", 0), self._handler())
        self.base = f"http://127.0.0.1:{self._server.server_address[1]}"
        self.issuer = f"{self.base}/mcp"
        self.prm_extra = {"resolve_endpoint": f"{self.base}/resolve"}
        threading.Thread(target=self._server.serve_forever, daemon=True).start()

    def close(self) -> None:
        self._server.shutdown()
        self._server.server_close()

    def issue(self, value: str) -> str:
        token = make_token("email").token
        self.values[token] = value
        return token

    def new_access(self, lifetime: float | None = None) -> str:
        token = secrets.token_urlsafe(24)
        self.access[token] = time.time() + (lifetime if lifetime is not None else self.expires_in)
        return token

    def _token_response(self, client_id: str) -> dict:
        refresh = secrets.token_urlsafe(24)
        self.refresh[refresh] = client_id
        body = {"access_token": self.new_access(), "token_type": "Bearer", "expires_in": self.expires_in,
                "refresh_token": refresh, "scope": "other.scope" if "narrow_scope" in self.mode else SCOPE}
        return body

    def _handler(self):
        fake = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def _send(self, status, body=None, headers=None):
                data = json.dumps(body).encode() if body is not None else b""
                self.send_response(status)
                for k, v in (headers or {}).items():
                    self.send_header(k, v)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def _record(self):
                if self.headers.get("Authorization"):
                    fake.authorization_headers.append(self.headers["Authorization"])

            def _body(self):
                return self.rfile.read(int(self.headers.get("Content-Length") or 0))

            def do_GET(self):  # noqa: N802
                self._record()
                parts = urlsplit(self.path)
                if parts.path == "/.well-known/oauth-protected-resource/mcp":
                    doc = {"resource": fake.prm_resource or fake.issuer, "authorization_servers": [fake.base]}
                    if fake.prm_extra is not None:
                        doc["sensitive_references"] = fake.prm_extra
                    return self._send(200, doc)
                if parts.path == "/.well-known/oauth-authorization-server":
                    return self._send(200, {
                        "issuer": fake.base, "authorization_endpoint": f"{fake.base}/authorize",
                        "token_endpoint": f"{fake.base}/token", "registration_endpoint": f"{fake.base}/register",
                        "code_challenge_methods_supported": ["S256"],
                        "authorization_response_iss_parameter_supported": True})
                if parts.path == "/elsewhere":
                    fake.elsewhere.append(self.headers.get("Authorization"))
                    return self._send(404, {"error": "not_found"})
                if parts.path == "/authorize":
                    q = {k: v[0] for k, v in parse_qs(parts.query).items()}
                    fake.authorize_requests.append(q)
                    if q["redirect_uri"] not in fake.clients.get(q["client_id"], []):
                        return self._send(400, {"error": "invalid_redirect_uri"})
                    code = secrets.token_urlsafe(16)
                    fake.codes[code] = q
                    state = "wrong" if "wrong_state" in fake.mode else q["state"]
                    iss = "http://127.0.0.1:1" if "wrong_iss" in fake.mode else fake.base
                    location = q["redirect_uri"] + "?" + urlencode({"code": code, "state": state, "iss": iss})
                    return self._send(302, headers={"Location": location})
                return self._send(404, {"error": "not_found"})

            def do_POST(self):  # noqa: N802
                self._record()
                parts = urlsplit(self.path)
                raw = self._body()
                if parts.path == "/register":
                    doc = json.loads(raw)
                    client_id = secrets.token_urlsafe(8)
                    fake.clients[client_id] = doc["redirect_uris"]
                    return self._send(201, {"client_id": client_id, "redirect_uris": doc["redirect_uris"]})
                if parts.path == "/token":
                    form = {k: v[0] for k, v in parse_qs(raw.decode()).items()}
                    if form.get("grant_type") == "authorization_code":
                        request = fake.codes.pop(form.get("code"), None)
                        challenge = urlsafe_b64encode(sha256(form.get("code_verifier", "").encode()).digest()).rstrip(b"=").decode()
                        if (request is None or request["code_challenge"] != challenge
                                or request["redirect_uri"] != form.get("redirect_uri")
                                or request["resource"] != form.get("resource")):
                            return self._send(400, {"error": "invalid_grant"})
                        return self._send(200, fake._token_response(form["client_id"]))
                    if form.get("grant_type") == "refresh_token":
                        fake.refresh_calls += 1
                        client = fake.refresh.pop(form.get("refresh_token"), None)  # rotation: single use
                        if client is None or "refresh_fails" in fake.mode:
                            return self._send(400, {"error": "invalid_grant"})
                        return self._send(200, fake._token_response(client))
                    return self._send(400, {"error": "unsupported_grant_type"})
                if parts.path == "/resolve":
                    if "redirect" in fake.mode:
                        return self._send(302, headers={"Location": f"{fake.base}/elsewhere"})
                    auth = self.headers.get("Authorization", "")
                    token = auth.removeprefix("Bearer ")
                    if ("always_401" in fake.mode or not auth.startswith("Bearer ")
                            or fake.access.get(token, 0) <= time.time()):
                        return self._send(401, {"error": "invalid_token"})
                    doc = json.loads(raw)
                    refs = doc["references"]
                    fake.resolve_batches.append(refs)
                    # The codes of SC-11 (protocol-package/SPEC-CHANGES.md).
                    if not refs:
                        return self._send(400, {"error": "invalid_request"})
                    if len(refs) > 100:
                        return self._send(413, {"error": "too_many_references"})
                    # A reference of another principal is unknown to this one.
                    unknown = [r for r in refs if r not in fake.values or r in fake.foreign]
                    revoked = [r for r in refs if r in fake.revoked and r not in unknown]
                    if unknown or revoked:
                        reasons = {k: n for k, n in (("unknown", len(unknown)), ("revoked", len(revoked))) if n}
                        return self._send(409, {"error": "unresolvable", "reasons": reasons})
                    values = {r: fake.values[r] for r in refs}
                    if "incomplete" in fake.mode:
                        values.pop(refs[0])
                    if "extra" in fake.mode:
                        values[make_token("email").token] = "extra@example.com"
                    return self._send(200, {"values": values})
                if parts.path == "/elsewhere":
                    fake.elsewhere.append(self.headers.get("Authorization"))
                    return self._send(404, {"error": "not_found"})
                return self._send(404, {"error": "not_found"})

        return Handler


def follow(url: str) -> None:
    """The browser: the fake page approves at once and redirects to the loopback callback."""
    urlopen(url, timeout=5).read()


class MaterializeTests(unittest.TestCase):
    def setUp(self):
        self.server = FakeServer()
        self.addCleanup(self.server.close)
        self.dir = Path(tempfile.mkdtemp(prefix="sref-m4b-"))
        self.dest = self.dir / "out.txt"
        self.cache = self.dir / "tokens.json"
        self.alice = self.server.issue("alice@example.com")
        self.bob = self.server.issue("bob@example.com")
        self.sentinels = ["alice@example.com", "bob@example.com"]
        self.store = ProvenanceStore()
        self.observe(self.alice, self.bob)

    def observe(self, *tokens, issuer=None):
        self.store.observe_mcp_result(issuer or self.server.issuer, extension_negotiated=True,
                                      result={"texts": [" ".join(tokens)]})

    def config(self, **overrides):
        values = dict(destination=str(self.dest), token_cache=str(self.cache), open_browser=follow,
                      authorization_timeout=10, timeout=5)
        values.update(overrides)
        return ResolveConfig(**values)

    def run_materialize(self, refs=None, agreed=AGREED, **overrides):
        return materialize(issuer=self.server.issuer, references=refs or [self.alice, self.bob],
                           provenance=self.store, agreed=agreed, config=self.config(**overrides),
                           sentinels=self.sentinels, agent_token=AGENT_TOKEN)

    def cache_entry(self, **entry):
        TokenCache(self.cache).store(json.dumps([self.server.issuer, self.server.base, SCOPE]),
                                     {"client_id": "pre", **entry})

    def assert_nothing_written(self, report, before=None):
        self.assertFalse(report.materialized)
        self.assertIsNotNone(report.failure)
        if before is None:
            self.assertFalse(self.dest.exists())
        else:
            self.assertEqual(self.dest.read_text(), before)
        self.assertEqual([p.name for p in self.dir.iterdir() if p.name.startswith(".sref-")], [])

    def assert_report_clean(self, report):
        text = json.dumps(report.__dict__)
        for secret in [self.alice, self.bob, *self.sentinels, *self.server.access, *self.server.refresh, AGENT_TOKEN]:
            self.assertNotIn(secret, text)
        self.assertNotIn("sref:", text)

    # -- the success paths

    def test_interactive_authorization_materializes_and_reports_no_secret(self):
        report = self.run_materialize()

        self.assertTrue(report.materialized, report.failure)
        self.assertEqual(report.resolver_token_source, "interactive")
        self.assertEqual(report.references_sent, 2)
        self.assertEqual(report.sentinels_in_file, 2)
        self.assertTrue(report.model_content_keeps_reference)
        self.assertEqual(report.sentinels_in_model_content, 0)
        self.assertEqual(self.dest.read_text(), "alice@example.com\nbob@example.com\n")
        request = self.server.authorize_requests[0]
        self.assertEqual((request["scope"], request["resource"], request["code_challenge_method"]),
                         (SCOPE, self.server.issuer, "S256"))
        self.assertTrue(request["redirect_uri"].startswith("http://127.0.0.1:"))
        self.assertEqual(self.cache.stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.dest.stat().st_mode & 0o077, 0)
        self.assert_report_clean(report)
        host = HostReport(server=self.server.issuer, declared=True)
        _check_materialization(host, report)
        self.assertTrue(host.ok, host.failures)

    def test_a_cached_token_is_used_without_a_new_authorization(self):
        self.run_materialize()
        self.dest.unlink()
        report = self.run_materialize()

        self.assertTrue(report.materialized, report.failure)
        self.assertEqual(report.resolver_token_source, "cache")
        self.assertEqual(len(self.server.authorize_requests), 1)

    def test_the_template_is_configuration(self):
        report = self.run_materialize(template="To: {ref}; ")
        self.assertTrue(report.materialized, report.failure)
        self.assertEqual(self.dest.read_text(), "To: alice@example.com; To: bob@example.com; ")

    def test_the_endpoint_and_scope_come_from_discovery(self):
        self.server.prm_extra = {"resolve_endpoint": f"{self.server.base}/resolve", "resolve_scope": SCOPE,
                                 "resolver_profiles": ["oauth-resolver-1"], "sink_profiles": ["local-file-1"]}
        report = self.run_materialize()
        self.assertTrue(report.materialized, report.failure)

    def test_more_than_100_references_go_in_batches_of_100(self):
        many = [self.server.issue(f"user{i}@example.com") for i in range(150)]
        self.observe(*many)
        report = self.run_materialize(refs=many, resolve_endpoint=f"{self.server.base}/resolve")

        self.assertTrue(report.materialized, report.failure)
        self.assertEqual([len(b) for b in self.server.resolve_batches], [100, 50])

    # -- authorization failures

    def test_without_a_token_and_without_interaction_nothing_is_written(self):
        report = self.run_materialize(interactive=False, resolve_endpoint=f"{self.server.base}/resolve")
        self.assert_nothing_written(report)
        self.assertEqual(self.server.resolve_batches, [])
        self.assertEqual(self.server.authorize_requests, [])

    def test_an_invalid_token_writes_nothing(self):
        self.dest.write_text("before\n")
        self.cache_entry(access_token="not-a-valid-token")
        report = self.run_materialize(interactive=False, resolve_endpoint=f"{self.server.base}/resolve")
        self.assert_nothing_written(report, before="before\n")
        # The server answered 401 invalid_token; the host could not renew without
        # interaction and names its own reason.
        self.assertEqual(report.failure, "resolution failed: unauthorized")
        self.assert_report_clean(report)

    def test_the_agent_token_is_never_sent(self):
        self.run_materialize()
        self.assertTrue(self.server.authorization_headers)
        self.assertNotIn(f"Bearer {AGENT_TOKEN}", self.server.authorization_headers)
        # A cache that holds the agent token is refused before a request.
        self.dest.unlink()
        self.server.resolve_batches.clear()
        self.cache_entry(access_token=AGENT_TOKEN)
        report = self.run_materialize(interactive=False, resolve_endpoint=f"{self.server.base}/resolve")
        self.assert_nothing_written(report)
        self.assertEqual(report.failure, "resolution failed: agent_token")
        self.assertNotIn(f"Bearer {AGENT_TOKEN}", self.server.authorization_headers)

    def test_an_expired_token_is_refreshed_and_rotated(self):
        self.run_materialize()
        self.dest.unlink()
        key = json.dumps([self.server.issuer, self.server.base, SCOPE])
        entry = TokenCache(self.cache).load(key)
        old_refresh = entry["refresh_token"]
        TokenCache(self.cache).store(key, {**entry, "expires_at": time.time() - 1})

        report = self.run_materialize(interactive=False)

        self.assertTrue(report.materialized, report.failure)
        self.assertEqual(report.resolver_token_source, "refresh")
        self.assertEqual(report.resolve_requests, 1, "the expired token was sent before the refresh")
        new_refresh = TokenCache(self.cache).load(key)["refresh_token"]
        self.assertNotEqual(new_refresh, old_refresh)
        self.assertNotIn(old_refresh, self.server.refresh)

    def test_an_expired_token_is_refreshed_once_then_the_run_fails(self):
        self.run_materialize()
        self.dest.write_text("before\n")
        self.server.mode.add("always_401")
        self.server.refresh_calls = 0
        report = self.run_materialize(interactive=False)

        self.assert_nothing_written(report, before="before\n")
        self.assertEqual(self.server.refresh_calls, 1)
        self.assertEqual(report.resolve_requests, 2)

    def test_a_failed_refresh_without_interaction_writes_nothing(self):
        self.cache_entry(access_token="expired", expires_at=time.time() - 100, refresh_token="unknown")
        report = self.run_materialize(interactive=False, resolve_endpoint=f"{self.server.base}/resolve")
        self.assert_nothing_written(report)
        self.assertEqual(self.server.resolve_batches, [])

    def test_a_callback_with_another_state_is_refused(self):
        self.server.mode.add("wrong_state")
        report = self.run_materialize()
        self.assert_nothing_written(report)
        self.assertEqual(report.failure, "resolution failed: state_mismatch")

    def test_a_callback_from_another_issuer_is_refused(self):
        self.server.mode.add("wrong_iss")
        report = self.run_materialize()
        self.assert_nothing_written(report)
        self.assertEqual(report.failure, "resolution failed: issuer_mismatch")

    def test_a_token_without_the_resolve_scope_is_refused(self):
        self.server.mode.add("narrow_scope")
        report = self.run_materialize()
        self.assert_nothing_written(report)
        self.assertEqual(report.failure, "resolution failed: scope_not_granted")

    def test_a_cache_file_that_others_can_read_is_refused(self):
        self.cache_entry(access_token="x")
        os.chmod(self.cache, 0o644)
        report = self.run_materialize(resolve_endpoint=f"{self.server.base}/resolve")
        self.assert_nothing_written(report)
        self.assertEqual(report.failure, "resolution failed: token_cache_permissions")

    # -- batch failures

    def test_a_revoked_reference_in_a_batch_writes_nothing(self):
        self.dest.write_text("before\n")
        self.server.revoked.add(self.bob)
        report = self.run_materialize()
        self.assert_nothing_written(report, before="before\n")
        self.assertEqual(report.failure, "resolution failed: unresolvable")
        self.assert_report_clean(report)

    def test_a_partially_invalid_batch_writes_nothing(self):
        unknown = make_token("email").token
        self.observe(unknown)
        report = self.run_materialize(refs=[self.alice, unknown, self.bob])
        self.assert_nothing_written(report)

    def test_a_reference_of_another_user_writes_nothing(self):
        self.server.foreign.add(self.alice)
        report = self.run_materialize()
        self.assert_nothing_written(report)
        self.assertEqual(report.failure, "resolution failed: unresolvable")

    def test_an_incomplete_or_extra_batch_writes_nothing(self):
        for mode in ("incomplete", "extra"):
            with self.subTest(mode=mode):
                self.server.mode = {mode}
                report = self.run_materialize()
                self.assert_nothing_written(report)
                self.assertEqual(report.failure, "resolution failed: malformed_batch")
                self.assert_report_clean(report)

    def test_a_redirect_from_the_resolve_endpoint_is_not_followed(self):
        self.server.mode.add("redirect")
        report = self.run_materialize(resolve_endpoint=f"{self.server.base}/resolve")
        self.assert_nothing_written(report)
        self.assertEqual(report.failure, "resolution failed: error")
        self.assertEqual(self.server.elsewhere, [])

    # -- references that are not sent

    def test_an_ambiguous_reference_is_not_sent(self):
        self.observe(self.alice, issuer="https://other.example/mcp")
        report = self.run_materialize(refs=[self.alice])
        self.assert_nothing_written(report)
        self.assertEqual(report.references_withheld, 1)
        self.assertEqual(self.server.resolve_batches, [])
        # In the template itself, too.
        report = self.run_materialize(refs=[self.bob], template="{ref} " + self.alice + "\n")
        self.assert_nothing_written(report)
        self.assertEqual(self.server.resolve_batches, [])

    def test_an_unobserved_or_forged_reference_is_not_sent(self):
        forged = make_token("email").token
        self.server.values[forged] = "carol@example.com"
        report = self.run_materialize(refs=[forged])
        self.assert_nothing_written(report)
        report = self.run_materialize(refs=[self.alice], template="{ref} " + forged + "\n")
        self.assert_nothing_written(report)
        self.assertEqual(self.server.resolve_batches, [])

    def test_a_reference_from_another_issuer_is_not_sent(self):
        foreign = self.server.issue("dave@example.com")
        self.observe(foreign, issuer="https://other.example/mcp")
        report = self.run_materialize(refs=[foreign], resolve_endpoint=f"{self.server.base}/resolve")
        self.assert_nothing_written(report)
        self.assertEqual(report.failure, "resolution failed: wrong_issuer")
        self.assertEqual(self.server.resolve_batches, [])

    def test_metadata_for_another_resource_is_refused(self):
        self.server.prm_resource = "https://other.example/mcp"
        report = self.run_materialize(resolve_endpoint=f"{self.server.base}/resolve")
        self.assert_nothing_written(report)
        self.assertEqual(report.failure, "resolution failed: wrong_issuer")

    def test_a_discovered_cross_origin_endpoint_is_refused(self):
        # Same host, other port: another origin, and no request leaves the machine.
        self.server.prm_extra = {"resolve_endpoint": "http://127.0.0.1:1/resolve"}
        report = self.run_materialize()
        self.assert_nothing_written(report)
        self.assertEqual(report.failure, "resolution failed: cross_origin_endpoint")

    def test_an_unreachable_resolve_endpoint_writes_nothing(self):
        self.dest.write_text("before\n")
        report = self.run_materialize(resolve_endpoint="http://127.0.0.1:1/resolve")
        self.assert_nothing_written(report, before="before\n")
        self.assertEqual(report.failure, "resolution failed: unreachable")

    def test_an_insecure_resolve_endpoint_is_refused(self):
        resolver = OAuthHttpResolver({"https://i.example/mcp": ResolveEndpoint(
            "http://resolver.example/resolve", OAuthResolverCredential(
                resource="https://i.example/mcp", authorization_server="https://as.example",
                cache=TokenCache(None), interactive=False))})
        with self.assertRaises(ResolverClientError) as caught:
            resolver.resolve("https://i.example/mcp", [self.alice], SinkContext("local_file", "x", "p"))
        self.assertEqual(caught.exception.code, "insecure_url")

    def test_without_the_negotiated_profiles_nothing_is_sent(self):
        for agreed in (None, NegotiatedSensitiveReferences("1", frozenset(), frozenset({"local-file-1"})),
                       NegotiatedSensitiveReferences("1", frozenset({"oauth-resolver-1"}), frozenset())):
            with self.subTest(agreed=agreed):
                report = self.run_materialize(agreed=agreed)
                self.assert_nothing_written(report)
        self.assertEqual(self.server.authorize_requests, [])
        self.assertEqual(self.server.resolve_batches, [])


def _serve_mcp(tool_text: str, settings: dict):
    """A real MCP SDK 2.x server on a loopback port that advertises ``settings``."""
    import socket

    import uvicorn
    from mcp.server.extension import Extension
    from mcp.server.mcpserver import MCPServer

    class SensitiveReferences(Extension):
        identifier = "org.example/sensitive-references"

        def settings(self):
            return settings

    server = MCPServer("fixture", extensions=[SensitiveReferences()], log_level="WARNING")

    @server.tool()
    def read() -> str:
        return tool_text

    probe = socket.socket()
    probe.bind(("127.0.0.1", 0))
    port = probe.getsockname()[1]
    probe.close()
    runner = uvicorn.Server(uvicorn.Config(server.streamable_http_app(), host="127.0.0.1", port=port,
                                           log_level="warning"))
    threading.Thread(target=runner.run, daemon=True).start()
    deadline = time.time() + 10
    while not runner.started and time.time() < deadline:
        time.sleep(0.05)
    return runner, f"http://127.0.0.1:{port}/mcp"


try:
    import mcp.server.extension  # noqa: F401
    import uvicorn  # noqa: F401
    HAVE_SDK2 = True
except ImportError:
    HAVE_SDK2 = False


@unittest.skipUnless(HAVE_SDK2, "needs the MCP SDK 2.x and uvicorn (the mcp-host extra)")
class EndToEndTests(unittest.TestCase):
    """``mcp_host.main`` against a real MCP server, the fake authorization server and resolve endpoint."""

    PROFILES = {"versions": ["1"], "resolver_profiles": ["oauth-resolver-1"], "sink_profiles": ["local-file-1"]}

    def setUp(self):
        self.fake = FakeServer()
        self.addCleanup(self.fake.close)
        self.alice = self.fake.issue("alice@example.com")
        self.dir = Path(tempfile.mkdtemp(prefix="sref-m4b-e2e-"))
        self.dest = self.dir / "out.txt"

    def run_host(self, settings, *extra):
        runner, url = _serve_mcp(f"mail {self.alice}", settings)
        extra = [a.replace("{origin}", url.rsplit("/", 1)[0]) for a in extra]
        self.addCleanup(setattr, runner, "should_exit", True)
        printed = []
        saved = (mcp_host.open_browser, os.environ.get("MCP_TOKEN"), os.environ.get("SREF_SENTINELS"))
        mcp_host.open_browser = follow
        os.environ["MCP_TOKEN"] = AGENT_TOKEN
        os.environ["SREF_SENTINELS"] = "alice@example.com"
        import builtins
        original_print, builtins.print = builtins.print, lambda *a, **k: printed.append(" ".join(map(str, a)))
        try:
            code = mcp_host.main([
                "--url", url, "--extension-id", "org.example/sensitive-references", "--tool", "read",
                "--expect-negotiation", "--resolve-into", str(self.dest),
                "--resolve-endpoint", f"{self.fake.base}/resolve", "--authorization-server", self.fake.base,
                "--resolver-token-cache", str(self.dir / "tokens.json"), "--timeout", "10", *extra])
        finally:
            builtins.print = original_print
            mcp_host.open_browser = saved[0]
            for name, value in (("MCP_TOKEN", saved[1]), ("SREF_SENTINELS", saved[2])):
                if value is None:
                    os.environ.pop(name, None)
                else:
                    os.environ[name] = value
        return code, "\n".join(printed)

    def test_the_host_materializes_an_observed_reference(self):
        code, output = self.run_host(self.PROFILES)
        report = json.loads(output)

        self.assertEqual(code, 0, report["failures"])
        self.assertTrue(report["materialization"]["materialized"])
        self.assertEqual(report["materialization"]["sentinels_in_file"], 1)
        self.assertTrue(report["materialization"]["model_content_keeps_reference"])
        self.assertEqual(self.dest.read_text(), "alice@example.com\n")
        for secret in (self.alice, "alice@example.com", AGENT_TOKEN, *self.fake.access, *self.fake.refresh):
            self.assertNotIn(secret, output)
        self.assertNotIn(f"Bearer {AGENT_TOKEN}", self.fake.authorization_headers)

    def test_a_configured_parent_resource_is_the_issuer(self):
        # The server publishes its metadata for the origin, not for /mcp.
        code, output = self.run_host(self.PROFILES, "--resource", "{origin}")
        report = json.loads(output)

        self.assertEqual(code, 0, report["failures"])
        self.assertEqual(self.dest.read_text(), "alice@example.com\n")

    def test_a_resource_the_mcp_url_is_not_under_stops_the_host(self):
        code, output = self.run_host(self.PROFILES, "--resource", "http://127.0.0.1:1/other")
        report = json.loads(output)

        self.assertEqual(code, 1)
        self.assertIn("the MCP URL is not under the configured resource", report["failures"])
        self.assertFalse(self.dest.exists())
        self.assertEqual((self.fake.authorize_requests, self.fake.resolve_batches), ([], []))

    def test_without_advertised_profiles_the_host_does_not_resolve(self):
        code, output = self.run_host({"versions": ["1"]})
        report = json.loads(output)

        self.assertEqual(code, 1)
        self.assertFalse(report["materialization"]["materialized"])
        self.assertFalse(self.dest.exists())
        self.assertEqual((self.fake.authorize_requests, self.fake.resolve_batches), ([], []))


class HostOptionTests(unittest.TestCase):
    def test_the_mcp_url_must_lie_under_the_resource(self):
        cases = [("https://s.example/mcp", "https://s.example", True),
                 ("https://s.example/mcp", "https://s.example/", True),
                 ("https://s.example/mcp", "https://s.example/mcp", True),
                 ("https://s.example/mcpx", "https://s.example/mcp", False),
                 ("https://s.example/mcp", "https://t.example", False),
                 ("https://s.example/mcp", "http://s.example", False)]
        for url, resource, expected in cases:
            with self.subTest(url=url, resource=resource):
                self.assertIs(mcp_host._within(url, resource), expected)

    def test_a_resolving_host_declares_both_profiles(self):
        self.assertEqual(mcp_host.RESOLVING_HOST_SETTINGS["resolver_profiles"], ["oauth-resolver-1"])
        self.assertEqual(mcp_host.RESOLVING_HOST_SETTINGS["sink_profiles"], ["local-file-1"])
        self.assertNotIn("resolver_profiles", mcp_host.HOST_SETTINGS)

    def test_the_options_map_to_the_configuration(self):
        args = mcp_host.parse_args(["--url", "https://s.example/mcp", "--extension-id", "x/y", "--tool", "t",
                                    "--resolve-into", "out.txt", "--resolve-endpoint", "https://s.example/r",
                                    "--resolve-scope", "s", "--resolver-token-cache", "c.json",
                                    "--no-interactive", "--materialize-template", "a {ref}"])
        config = mcp_host.resolve_config(args)
        self.assertEqual((config.destination, config.resolve_endpoint, config.resolve_scope, config.token_cache,
                          config.interactive, config.template),
                         ("out.txt", "https://s.example/r", "s", "c.json", False, "a {ref}"))


if __name__ == "__main__":
    unittest.main()
