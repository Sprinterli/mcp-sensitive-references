import json
from urllib.parse import parse_qs, urlparse
from unittest.mock import Mock, patch
import unittest

from fastapi.testclient import TestClient

from sensitive_references.issuer import InMemoryIssuer
from sensitive_references.http_resolver import HttpResolver, ResolverEndpoint
from sensitive_references.oidc import OidcMetadata, PkceResolverClient
from sensitive_references.resolve_http import create_resolve_app
from sensitive_references.resolver import ResolutionError, SinkContext


ISSUER = "https://issuer.example/mcp"
OIDC_ISSUER = "https://idp.example/realms/demo"


class OidcAndResolveHttpTests(unittest.TestCase):
    def test_discovery_and_pkce_request_are_resource_bound(self):
        payload = json.dumps({
            "issuer": OIDC_ISSUER,
            "authorization_endpoint": f"{OIDC_ISSUER}/protocol/openid-connect/auth",
            "token_endpoint": f"{OIDC_ISSUER}/protocol/openid-connect/token",
            "jwks_uri": f"{OIDC_ISSUER}/protocol/openid-connect/certs",
        }).encode()
        response = Mock()
        response.__enter__ = lambda _: _
        response.__exit__ = Mock(return_value=False)
        response.read.return_value = payload
        with patch("sensitive_references.oidc.urlopen", return_value=response):
            metadata = OidcMetadata.discover(OIDC_ISSUER)
        authorization = PkceResolverClient(metadata, "resolver-client", "http://127.0.0.1/callback", resource=ISSUER).begin_authorization()
        query = parse_qs(urlparse(authorization.authorization_url).query)
        self.assertEqual(query["resource"], [ISSUER])
        self.assertEqual(query["code_challenge_method"], ["S256"])
        self.assertIn("sensitive-references.resolve", query["scope"][0])
        self.assertNotEqual(authorization.code_verifier, query["code_challenge"][0])

    def test_pkce_callback_requires_state_and_exchanges_the_code(self):
        metadata = OidcMetadata(OIDC_ISSUER, f"{OIDC_ISSUER}/auth", f"{OIDC_ISSUER}/token", f"{OIDC_ISSUER}/certs")
        client = PkceResolverClient(metadata, "resolver-client", "http://127.0.0.1/callback", resource=ISSUER)
        authorization = client.begin_authorization()
        response = Mock()
        response.__enter__ = lambda _: _
        response.__exit__ = Mock(return_value=False)
        response.read.return_value = json.dumps({"access_token": "test-access-token"}).encode()
        callback = f"http://127.0.0.1/callback?code=authorization-code&state={authorization.state}"
        with patch("sensitive_references.oidc.urlopen", return_value=response):
            self.assertEqual(client.complete_authorization(callback, authorization), "test-access-token")
        with self.assertRaises(PermissionError):
            client.complete_authorization("http://127.0.0.1/callback?code=authorization-code&state=wrong", authorization)

    def test_resolve_endpoint_is_subject_bound_and_has_no_partial_success(self):
        registry = InMemoryIssuer(ISSUER)
        valid = registry.issue("email", "alice@example.com", principal="user-a")
        verifier = Mock()
        verifier.verify.return_value = {"sub": "user-a"}
        client = TestClient(create_resolve_app(registry, verifier))
        response = client.post(
            "/sensitive-references/resolve",
            headers={"Authorization": "Bearer resolver-token"},
            json={"references": [valid.token, "⟦sref:email:UNKNOWN_REFERENCE_VALUE_01⟧"], "sink_type": "local_file", "destination": "customers.csv"},
        )
        self.assertEqual(response.status_code, 403)
        self.assertNotIn("alice@example.com", response.text)

    def test_http_resolver_accepts_only_complete_batch_from_configured_endpoint(self):
        response = Mock()
        response.__enter__ = lambda _: _
        response.__exit__ = Mock(return_value=False)
        first = "⟦sref:email:AbCdEfGhIjKlMnOpQrStUvWx1234⟧"
        second = "⟦sref:phone:ZyXwVuTsRqPoNmLkJiHgFeDc9876⟧"
        response.read.return_value = json.dumps({"values": {first: "a@example.com", second: "+1-555-0100"}}).encode()
        resolver = HttpResolver({ISSUER: ResolverEndpoint("https://resolver.example/resolve", lambda: "resolver-access-token")})
        context = SinkContext("local_file", "customers.csv", "user-a")
        with patch("sensitive_references.http_resolver.urlopen", return_value=response):
            values = resolver.resolve(ISSUER, [first, second], context)
        self.assertEqual(set(values), {first, second})
        with self.assertRaises(ResolutionError):
            resolver.resolve("https://untrusted.example/mcp", [first], context)
