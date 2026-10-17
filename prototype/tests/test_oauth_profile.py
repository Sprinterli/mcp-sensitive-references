from datetime import datetime, timedelta, timezone
import unittest

from sensitive_references.issuer import InMemoryIssuer
from sensitive_references.oauth_profile import OAuthResolverProfile, RESOLVE_SCOPE, ResolverAccessToken
from sensitive_references.resolver import ResolutionError, SinkContext


ISSUER = "https://issuer.example/mcp"
PRINCIPAL = "user-a"


class OAuthResolverProfileTests(unittest.TestCase):
    def setUp(self):
        self.registry = InMemoryIssuer(ISSUER)
        self.reference = self.registry.issue("email", "alice@example.com", principal=PRINCIPAL)

    def profile(self, **changes):
        fields = {
            "issuer": ISSUER,
            "subject": PRINCIPAL,
            "audience": ISSUER,
            "scopes": frozenset({RESOLVE_SCOPE}),
            "expires_at": datetime.now(timezone.utc) + timedelta(minutes=5),
        }
        fields.update(changes)
        token = ResolverAccessToken(**fields)
        return OAuthResolverProfile({ISSUER: self.registry}, {(ISSUER, PRINCIPAL): token})

    def context(self):
        return SinkContext("local_file", "customers.csv", PRINCIPAL)

    def test_resource_bound_resolve_scope_authorizes_resolution(self):
        self.assertEqual(self.profile().resolve(ISSUER, [self.reference.token], self.context()), {self.reference.token: "alice@example.com"})

    def test_wrong_audience_scope_or_expiry_fails_closed(self):
        cases = [
            {"audience": "https://other.example/mcp"},
            {"scopes": frozenset()},
            {"expires_at": datetime.now(timezone.utc) - timedelta(seconds=1)},
        ]
        for changes in cases:
            with self.subTest(changes=changes), self.assertRaises(ResolutionError):
                self.profile(**changes).resolve(ISSUER, [self.reference.token], self.context())
