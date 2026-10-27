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
  the validation of the discovery object [test_a_discovery_object_without_a_mandatory_member_is_refused];
  the origin-root fallback put back [test_root_metadata_is_not_a_fallback_for_a_resource_with_a_path];
  the challenge mechanism removed [test_metadata_named_in_the_www_authenticate_challenge_is_used];
  ``require_secure`` on the challenge URL removed [test_an_insecure_challenge_metadata_url_is_refused];
* ``_resolver_setup``: the profile checks of a present discovery object
  [test_a_discovery_object_without_the_negotiated_profiles_is_refused]; the checks skipped when an
  endpoint is configured [test_a_configured_endpoint_does_not_excuse_a_bad_discovery_object]; the
  discovered scope ignored [test_the_endpoint_and_scope_come_from_discovery];
* ``issuer_identity`` (round 1: ``public_endpoint``): the host lower-cased [test_the_issuer_string_is_kept_as_given];
* ``OAuthResolverCredential``: an absent ``iss`` accepted although advertised
  [test_a_callback_without_iss_is_refused_when_the_server_advertises_iss];
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

Rounds two and three: ``tests/tools/mutation_probe.py`` in this repository holds each mutation. It works
on a copy outside the repository. The round-two figure (13 of 13 killed) came from an earlier script
outside the repository and is reported; the repository script repeats those mutations on the current text.

Second review round:

* ``_well_known``: the query dropped, or a trailing slash removed
  [test_the_well_known_url_follows_rfc_9728_section_3_1, test_a_resource_with_a_query_or_a_trailing_slash_keeps_it];
* ``discover_protected_resource``: the old order (well-known URL first)
  [test_the_challenge_comes_before_the_well_known_url]; the fragment check removed
  [test_a_resource_with_a_fragment_is_refused]; an empty ``resolve_scope`` or ``resolve_endpoint`` accepted
  [test_a_discovery_object_with_a_malformed_member_is_refused];
* ``discover_authorization_server``: an absent ``code_challenge_methods_supported`` accepted
  [test_authorization_server_metadata_without_s256_is_refused];
* ``_resolver_setup``: ``use_challenge = True`` [test_a_parent_resource_gets_no_challenge_probe_of_the_mcp_url];
  no metadata accepted without the flag [test_without_metadata_the_host_stops_unless_the_operator_says_there_is_none,
  test_root_metadata_is_not_a_fallback_for_a_resource_with_a_path]; unreachable metadata accepted without the
  flag [test_unreachable_metadata_fails_closed]; the origin check for a discovered endpoint only
  [test_a_configured_cross_origin_endpoint_is_refused];
* ``issuer_identity``: user information and a fragment accepted
  [test_a_url_with_user_information_or_a_fragment_is_no_issuer]; the query removed
  [test_the_issuer_string_is_kept_as_given];
* ``resolve_config``: ``--no-resource-metadata`` ignored [test_the_options_map_to_the_configuration].

Third review round (``FetchPolicyTests`` and the tests named below; the result is in
``protocol-package/CONFORMANCE-RESULTS.md``):

* ``FetchPolicy`` and ``_exchange``: the check before a request removed, every target allowed, the local
  exception removed, names not resolved, an unresolvable name allowed, IPv4-mapped addresses not
  unwrapped, the RFC 4193 range removed; the check of the authorization-server endpoints removed;
* ``authorization_server_metadata_urls``: a terminating slash kept [test_rfc_8414_removes_a_terminating_slash_of_the_issuer];
* ``_resolver_setup``: metadata without the discovery object accepted
  [test_metadata_without_a_discovery_object_stops_the_host]; configuration mode not labelled;
* ``discover_protected_resource``: a challenge URL without a document taken as no metadata
  [test_a_challenge_url_without_a_document_is_not_a_server_without_metadata];
* ``run``: deviation P16 not labelled [test_a_configured_parent_resource_is_the_issuer];
* ``resolve_config``: ``--no-discovery-object`` ignored [test_the_options_map_to_the_configuration].

Fourth review round (``FetchPolicyTests``, ``NoRedirectNoProxyTests`` and the end-to-end test without the
local option; the names of the mutations are in ``tests/tools/mutation_probe.py``):

* ``FetchPolicy``: local mode without the operator option, with mixed DNS records of the MCP host, for any
  origin, for link-local, unspecified and multicast targets, with the MCP host resolved again at each check;
* ``non_public_address``: ``is_private`` in place of ``is_global``, multicast or site-local counted as public,
  NAT64, IPv4-compatible and 6to4 addresses not unwrapped, the embedded address not judged;
* ``_new_opener``: a proxy from the environment, redirects followed;
* ``ResolveConfig`` and ``resolve_config``: local mode on by default
  [test_the_default_configuration_has_no_local_mode], ``--allow-local-targets`` and ``--local-origin``
  ignored [test_the_options_map_to_the_configuration].

Fifth review round (DNS rebinding, ``NoRedirectNoProxyTests``):

* ``_PinnedHTTPConnection`` and ``_PinnedHTTPSConnection``: a connection to the host name in place of the
  checked address [test_the_request_connects_to_the_checked_address,
  test_the_tls_server_name_is_the_host_name_of_the_url];
* ``_pinned_addresses`` and ``_new_opener``: a request without a checked address is sent, the real opener
  does not pin [test_a_request_without_a_checked_address_is_refused].

Sixth review round (``NoRedirectNoProxyTests``):

* ``_new_opener``: an unverified TLS context [test_the_real_opener_verifies_certificates_and_host_names].

Seventh review round (``PinnedTlsTests``, a real TLS server with a test CA):

* ``_PinnedHTTPSConnection``: no certificate check [test_a_certificate_for_another_host_name_is_refused,
  test_a_certificate_from_an_untrusted_ca_is_refused].

Eighth review round (Opus):

* ``_connect_checked``: only the first checked address tried [test_the_host_tries_each_checked_address],
  the timeout dropped [test_each_connection_attempt_gets_the_timeout_of_the_request];
* ``_globally_reachable``: the IANA corrections dropped
  [test_three_registry_entries_that_the_python_tables_do_not_follow].
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
        self.get_paths: list[str] = []
        self.get_targets: list[str] = []          # path and query of each GET
        self.post_paths: list[str] = []
        self.mcp_posts = 0
        self.challenge_resource: str | None = None
        self.challenge_url: str | None = None
        self.prm_extra: dict | None = None
        self.prm_resource: str | None = None
        self.expires_in = 3600
        self._server = ThreadingHTTPServer(("127.0.0.1", 0), self._handler())
        self.base = f"http://127.0.0.1:{self._server.server_address[1]}"
        self.issuer = f"{self.base}/mcp"
        self.prm_extra = self.discovery()
        threading.Thread(target=self._server.serve_forever, daemon=True).start()

    def discovery(self, **members) -> dict:
        """A complete discovery object (SC-02); ``members`` replace or, with None, remove members."""
        extra = {"resolve_endpoint": f"{self.base}/resolve", "resolve_scope": SCOPE,
                 "resolver_profiles": ["oauth-resolver-1"], "sink_profiles": ["local-file-1"]}
        extra.update(members)
        return {k: v for k, v in extra.items() if v is not None}

    def metadata(self, resource: str | None = None) -> dict:
        doc = {"resource": resource or self.prm_resource or self.issuer, "authorization_servers": [self.base]}
        if self.prm_extra is not None:
            doc["sensitive_references"] = self.prm_extra
        return doc

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

    def _token_response(self, client_id: str, scope: str = SCOPE) -> dict:
        refresh = secrets.token_urlsafe(24)
        self.refresh[refresh] = client_id
        body = {"access_token": self.new_access(), "token_type": "Bearer", "expires_in": self.expires_in,
                "refresh_token": refresh, "scope": "other.scope" if "narrow_scope" in self.mode else scope}
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
                fake.get_paths.append(parts.path)
                fake.get_targets.append(self.path)
                if (parts.path.startswith("/.well-known/oauth-protected-resource/")
                        and "no_path_metadata" not in fake.mode):
                    return self._send(200, fake.metadata())
                if parts.path == "/.well-known/oauth-protected-resource" and "root_metadata" in fake.mode:
                    # Metadata for the MCP URL at the origin root: RFC 9728 does not let a client look here.
                    return self._send(200, fake.metadata())
                if parts.path == "/challenge-metadata":
                    return self._send(200, fake.metadata(fake.challenge_resource))
                if parts.path == "/.well-known/oauth-authorization-server":
                    doc = {"issuer": "http://127.0.0.1:1" if "as_wrong_issuer" in fake.mode else fake.base,
                           "authorization_endpoint": f"{fake.base}/authorize",
                           "token_endpoint": f"{fake.base}/token", "registration_endpoint": f"{fake.base}/register",
                           "code_challenge_methods_supported": ["S256"]}
                    for mode, methods in (("pkce_absent", None), ("pkce_plain", ["plain"]), ("pkce_malformed", "S256")):
                        if mode in fake.mode:
                            doc["code_challenge_methods_supported"] = methods
                    doc = {k: v for k, v in doc.items() if v is not None}
                    if "no_iss_support" not in fake.mode:
                        doc["authorization_response_iss_parameter_supported"] = True
                    return self._send(200, doc)
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
                    answer = {"code": code, "state": state, "iss": iss}
                    if "no_iss" in fake.mode:
                        del answer["iss"]
                    location = q["redirect_uri"] + "?" + urlencode(answer)
                    return self._send(302, headers={"Location": location})
                return self._send(404, {"error": "not_found"})

            def do_POST(self):  # noqa: N802
                self._record()
                parts = urlsplit(self.path)
                fake.post_paths.append(parts.path)
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
                        return self._send(200, fake._token_response(form["client_id"], request["scope"]))
                    if form.get("grant_type") == "refresh_token":
                        fake.refresh_calls += 1
                        client = fake.refresh.pop(form.get("refresh_token"), None)  # rotation: single use
                        if client is None or "refresh_fails" in fake.mode:
                            return self._send(400, {"error": "invalid_grant"})
                        return self._send(200, fake._token_response(client, form.get("scope", SCOPE)))
                    return self._send(400, {"error": "unsupported_grant_type"})
                if parts.path == "/mcp":
                    # An MCP endpoint without a token: 401, and in "challenge" mode it names its metadata.
                    fake.mcp_posts += 1
                    if "challenge" in fake.mode:
                        named = fake.challenge_url or f"{fake.base}/challenge-metadata"
                        return self._send(401, {"error": "invalid_token"}, headers={
                            "WWW-Authenticate": f'Bearer error="invalid_token", resource_metadata="{named}"'})
                    return self._send(401, {"error": "invalid_token"}, headers={"WWW-Authenticate": "Bearer"})
                if parts.path == "/resolve":
                    if "redirect" in fake.mode:
                        return self._send(302, headers={"Location": f"{fake.base}/elsewhere"})
                    if "resolve_hangup" in fake.mode:
                        self.close_connection = True  # no answer at all: the server is unreachable
                        return
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
        # The fake server is on loopback: the operator opts in to local mode (D11).
        values = dict(destination=str(self.dest), token_cache=str(self.cache), open_browser=follow,
                      authorization_timeout=10, timeout=5, allow_local=True)
        values.update(overrides)
        return ResolveConfig(**values)

    def run_materialize(self, refs=None, agreed=AGREED, issuer=None, mcp_url=None, **overrides):
        return materialize(issuer=issuer or self.server.issuer, references=refs or [self.alice, self.bob],
                           provenance=self.store, agreed=agreed, config=self.config(**overrides),
                           sentinels=self.sentinels, agent_token=AGENT_TOKEN, mcp_url=mcp_url)

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
        self.server.prm_extra = self.server.discovery(resolve_scope="custom.resolve")
        report = self.run_materialize()
        self.assertTrue(report.materialized, report.failure)
        self.assertEqual(self.server.authorize_requests[0]["scope"], "custom.resolve")
        self.assertEqual(len(self.server.resolve_batches), 1)
        # MCP order: one probe of the MCP URL without a challenge, then the path-inserted URL, no other URL.
        self.assertEqual(self.server.mcp_posts, 1)
        self.assertIn("/.well-known/oauth-protected-resource/mcp", self.server.get_paths)
        self.assertNotIn("/.well-known/oauth-protected-resource", self.server.get_paths)

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

    def test_the_default_configuration_has_no_local_mode(self):
        # D11: a configuration without the option sends nothing to the loopback fake server.
        config = ResolveConfig(destination=str(self.dest), token_cache=str(self.cache), open_browser=follow,
                               authorization_timeout=10, timeout=5)
        report = materialize(issuer=self.server.issuer, references=[self.alice], provenance=self.store,
                             agreed=AGREED, config=config, sentinels=self.sentinels, agent_token=AGENT_TOKEN)
        self.assert_nothing_written(report)
        self.assertEqual(report.failure, "resolution failed: forbidden_target")
        self.assertEqual((self.server.get_paths, self.server.authorize_requests), ([], []))

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
        self.server.prm_extra = self.server.discovery(resolve_endpoint="http://127.0.0.1:1/resolve")
        report = self.run_materialize()
        self.assert_nothing_written(report)
        self.assertEqual(report.failure, "resolution failed: cross_origin_endpoint")

    def test_a_configured_cross_origin_endpoint_is_refused(self):
        # SC-04: an operator-configured endpoint on another origin gets no resolver token either.
        report = self.run_materialize(resolve_endpoint="http://127.0.0.1:1/resolve")
        self.assert_nothing_written(report)
        self.assertEqual(report.failure, "resolution failed: cross_origin_endpoint")
        self.assertEqual((self.server.authorize_requests, self.server.resolve_batches), ([], []))

    def test_an_unreachable_resolve_endpoint_writes_nothing(self):
        self.dest.write_text("before\n")
        self.server.mode.add("resolve_hangup")
        report = self.run_materialize()
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

    # -- RFC 9728 discovery: two mechanisms only (SC-01)

    def test_metadata_named_in_the_www_authenticate_challenge_is_used(self):
        self.server.mode |= {"no_path_metadata", "challenge"}
        report = self.run_materialize()
        self.assertTrue(report.materialized, report.failure)
        self.assertEqual(self.server.mcp_posts, 1)
        self.assertIn("/challenge-metadata", self.server.get_paths)
        self.assertNotIn("/.well-known/oauth-protected-resource", self.server.get_paths)

    def test_the_challenge_comes_before_the_well_known_url(self):
        # MCP order: the resource_metadata URL of the challenge first. The path-inserted
        # document here names another resource; the host must not read it.
        self.server.mode.add("challenge")
        self.server.prm_resource = "https://other.example/mcp"
        self.server.challenge_resource = self.server.issuer
        report = self.run_materialize()
        self.assertTrue(report.materialized, report.failure)
        self.assertNotIn("/.well-known/oauth-protected-resource/mcp", self.server.get_paths)

    def test_a_parent_resource_gets_no_challenge_probe_of_the_mcp_url(self):
        # The challenge names metadata for the MCP URL, not for a parent resource: no probe at all.
        self.server.mode |= {"challenge", "root_metadata"}
        self.server.prm_resource = self.server.base
        self.store = ProvenanceStore()
        self.observe(self.alice, self.bob, issuer=self.server.base)
        report = self.run_materialize(issuer=self.server.base, mcp_url=self.server.issuer)
        self.assertTrue(report.materialized, report.failure)
        self.assertEqual(self.server.mcp_posts, 0)
        self.assertNotIn("/", self.server.post_paths)

    def test_without_metadata_the_host_stops_unless_the_operator_says_there_is_none(self):
        self.server.mode.add("no_path_metadata")
        configured = dict(resolve_endpoint=f"{self.server.base}/resolve", authorization_server=self.server.base)
        report = self.run_materialize(**configured)
        self.assert_nothing_written(report)
        self.assertEqual(report.failure, "resolution failed: no_metadata")
        self.assertEqual(self.server.authorize_requests, [])
        report = self.run_materialize(no_metadata=True, **configured)
        self.assertTrue(report.materialized, report.failure)
        self.assertEqual(len(report.non_conformant), 1)
        self.assertIn("not SC-01 or SC-02 conformant", report.non_conformant[0])

    def test_a_challenge_url_without_a_document_is_not_a_server_without_metadata(self):
        # Opus round 3, L2: the challenge says that metadata exists, so the option does not apply.
        self.server.mode |= {"no_path_metadata", "challenge"}
        self.server.challenge_url = f"{self.server.base}/missing-metadata"
        configured = dict(resolve_endpoint=f"{self.server.base}/resolve", authorization_server=self.server.base)
        for flag in (False, True):
            with self.subTest(no_metadata=flag):
                report = self.run_materialize(no_metadata=flag, **configured)
                self.assert_nothing_written(report)
                self.assertEqual(report.failure, "resolution failed: metadata_unavailable")
        self.assertEqual((self.server.authorize_requests, self.server.resolve_batches), ([], []))

    def test_unreachable_metadata_fails_closed(self):
        # The resource does not answer. That is not "no metadata": without the flag the host stops.
        issuer = "http://127.0.0.1:1/mcp"
        self.store = ProvenanceStore()
        self.observe(self.alice, self.bob, issuer=issuer)
        configured = dict(resolve_endpoint="http://127.0.0.1:1/resolve", authorization_server=self.server.base)
        configured["local_origins"] = (self.server.base,)
        report = self.run_materialize(issuer=issuer, **configured)
        self.assert_nothing_written(report)
        self.assertEqual(report.failure, "resolution failed: unreachable")
        self.assertEqual(self.server.authorize_requests, [])
        # With the flag the host goes on into configuration mode (and fails later at the endpoint).
        report = self.run_materialize(issuer=issuer, no_metadata=True, **configured)
        self.assertEqual(len(self.server.authorize_requests), 1)

    def test_a_resource_with_a_query_or_a_trailing_slash_keeps_it(self):
        # RFC 9728 section 3.1: the well-known string goes between the host and the path and query.
        for path, target in (("/mcp?tenant=a", "/.well-known/oauth-protected-resource/mcp?tenant=a"),
                             ("/mcp/", "/.well-known/oauth-protected-resource/mcp/")):
            with self.subTest(path=path):
                issuer = self.server.base + path
                self.server.prm_resource = issuer
                self.server.get_targets.clear()
                self.store = ProvenanceStore()
                self.observe(self.alice, self.bob, issuer=issuer)
                self.dest.unlink(missing_ok=True)
                report = self.run_materialize(issuer=issuer)
                self.assertTrue(report.materialized, report.failure)
                self.assertIn(target, self.server.get_targets)
                self.assertEqual(self.server.authorize_requests[-1]["resource"], issuer)

    def test_challenge_metadata_for_another_resource_is_refused(self):
        # RFC 9728 section 3.3: the resource must be the URL the request went to, not its parent.
        self.server.mode |= {"no_path_metadata", "challenge"}
        self.server.challenge_resource = self.server.base
        report = self.run_materialize()
        self.assert_nothing_written(report)
        self.assertEqual(report.failure, "resolution failed: wrong_issuer")

    def test_an_insecure_challenge_metadata_url_is_refused(self):
        self.server.mode |= {"no_path_metadata", "challenge"}
        self.server.challenge_url = "http://metadata.example/challenge-metadata"
        report = self.run_materialize()
        self.assert_nothing_written(report)
        self.assertEqual(report.failure, "resolution failed: insecure_url")

    def test_root_metadata_is_not_a_fallback_for_a_resource_with_a_path(self):
        # The origin root holds a document that names the MCP URL, but no mechanism of RFC 9728 points there.
        self.server.mode |= {"no_path_metadata", "root_metadata"}
        report = self.run_materialize()
        self.assert_nothing_written(report)
        self.assertEqual(report.failure, "resolution failed: no_metadata")
        self.assertNotIn("/.well-known/oauth-protected-resource", self.server.get_paths)
        self.assertEqual((self.server.authorize_requests, self.server.resolve_batches), ([], []))

    # -- the discovery object (SC-02): complete, typed, with both profiles, or refused

    def test_a_discovery_object_without_a_mandatory_member_is_refused(self):
        for member in ("resolve_endpoint", "resolve_scope", "resolver_profiles", "sink_profiles"):
            with self.subTest(missing=member):
                self.server.prm_extra = self.server.discovery(**{member: None})
                report = self.run_materialize()
                self.assert_nothing_written(report)
                self.assertEqual(report.failure, "resolution failed: malformed_discovery")
        self.assertEqual((self.server.authorize_requests, self.server.resolve_batches), ([], []))

    def test_a_discovery_object_with_a_malformed_member_is_refused(self):
        malformed = [("resolve_endpoint", 123), ("resolve_endpoint", ""), ("resolve_scope", ""),
                     ("resolve_scope", ["sensitive-references.resolve"]),
                     ("resolver_profiles", "oauth-resolver-1"), ("sink_profiles", ["local-file-1", 1])]
        for member, value in malformed:
            with self.subTest(malformed=member, value=value):
                self.server.prm_extra = self.server.discovery(**{member: value})
                report = self.run_materialize()
                self.assert_nothing_written(report)
                self.assertEqual(report.failure, "resolution failed: malformed_discovery")
        with self.subTest(malformed="the object itself"):
            self.server.prm_extra = "on"
            report = self.run_materialize()
            self.assert_nothing_written(report)
            self.assertEqual(report.failure, "resolution failed: malformed_discovery")
        self.assertEqual((self.server.authorize_requests, self.server.resolve_batches), ([], []))

    def test_a_discovery_object_without_the_negotiated_profiles_is_refused(self):
        for member in ("resolver_profiles", "sink_profiles"):
            with self.subTest(member=member):
                self.server.prm_extra = self.server.discovery(**{member: ["another-profile-1"]})
                report = self.run_materialize()
                self.assert_nothing_written(report)
                self.assertEqual(report.failure, "resolution failed: profile_not_offered")
        self.assertEqual((self.server.authorize_requests, self.server.resolve_batches), ([], []))

    def test_a_configured_endpoint_does_not_excuse_a_bad_discovery_object(self):
        for extra, code in ((self.server.discovery(resolve_scope=None), "malformed_discovery"),
                            (self.server.discovery(sink_profiles=[]), "profile_not_offered")):
            with self.subTest(code=code):
                self.server.prm_extra = extra
                report = self.run_materialize(resolve_endpoint=f"{self.server.base}/resolve", resolve_scope=SCOPE)
                self.assert_nothing_written(report)
                self.assertEqual(report.failure, f"resolution failed: {code}")

    def test_a_configured_scope_replaces_the_discovered_scope(self):
        self.server.prm_extra = self.server.discovery(resolve_scope="custom.resolve")
        report = self.run_materialize(resolve_scope=SCOPE)
        self.assertTrue(report.materialized, report.failure)
        self.assertEqual(self.server.authorize_requests[0]["scope"], SCOPE)

    def test_metadata_without_a_discovery_object_stops_the_host(self):
        # Codex round 3, M1: an absent object stops resolution like an incomplete one,
        # also when an endpoint is configured.
        self.server.prm_extra = None
        for configured in ({}, {"resolve_endpoint": f"{self.server.base}/resolve", "resolve_scope": SCOPE}):
            with self.subTest(configured=sorted(configured)):
                report = self.run_materialize(**configured)
                self.assert_nothing_written(report)
                self.assertEqual(report.failure, "resolution failed: no_discovery_object")
        self.assertEqual((self.server.authorize_requests, self.server.resolve_batches), ([], []))

    def test_without_a_discovery_object_configuration_mode_needs_the_option_and_is_not_conformant(self):
        self.server.prm_extra = None
        report = self.run_materialize(no_discovery_object=True)
        self.assert_nothing_written(report)
        self.assertEqual(report.failure, "resolution failed: no_resolve_endpoint")
        report = self.run_materialize(no_discovery_object=True, resolve_endpoint=f"{self.server.base}/resolve")
        self.assertTrue(report.materialized, report.failure)
        self.assertEqual(self.server.authorize_requests[0]["scope"], SCOPE)
        self.assertEqual(len(report.non_conformant), 1)
        self.assertIn("not SC-02 conformant", report.non_conformant[0])

    def test_a_conformant_run_has_no_deviation(self):
        report = self.run_materialize()
        self.assertTrue(report.materialized, report.failure)
        self.assertEqual(report.non_conformant, [])
        # The option changes nothing when the object is present.
        self.dest.unlink()
        report = self.run_materialize(no_discovery_object=True)
        self.assertEqual(report.non_conformant, [])

    # -- RFC 8414 and PKCE support of the authorization server (D10)

    def test_authorization_server_metadata_without_s256_is_refused(self):
        for mode in ("pkce_absent", "pkce_plain", "pkce_malformed"):
            with self.subTest(mode=mode):
                self.server.mode = {mode}
                report = self.run_materialize()
                self.assert_nothing_written(report)
                self.assertEqual(report.failure, "resolution failed: no_pkce_s256")
        self.assertEqual(self.server.authorize_requests, [])

    def test_authorization_server_metadata_for_another_issuer_is_refused(self):
        self.server.mode.add("as_wrong_issuer")
        report = self.run_materialize()
        self.assert_nothing_written(report)
        self.assertEqual(report.failure, "resolution failed: wrong_authorization_server")
        self.assertEqual(self.server.authorize_requests, [])

    # -- RFC 9207 (SC-08)

    def test_a_callback_without_iss_is_refused_when_the_server_advertises_iss(self):
        self.server.mode.add("no_iss")
        report = self.run_materialize()
        self.assert_nothing_written(report)
        self.assertEqual(report.failure, "resolution failed: issuer_mismatch")
        self.assertEqual(self.server.resolve_batches, [])

    def test_a_callback_without_iss_is_accepted_when_the_server_does_not_advertise_iss(self):
        self.server.mode |= {"no_iss", "no_iss_support"}
        report = self.run_materialize()
        self.assertTrue(report.materialized, report.failure)

    def test_a_wrong_iss_is_refused_also_when_the_server_does_not_advertise_iss(self):
        self.server.mode |= {"wrong_iss", "no_iss_support"}
        report = self.run_materialize()
        self.assert_nothing_written(report)
        self.assertEqual(report.failure, "resolution failed: issuer_mismatch")

    def test_without_the_negotiated_profiles_nothing_is_sent(self):
        for agreed in (None, NegotiatedSensitiveReferences("1", frozenset(), frozenset({"local-file-1"})),
                       NegotiatedSensitiveReferences("1", frozenset({"oauth-resolver-1"}), frozenset())):
            with self.subTest(agreed=agreed):
                report = self.run_materialize(agreed=agreed)
                self.assert_nothing_written(report)
        self.assertEqual(self.server.authorize_requests, [])
        self.assertEqual(self.server.resolve_batches, [])


def _forward(method: str, url: str, body: bytes, headers: dict) -> tuple[int, list, bytes]:
    from urllib.error import HTTPError
    from urllib.request import HTTPRedirectHandler, Request, build_opener

    class NoRedirect(HTTPRedirectHandler):
        def redirect_request(self, *args):
            return None

    request = Request(url, data=body or None, method=method, headers=headers)
    try:
        with build_opener(NoRedirect).open(request, timeout=10) as response:
            status, answer, data = response.status, response.headers, response.read()
    except HTTPError as error:
        status, answer, data = error.code, error.headers, error.read()
    kept = [(k.lower().encode(), v.encode()) for k, v in answer.items()
            if k.lower() in ("content-type", "location", "www-authenticate")]
    return status, kept, data


def _serve_mcp(tool_text: str, settings: dict, fallback: str):
    """A real MCP SDK 2.x server on a loopback port that advertises ``settings``.

    Every path other than ``/mcp`` goes to ``fallback`` (the fake server), so the
    metadata and the resolve endpoint are on the origin of the MCP URL (SC-01, SC-04).
    """
    import asyncio
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
    inner = server.streamable_http_app()

    async def app(scope, receive, send):
        if scope["type"] != "http" or scope["path"] == "/mcp":
            return await inner(scope, receive, send)
        body = b""
        while True:
            message = await receive()
            body += message.get("body", b"")
            if not message.get("more_body"):
                break
        query = scope["query_string"].decode()
        url = fallback + scope["path"] + (f"?{query}" if query else "")
        headers = {k.decode(): v.decode() for k, v in scope["headers"]
                   if k.lower() in (b"authorization", b"content-type", b"accept")}
        status, kept, data = await asyncio.to_thread(_forward, scope["method"], url, body, headers)
        await send({"type": "http.response.start", "status": status, "headers": kept})
        await send({"type": "http.response.body", "body": data})

    runner = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
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

    def run_host(self, settings, *extra, parent=False, strict=False):
        runner, url = _serve_mcp(f"mail {self.alice}", settings, self.fake.base)
        origin = url.rsplit("/", 1)[0]
        # The fake metadata names the MCP URL (or, with ``parent``, its origin) and an endpoint on that origin.
        self.fake.prm_resource = origin if parent else url
        self.fake.prm_extra = self.fake.discovery(resolve_endpoint=f"{origin}/resolve")
        if parent:
            self.fake.mode.add("root_metadata")
        extra = [a.replace("{origin}", origin) for a in extra]
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
                "--resolver-token-cache", str(self.dir / "tokens.json"), "--timeout", "10",
                # Local mode (D11): the MCP server and the fake authorization server are on loopback.
                *([] if strict else ["--allow-local-targets", "--local-origin", self.fake.base]), *extra])
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
        self.assertEqual(report["materialization"]["non_conformant"], [])
        self.assertEqual(self.dest.read_text(), "alice@example.com\n")
        for secret in (self.alice, "alice@example.com", AGENT_TOKEN, *self.fake.access, *self.fake.refresh):
            self.assertNotIn(secret, output)
        self.assertNotIn(f"Bearer {AGENT_TOKEN}", self.fake.authorization_headers)
        # SC-01 and SC-02 without options: metadata of the MCP URL, endpoint from discovery on its origin.
        self.assertIn("/.well-known/oauth-protected-resource/mcp", self.fake.get_paths)
        self.assertEqual(len(self.fake.resolve_batches), 1)

    def test_without_the_local_option_a_loopback_server_gets_no_request(self):
        # D11: no automatic exception for a loopback MCP URL.
        code, output = self.run_host(self.PROFILES, strict=True)
        report = json.loads(output)

        self.assertEqual(code, 1)
        self.assertEqual(report["materialization"]["failure"], "resolution failed: forbidden_target")
        self.assertFalse(self.dest.exists())
        self.assertEqual((self.fake.get_paths, self.fake.authorize_requests, self.fake.resolve_batches),
                         ([], [], []))

    def test_a_configured_parent_resource_is_the_issuer(self):
        # The server publishes its metadata for the origin, not for /mcp.
        code, output = self.run_host(self.PROFILES, "--resource", "{origin}", parent=True)
        report = json.loads(output)

        self.assertEqual(code, 0, report["failures"])
        self.assertEqual(self.dest.read_text(), "alice@example.com\n")
        # Deviation P16: the report says that the run is not conformant.
        self.assertEqual(len(report["materialization"]["non_conformant"]), 1)
        self.assertIn("P16", report["materialization"]["non_conformant"][0])

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


class IssuerExactStringTests(unittest.TestCase):
    """SC-01: the host keeps the issuer string as given and compares it as an exact string.

    The metadata comes from a stub, so that the near misses can use any host, scheme and port.
    """

    ISSUER = "https://mcp.example.com/mcp"

    def discover(self, issuer: str, metadata_resource: str):
        from sensitive_references import resolver_client

        def fake_http_json(method, url, **_):
            return 200, {"resource": metadata_resource, "authorization_servers": ["https://as.example.com"]}

        original, resolver_client.http_json = resolver_client.http_json, fake_http_json
        try:
            return resolver_client.discover_protected_resource(issuer, use_challenge=False)
        finally:
            resolver_client.http_json = original

    def test_the_issuer_string_is_kept_as_given(self):
        for url in ("https://MCP.Example.com:443/mcp/", "HTTPS://MCP.example.com/mcp?x=1",
                    "https://mcp.example.com/a%2Fb", "https://mcp.example.com/mcp?tenant=a"):
            with self.subTest(url=url):
                self.assertEqual(mcp_host.issuer_identity(url), url)

    def test_a_url_with_user_information_or_a_fragment_is_no_issuer(self):
        for url in ("https://user:pw@mcp.example.com/mcp", "https://user@mcp.example.com/mcp",
                    "https://mcp.example.com/mcp#f", "https://mcp.example.com/mcp#"):
            with self.subTest(url=url):
                with self.assertRaises(ValueError):
                    mcp_host.issuer_identity(url)

    def test_the_report_holds_no_user_information_and_no_query(self):
        self.assertEqual(mcp_host.public_endpoint("HTTPS://user:pw@MCP.example.com/mcp?x=1#f"),
                         "HTTPS://MCP.example.com/mcp")

    def test_identical_metadata_is_accepted(self):
        # Upper case in the scheme or the host is accepted when the metadata names the identical string.
        for issuer in (self.ISSUER, "HTTPS://MCP.example.com/mcp"):
            with self.subTest(issuer=issuer):
                self.assertEqual(self.discover(issuer, issuer).resource, issuer)

    def test_the_well_known_url_follows_rfc_9728_section_3_1(self):
        from sensitive_references.resolver_client import protected_resource_metadata_url

        prefix = "https://mcp.example.com/.well-known/oauth-protected-resource"
        cases = {"https://mcp.example.com/mcp": prefix + "/mcp",
                 "https://mcp.example.com/mcp?tenant=a": prefix + "/mcp?tenant=a",
                 "https://mcp.example.com/mcp/": prefix + "/mcp/",
                 "https://mcp.example.com": prefix,
                 "https://mcp.example.com/": prefix,
                 "https://mcp.example.com/?tenant=a": prefix + "?tenant=a"}
        for resource, expected in cases.items():
            with self.subTest(resource=resource):
                self.assertEqual(protected_resource_metadata_url(resource), expected)

    def test_a_resource_with_a_fragment_is_refused(self):
        with self.assertRaises(ResolverClientError) as caught:
            self.discover("https://mcp.example.com/mcp#f", "https://mcp.example.com/mcp#f")
        self.assertEqual(caught.exception.code, "invalid_resource")

    def test_a_near_miss_of_the_issuer_is_refused(self):
        near_misses = {
            "trailing slash": "https://mcp.example.com/mcp/",
            "parent path": "https://mcp.example.com",
            "parent path with slash": "https://mcp.example.com/",
            "host case": "https://MCP.example.com/mcp",
            "explicit default port": "https://mcp.example.com:443/mcp",
            "scheme case": "HTTPS://mcp.example.com/mcp",
            "percent-encoding": "https://mcp.example.com/%6Dcp",
        }
        for name, resource in near_misses.items():
            with self.subTest(name):
                with self.assertRaises(ResolverClientError) as caught:
                    self.discover(self.ISSUER, resource)
                self.assertEqual(caught.exception.code, "wrong_issuer")

    def test_an_issuer_with_upper_case_is_not_lowered_to_match(self):
        for issuer in ("https://MCP.example.com/mcp", "https://mcp.example.com:443/mcp"):
            with self.subTest(issuer=issuer):
                with self.assertRaises(ResolverClientError) as caught:
                    self.discover(issuer, self.ISSUER)
                self.assertEqual(caught.exception.code, "wrong_issuer")


class AuthorizationServerWellKnownTests(unittest.TestCase):
    def test_rfc_8414_removes_a_terminating_slash_of_the_issuer(self):
        # Opus round 3, M1: RFC 8414 section 3.1, unlike RFC 9728 for a resource.
        from sensitive_references.resolver_client import authorization_server_metadata_urls

        cases = {
            "https://as.example/realms/x/": [
                "https://as.example/.well-known/oauth-authorization-server/realms/x",
                "https://as.example/.well-known/openid-configuration/realms/x",
                "https://as.example/realms/x/.well-known/openid-configuration"],
            "https://as.example/realms/x": [
                "https://as.example/.well-known/oauth-authorization-server/realms/x",
                "https://as.example/.well-known/openid-configuration/realms/x",
                "https://as.example/realms/x/.well-known/openid-configuration"],
            "https://as.example/": [
                "https://as.example/.well-known/oauth-authorization-server",
                "https://as.example/.well-known/openid-configuration"],
        }
        for issuer, expected in cases.items():
            with self.subTest(issuer=issuer):
                self.assertEqual(authorization_server_metadata_urls(issuer), expected)


class _Answer:
    def __init__(self, status, body, headers):
        self.status, self.headers, self._body = status, headers, body

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class FetchPolicyTests(unittest.TestCase):
    """RFC 9728 section 7.7: no request to a non-public target for an MCP URL on a public address.

    A stub replaces DNS, and a fake opener replaces the network. No request leaves the machine.
    """

    MCP = "https://mcp.example.com/mcp"
    # Globally reachable stand-ins (the documentation ranges 192.0.2.0/24 and 2001:db8::/32 are not).
    DNS = {"mcp.example.com": ["20.0.0.10"], "as.example.com": ["20.0.0.20", "2a00:1::20"],
           "internal.example.com": ["10.0.0.5"], "mixed.example.com": ["20.0.0.30", "192.168.1.1"],
           "v6local.example.com": ["fd00::5"], "local-mcp.example.com": ["10.0.0.9"],
           "mixed-mcp.example.com": ["20.0.0.40", "127.0.0.1"], "docs.example.com": ["192.0.2.10"]}

    def setUp(self):
        from email.message import Message
        from sensitive_references import resolver_client

        self.rc = resolver_client
        self.requests: list[str] = []
        self.routes: dict[str, tuple[int, dict, dict]] = {}
        test = self

        def lookup(host):
            if host not in test.DNS:
                raise OSError("no such name")
            return list(test.DNS[host])

        class Opener:
            def open(self, request, timeout=None):
                from urllib.error import HTTPError
                import io

                url = request.full_url
                test.requests.append(url)
                status, headers, body = test.routes.get(url, (404, {}, {"error": "not_found"}))
                message = Message()
                for k, v in headers.items():
                    message[k] = v
                data = json.dumps(body).encode()
                if status >= 400:
                    raise HTTPError(url, status, "error", message, io.BytesIO(data))
                return _Answer(status, data, message)

        saved = (resolver_client._lookup, resolver_client._OPENER)
        resolver_client._lookup, resolver_client._OPENER = lookup, Opener()
        self.addCleanup(setattr, resolver_client, "_lookup", saved[0])
        self.addCleanup(setattr, resolver_client, "_OPENER", saved[1])

    def challenge(self, url):
        self.routes[self.MCP] = (401, {"WWW-Authenticate": f'Bearer resource_metadata="{url}"'}, {})

    def metadata(self, servers=("https://as.example.com",), at=None):
        url = at or "https://mcp.example.com/.well-known/oauth-protected-resource/mcp"
        self.routes[url] = (200, {}, {"resource": self.MCP, "authorization_servers": list(servers),
                                      "sensitive_references": {
                                          "resolve_endpoint": "https://mcp.example.com/resolve",
                                          "resolve_scope": SCOPE, "resolver_profiles": ["oauth-resolver-1"],
                                          "sink_profiles": ["local-file-1"]}})

    def as_metadata(self, **endpoints):
        doc = {"issuer": "https://as.example.com", "authorization_endpoint": "https://as.example.com/authorize",
               "token_endpoint": "https://as.example.com/token",
               "registration_endpoint": "https://as.example.com/register",
               "code_challenge_methods_supported": ["S256"]}
        doc.update(endpoints)
        self.routes["https://as.example.com/.well-known/oauth-authorization-server"] = (200, {}, doc)

    def refused(self, call):
        with self.assertRaises(ResolverClientError) as caught:
            call()
        self.assertEqual(caught.exception.code, "forbidden_target")

    def test_the_non_public_ranges(self):
        # Not globally reachable (IANA special-purpose registries), multicast, site-local, or an embedded
        # IPv4 address that is not globally reachable (IPv4-mapped, IPv4-compatible, NAT64, 6to4).
        non_public = ["127.0.0.1", "127.8.9.1", "10.1.2.3", "172.16.0.1", "172.31.255.254", "192.168.0.1",
                      "169.254.169.254", "0.0.0.0", "224.0.0.1", "239.1.1.1", "255.255.255.255", "240.0.0.1",
                      "100.64.0.1", "::1", "::", "fd00::1", "fc00::1", "fe80::1%en0", "ff02::1", "ff0e::1",
                      "::ffff:127.0.0.1", "::ffff:10.0.0.1", "::ffff:169.254.169.254",
                      "192.0.2.10", "198.51.100.7", "203.0.113.5", "2001:db8::1", "::ffff:192.0.2.1",
                      "198.18.0.1", "192.0.0.8", "64:ff9b::a00:1", "64:ff9b::7f00:1", "64:ff9b:1::1",
                      "2002:a00:1::1", "::10.0.0.1", "::127.0.0.1", "fec0::1", "2001::1"]
        public = ["172.32.0.1", "100.128.0.1", "20.0.0.10", "2a00:1::20", "192.0.0.9", "64:ff9b::1400:a", "::ffff:20.0.0.10"]
        for address in non_public:
            with self.subTest(address=address):
                self.assertTrue(self.rc.non_public_address(address))
        for address in public:
            with self.subTest(address=address):
                self.assertFalse(self.rc.non_public_address(address))

    def test_the_most_specific_registry_entry_decides(self):
        # SC-01: an address in a broad "Globally Reachable: False" block and in a more specific "True"
        # entry is public. IPv4 192.0.0.0/24 holds 192.0.0.9/32 and 192.0.0.10/32; IPv6 2001::/23 holds
        # 2001:1::1/128, 2001:3::/32, 2001:4:112::/48 and 2001:20::/28.
        cases = {"192.0.0.8": True, "192.0.0.9": False, "192.0.0.10": False, "192.0.0.11": True,
                 "2001:2::1": True, "2001:1::1": False, "2001:1::4": True, "2001:3::1": False,
                 "2001:4:112::1": False, "2001:4:113::1": True, "2001:20::1": False}
        for address, non_public in cases.items():
            with self.subTest(address=address):
                self.assertEqual(self.rc.non_public_address(address), non_public)

    def test_three_registry_entries_that_the_python_tables_do_not_follow(self):
        # IANA 2026-10-27: 5f00::/16 (SRv6 SIDs) False, 192.88.99.2/32 (6a44 relay anycast) False in the
        # deprecated 192.88.99.0/24 block without a value, 2001:1::3/128 (DNS-SD SRP anycast) True.
        cases = {"5f00::1": True, "192.88.99.2": True, "192.88.99.1": True, "2001:1::3": False,
                 "2001:1::4": True, "5eff::1": False}
        for address, non_public in cases.items():
            with self.subTest(address=address):
                self.assertEqual(self.rc.non_public_address(address), non_public)

    def test_the_embedded_ipv4_address(self):
        # The registry marks 6to4 and Teredo "N/A", which the fetch policy counts as non-public;
        # the unwrap still judges the embedded IPv4 address.
        cases = {"::ffff:10.0.0.1": "10.0.0.1", "::10.0.0.1": "10.0.0.1", "64:ff9b::a00:1": "10.0.0.1",
                 "2002:a00:1::1": "10.0.0.1", "2a00:1::20": None, "::1": None, "::": None, "10.0.0.1": None}
        import ipaddress
        for address, expected in cases.items():
            with self.subTest(address=address):
                embedded = self.rc._embedded_ipv4(ipaddress.ip_address(address))
                self.assertEqual(None if embedded is None else str(embedded), expected)

    def test_a_public_resource_discovers_normally(self):
        self.metadata()
        self.as_metadata()
        policy = self.rc.FetchPolicy(self.MCP)
        found = self.rc.discover_protected_resource(self.MCP, policy=policy)
        self.assertEqual(found.authorization_servers, ("https://as.example.com",))
        server = self.rc.discover_authorization_server("https://as.example.com", policy=policy)
        self.assertEqual(server.token_endpoint, "https://as.example.com/token")
        self.assertFalse(policy.local)

    def test_a_loopback_or_private_challenge_url_is_refused_before_a_request(self):
        for target in ("http://127.0.0.1:9/metadata", "https://[::1]/metadata", "https://10.0.0.5/metadata",
                       "https://169.254.169.254/latest", "https://internal.example.com/metadata",
                       "https://mixed.example.com/metadata", "https://v6local.example.com/metadata",
                       "https://unresolvable.example.com/metadata"):
            with self.subTest(target=target):
                self.requests.clear()
                self.challenge(target)
                self.refused(lambda: self.rc.discover_protected_resource(self.MCP))
                self.assertEqual(self.requests, [self.MCP])

    def test_a_non_public_authorization_server_is_refused(self):
        policy = self.rc.FetchPolicy(self.MCP)
        for issuer in ("http://127.0.0.1:8080", "https://[fd00::1]", "https://internal.example.com",
                       "https://192.168.1.1/realms/x"):
            with self.subTest(issuer=issuer):
                self.requests.clear()
                self.refused(lambda: self.rc.discover_authorization_server(issuer, policy=policy))
                self.assertEqual(self.requests, [])

    def test_a_non_public_endpoint_in_authorization_server_metadata_is_refused(self):
        policy = self.rc.FetchPolicy(self.MCP)
        for name, url in (("token_endpoint", "https://10.0.0.7/token"),
                          ("registration_endpoint", "http://127.0.0.1:5000/register"),
                          ("authorization_endpoint", "https://internal.example.com/authorize")):
            with self.subTest(name=name):
                self.as_metadata(**{name: url})
                self.refused(lambda: self.rc.discover_authorization_server("https://as.example.com", policy=policy))
                self.assertNotIn(url, self.requests)

    def test_a_non_public_resolve_endpoint_is_refused_before_a_request(self):
        cache = TokenCache(Path(tempfile.mkdtemp(prefix="sref-ssrf-")) / "tokens.json")
        credential = OAuthResolverCredential(resource=self.MCP, authorization_server="https://as.example.com",
                                             cache=cache, interactive=False)
        cache.store(credential.key, {"client_id": "pre", "access_token": "cached-resolver-token"})
        resolver = OAuthHttpResolver({self.MCP: ResolveEndpoint("https://internal.example.com/resolve",
                                                                credential)})
        self.refused(lambda: resolver.resolve(self.MCP, [make_token("email").token],
                                              SinkContext("local_file", "x", "p")))
        self.assertEqual(self.requests, [])

    def test_the_host_stops_at_a_loopback_authorization_server_of_a_public_mcp_url(self):
        self.routes[self.MCP] = (401, {"WWW-Authenticate": "Bearer"}, {})
        self.metadata(servers=["http://127.0.0.1:1"])
        store = ProvenanceStore()
        token = make_token("email").token
        store.observe_mcp_result(self.MCP, extension_negotiated=True, result={"texts": [token]})
        dest = Path(tempfile.mkdtemp(prefix="sref-ssrf-")) / "out.txt"
        report = materialize(issuer=self.MCP, references=[token], provenance=store, agreed=AGREED,
                             config=ResolveConfig(destination=str(dest), open_browser=follow, timeout=5),
                             sentinels=[], agent_token=AGENT_TOKEN, mcp_url=self.MCP)
        self.assertEqual(report.failure, "resolution failed: forbidden_target")
        self.assertFalse(dest.exists())
        self.assertFalse([url for url in self.requests if "127.0.0.1" in url])

    def test_a_non_public_mcp_url_gives_no_exception_without_the_operator_option(self):
        for mcp_url in ("http://127.0.0.1:8080/mcp", "https://local-mcp.example.com/mcp", "https://[fd00::9]/mcp"):
            with self.subTest(mcp_url=mcp_url):
                policy = self.rc.FetchPolicy(mcp_url)
                self.assertFalse(policy.local)
                origin = mcp_url.rsplit("/", 1)[0]
                self.refused(lambda: policy.check(f"{origin}/x", "test"))
                self.refused(lambda: policy.check("http://127.0.0.1:9/x", "test"))

    def test_local_mode_allows_only_the_mcp_origin_and_configured_origins(self):
        for mcp_url in ("http://127.0.0.1:8080/mcp", "https://local-mcp.example.com/mcp", "https://[fd00::9]/mcp"):
            with self.subTest(mcp_url=mcp_url):
                policy = self.rc.FetchPolicy(mcp_url, allow_local=True)
                self.assertTrue(policy.local)
                origin = mcp_url.rsplit("/", 1)[0]
                self.assertEqual(policy.check(f"{origin}/x", "test"), f"{origin}/x")
                # A public target stays allowed.
                self.assertEqual(policy.check("https://as.example.com/x", "test"), "https://as.example.com/x")
                for target in ("http://127.0.0.1:2375/containers", "https://10.0.0.1/admin",
                               "https://internal.example.com/x", "https://[fd00::1]/x",
                               "https://unresolvable.example.com/x"):
                    self.refused(lambda: policy.check(target, "test"))
        policy = self.rc.FetchPolicy("http://127.0.0.1:8080/mcp", allow_local=True,
                                     local_origins=("https://internal.example.com",))
        self.assertEqual(policy.check("https://internal.example.com/x", "test"), "https://internal.example.com/x")
        # Exact origin: another port or scheme of the same host is another origin.
        self.refused(lambda: policy.check("https://internal.example.com:8443/x", "test"))
        self.refused(lambda: policy.check("http://internal.example.com/x", "test"))

    def test_a_loopback_mcp_server_never_reaches_link_local_unspecified_or_multicast(self):
        never = ("http://169.254.169.254", "http://[fe80::1]", "http://[::ffff:169.254.169.254]",
                 "http://0.0.0.0:8080", "http://[::]:8080", "http://224.0.0.251", "http://[ff02::1]",
                 "http://255.255.255.255")
        policy = self.rc.FetchPolicy("http://127.0.0.1:8080/mcp", allow_local=True, local_origins=never)
        self.assertTrue(policy.local)
        for target in never:
            with self.subTest(target=target):
                self.refused(lambda: policy.check(f"{target}/latest/meta-data/", "test"))
        # An MCP server on a link-local address gets local mode, but not its own origin.
        policy = self.rc.FetchPolicy("http://169.254.10.10/mcp", allow_local=True)
        self.refused(lambda: policy.check("http://169.254.10.10/x", "test"))

    def test_mixed_dns_records_of_the_mcp_host_give_no_local_mode(self):
        policy = self.rc.FetchPolicy("https://mixed-mcp.example.com/mcp", allow_local=True)
        self.assertFalse(policy.local)
        for target in ("https://mixed-mcp.example.com/x", "http://127.0.0.1:2375/x",
                       "http://169.254.169.254/latest/meta-data/", "https://10.0.0.1/admin"):
            with self.subTest(target=target):
                self.refused(lambda: policy.check(target, "test"))
        # A documentation address is not globally reachable either: no local mode for a public stand-in.
        self.assertTrue(self.rc.FetchPolicy("https://docs.example.com/mcp", allow_local=True).local)

    def test_the_host_keeps_the_dns_answer_for_the_mcp_host_from_the_connection(self):
        dns = dict(self.DNS)
        self.addCleanup(setattr, self, "DNS", self.DNS)
        self.DNS = dns
        policy = self.rc.FetchPolicy(self.MCP, allow_local=True)
        self.assertFalse(policy.local)
        # Later the name points to loopback: the policy keeps its decision and refuses the target.
        dns["mcp.example.com"] = ["127.0.0.1"]
        self.assertFalse(policy.local)
        self.assertEqual(policy.mcp_addresses, ["20.0.0.10"])
        self.refused(lambda: policy.check("https://mcp.example.com/resolve", "test"))


class NoRedirectNoProxyTests(unittest.TestCase):
    """SC-01 and SC-04: no HTTP client of the host follows a redirect or uses a proxy from the environment.

    Real loopback servers: one answers each request with 302 to the other, which counts what it gets.
    """

    def setUp(self):
        from sensitive_references import resolver_client

        self.rc = resolver_client
        self.hits: dict[str, list] = {"target": [], "redirector": [], "proxy": []}
        self.target = self._serve("target", 200, None)
        self.redirector = self._serve("redirector", 302, f"{self.target}/moved")
        self.proxy = self._serve("proxy", 200, None)
        self.policy = resolver_client.FetchPolicy(f"{self.redirector}/mcp", allow_local=True,
                                                  local_origins=(self.target, self.proxy))

    def _serve(self, name, status, location):
        hits = self.hits[name]

        class Handler(BaseHTTPRequestHandler):
            def _answer(self):
                hits.append((self.command, self.path))
                self.rfile.read(int(self.headers.get("Content-Length") or 0))
                body = b"{}"
                self.send_response(status)
                if location:
                    self.send_header("Location", location)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            do_GET = do_POST = _answer

            def log_message(self, *args):
                pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        return f"http://127.0.0.1:{server.server_address[1]}"

    def test_no_client_follows_a_redirect(self):
        rc, base = self.rc, self.redirector
        # Protected-resource metadata: the challenge probe and the well-known URL.
        self.assertIsNone(rc.discover_protected_resource(f"{base}/mcp", policy=self.policy, timeout=5))
        # Authorization server metadata (discovery).
        with self.assertRaises(ResolverClientError) as caught:
            rc.discover_authorization_server(base, policy=self.policy, timeout=5)
        self.assertEqual(caught.exception.code, "no_authorization_server")
        metadata = rc.AuthorizationServer(issuer=base, authorization_endpoint=f"{base}/authorize",
                                          token_endpoint=f"{base}/token", registration_endpoint=f"{base}/register")
        cache = TokenCache(Path(tempfile.mkdtemp(prefix="sref-redirect-")) / "tokens.json")
        credential = OAuthResolverCredential(resource=f"{base}/mcp", authorization_server=base, cache=cache,
                                             metadata=lambda: metadata, interactive=False, timeout=5,
                                             policy=self.policy)
        # Registration.
        with self.assertRaises(ResolverClientError) as caught:
            credential._register("http://127.0.0.1:1/callback")
        self.assertEqual(caught.exception.code, "registration_failed")
        # Token endpoint (refresh).
        cache.store(credential.key, {"client_id": "c", "refresh_token": "r"})
        with self.assertRaises(ResolverClientError) as caught:
            credential.access_token()
        self.assertEqual(caught.exception.code, "unauthorized")
        # Resolve endpoint.
        cache.store(credential.key, {"client_id": "c", "access_token": "cached-resolver-token"})
        resolver = OAuthHttpResolver({f"{base}/mcp": ResolveEndpoint(f"{base}/resolve", credential)}, timeout=5)
        with self.assertRaises(ResolverClientError):
            resolver.resolve(f"{base}/mcp", [make_token("email").token], SinkContext("local_file", "x", "p"))
        self.assertEqual(self.hits["target"], [])
        self.assertEqual({path.split("?")[0] for _, path in self.hits["redirector"]},
                         {"/mcp", "/.well-known/oauth-protected-resource/mcp",
                          "/.well-known/oauth-authorization-server", "/.well-known/openid-configuration",
                          "/register", "/token", "/resolve"})

    def test_no_client_uses_a_proxy_from_the_environment(self):
        names = ("http_proxy", "HTTP_PROXY", "https_proxy", "HTTPS_PROXY", "no_proxy", "NO_PROXY")
        saved = {name: os.environ.get(name) for name in names}

        def restore():
            for name, value in saved.items():
                if value is None:
                    os.environ.pop(name, None)
                else:
                    os.environ[name] = value

        self.addCleanup(restore)
        for name in names:
            os.environ.pop(name, None)
        os.environ["http_proxy"] = os.environ["HTTP_PROXY"] = self.proxy
        saved_opener = self.rc._OPENER
        self.addCleanup(setattr, self.rc, "_OPENER", saved_opener)
        self.rc._OPENER = self.rc._new_opener()
        status, _ = self.rc.http_json("GET", f"{self.target}/direct", policy=self.policy, timeout=5)
        self.assertEqual(status, 200)
        self.assertEqual(self.hits["proxy"], [])
        self.assertEqual(self.hits["target"], [("GET", "/direct")])


    def _use_real_opener(self):
        saved_opener = self.rc._OPENER
        self.addCleanup(setattr, self.rc, "_OPENER", saved_opener)
        self.rc._OPENER = self.rc._new_opener()

    def test_the_request_connects_to_the_checked_address(self):
        """SC-01: the host resolves the name once. The system resolver does not know the name."""
        self._use_real_opener()
        port = int(self.target.rsplit(":", 1)[1])
        lookups = []

        def lookup(host):
            lookups.append(host)
            return ["127.0.0.1"]

        saved_lookup = self.rc._lookup
        self.addCleanup(setattr, self.rc, "_lookup", saved_lookup)
        self.rc._lookup = lookup
        policy = self.rc.FetchPolicy(f"http://rebind.invalid:{port}/mcp", allow_local=True)
        lookups.clear()
        status, _ = self.rc.http_json("GET", f"http://rebind.invalid:{port}/pinned", policy=policy, timeout=5)
        self.assertEqual(status, 200)
        self.assertEqual(lookups, ["rebind.invalid"])
        self.assertEqual(self.hits["target"], [("GET", "/pinned")])

    def test_a_request_without_a_checked_address_is_refused(self):
        self._use_real_opener()
        from urllib.error import URLError
        from urllib.request import Request

        with self.assertRaises(URLError):
            self.rc._OPENER.open(Request(f"{self.target}/unchecked"), timeout=5)
        self.assertEqual(self.hits["target"], [])

    def test_the_real_opener_verifies_certificates_and_host_names(self):
        import ssl

        handlers = [h for h in self.rc._new_opener().handlers if isinstance(h, self.rc._PinnedHTTPS)]
        self.assertEqual(len(handlers), 1)
        self.assertEqual(handlers[0]._context.verify_mode, ssl.CERT_REQUIRED)
        self.assertTrue(handlers[0]._context.check_hostname)

    def test_the_tls_server_name_is_the_host_name_of_the_url(self):
        # SNI and the host name check of TLS use the name of the URL, the socket goes to the checked address.
        rc = self.rc
        seen = {}

        class Context:
            def wrap_socket(self, sock, server_hostname):
                seen["peer"], seen["name"] = sock.getpeername()[0], server_hostname
                return sock

        port = int(self.target.rsplit(":", 1)[1])
        connection = rc._PinnedHTTPSConnection("as.example.invalid", port, timeout=5, context=Context(),
                                               addresses=["127.0.0.1"])
        self.addCleanup(connection.close)
        connection.connect()
        self.assertEqual(seen, {"peer": "127.0.0.1", "name": "as.example.invalid"})

    def _lookup_returns(self, answer):
        saved_lookup = self.rc._lookup
        self.addCleanup(setattr, self.rc, "_lookup", saved_lookup)
        self.rc._lookup = lambda host: list(answer)

    def test_the_host_tries_each_checked_address(self):
        """A server that listens only on ::1: the first checked address 127.0.0.1 refuses, ::1 answers."""
        import socket as socket_module

        self._use_real_opener()
        hits = []

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                hits.append(self.path)
                self.send_response(200)
                self.send_header("Content-Length", "2")
                self.end_headers()
                self.wfile.write(b"{}")

            def log_message(self, *args):
                pass

        class Server6(ThreadingHTTPServer):
            address_family = socket_module.AF_INET6

        try:
            server = Server6(("::1", 0), Handler)
        except OSError:
            self.skipTest("no IPv6 loopback interface")
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        port = server.server_address[1]
        self._lookup_returns(["127.0.0.1", "::1"])
        policy = self.rc.FetchPolicy(f"http://dual.invalid:{port}/mcp", allow_local=True)
        status, _ = self.rc.http_json("GET", f"http://dual.invalid:{port}/both", policy=policy, timeout=5)
        self.assertEqual(status, 200)
        self.assertEqual(hits, ["/both"])

    def test_each_connection_attempt_gets_the_timeout_of_the_request(self):
        self._use_real_opener()
        attempts = []

        def create_connection(target, timeout=None, source_address=None):
            attempts.append((target[0], timeout))
            raise OSError("refused")

        saved = self.rc.socket.create_connection
        self.addCleanup(setattr, self.rc.socket, "create_connection", saved)
        self.rc.socket.create_connection = create_connection
        self._lookup_returns(["127.0.0.1", "::1"])
        policy = self.rc.FetchPolicy("http://dual.invalid:9/mcp", allow_local=True)
        with self.assertRaises(ResolverClientError) as caught:
            self.rc.http_json("GET", "http://dual.invalid:9/x", policy=policy, timeout=3)
        self.assertEqual(caught.exception.code, "unreachable")
        self.assertEqual(attempts, [("127.0.0.1", 3), ("::1", 3)])



class PinnedTlsTests(unittest.TestCase):
    """SC-01: a TLS request on the checked address still verifies the certificate for the host name of the URL.

    A real TLS server on 127.0.0.1 with a certificate for ``as.example.invalid`` from a test CA. The request
    goes through ``_new_opener`` with the test CA as its trust store; the system resolver does not know
    the names. The certificates
    come from the ``openssl`` command line tool; without it the tests are skipped.
    """

    @classmethod
    def setUpClass(cls):
        import shutil
        import ssl
        import subprocess

        if shutil.which("openssl") is None:
            raise unittest.SkipTest("needs the openssl command line tool")
        cls.dir = Path(tempfile.mkdtemp(prefix="sref-tls-"))

        def run(*args):
            subprocess.run(["openssl", *args], cwd=cls.dir, check=True, capture_output=True)

        for ca in ("ca", "other-ca"):
            run("req", "-x509", "-newkey", "rsa:2048", "-nodes", "-keyout", f"{ca}.key", "-out", f"{ca}.pem",
                "-days", "2", "-subj", f"/CN={ca}", "-addext", "basicConstraints=critical,CA:TRUE",
                "-addext", "keyUsage=critical,keyCertSign")
        (cls.dir / "leaf.ext").write_text("subjectAltName=DNS:as.example.invalid\nbasicConstraints=CA:FALSE\n"
                                         "extendedKeyUsage=serverAuth\nauthorityKeyIdentifier=keyid,issuer\n"
                                         "subjectKeyIdentifier=hash\n")
        run("req", "-newkey", "rsa:2048", "-nodes", "-keyout", "leaf.key", "-out", "leaf.csr",
            "-subj", "/CN=as.example.invalid")
        run("x509", "-req", "-in", "leaf.csr", "-CA", "ca.pem", "-CAkey", "ca.key", "-CAcreateserial",
            "-out", "leaf.pem", "-days", "2", "-extfile", "leaf.ext")

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                body = b"{}"
                self.send_response(200)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        server_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        server_context.load_cert_chain(cls.dir / "leaf.pem", cls.dir / "leaf.key")
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.server.socket = server_context.wrap_socket(cls.server.socket, server_side=True)
        cls.port = cls.server.server_address[1]
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        import shutil

        cls.server.shutdown()
        cls.server.server_close()
        shutil.rmtree(cls.dir, ignore_errors=True)

    def _get(self, host, ca):
        import ssl
        from urllib.request import Request

        from sensitive_references import resolver_client as rc

        context = ssl.create_default_context(cafile=str(self.dir / ca))
        opener = rc._new_opener(context=context)
        request = Request(f"https://{host}:{self.port}/x")
        request.pinned_addresses = ["127.0.0.1"]
        with opener.open(request, timeout=5) as response:
            return response.status

    def _refused(self, host, ca):
        import ssl
        from urllib.error import URLError

        with self.assertRaises(URLError) as caught:
            self._get(host, ca)
        self.assertIsInstance(caught.exception.reason, ssl.SSLCertVerificationError)

    def test_a_certificate_for_the_host_name_of_the_url_is_accepted_on_the_checked_address(self):
        self.assertEqual(self._get("as.example.invalid", "ca.pem"), 200)

    def test_a_certificate_for_another_host_name_is_refused(self):
        self._refused("other.example.invalid", "ca.pem")

    def test_a_certificate_from_an_untrusted_ca_is_refused(self):
        self._refused("as.example.invalid", "other-ca.pem")


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
                                    "--no-interactive", "--materialize-template", "a {ref}",
                                    "--no-resource-metadata", "--no-discovery-object", "--allow-local-targets",
                                    "--local-origin", "http://127.0.0.1:9000", "--local-origin", "https://a.test"])
        config = mcp_host.resolve_config(args)
        self.assertEqual((config.destination, config.resolve_endpoint, config.resolve_scope, config.token_cache,
                          config.interactive, config.template, config.no_metadata, config.no_discovery_object,
                          config.allow_local, config.local_origins),
                         ("out.txt", "https://s.example/r", "s", "c.json", False, "a {ref}", True, True,
                          True, ("http://127.0.0.1:9000", "https://a.test")))
        default = mcp_host.resolve_config(mcp_host.parse_args(
            ["--url", "https://s.example/mcp", "--extension-id", "x/y", "--tool", "t"]))
        self.assertFalse(default.no_metadata)
        self.assertFalse(default.no_discovery_object)
        self.assertFalse(default.allow_local)
        self.assertEqual(default.local_origins, ())
        policy = mcp_host.fetch_policy("http://127.0.0.1:9/mcp", config)
        self.assertEqual((policy.local, ("https", "a.test", 443) in policy.local_origins), (True, True))


if __name__ == "__main__":
    unittest.main()
