from pathlib import Path
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

from sensitive_references import InMemoryIssuer, InMemoryResolver, ProtectedFileSink, ProvenanceStore, ResolverAuthorization
from sensitive_references.provenance import AmbiguousReference, UnknownReference
from sensitive_references.output_guard import redact_resolved_output
from sensitive_references.capabilities import CapabilitySettingsError, SensitiveReferencesCapabilities, negotiate
from sensitive_references.resolver import ResolutionError


ISSUER_A = "https://issuer-a.example/mcp"
ISSUER_B = "https://issuer-b.example/mcp"
PRINCIPAL = "user-a"


class SensitiveReferenceTests(unittest.TestCase):
    def setUp(self):
        self.issuer = InMemoryIssuer(ISSUER_A)
        self.provenance = ProvenanceStore()
        self.authorization = ResolverAuthorization()
        self.resolver = InMemoryResolver({ISSUER_A: self.issuer}, self.authorization)

    def observe(self, token):
        self.provenance.observe_mcp_result(ISSUER_A, extension_negotiated=True, result={"email": token})

    def sink(self):
        return ProtectedFileSink(self.provenance, self.resolver, principal=PRINCIPAL)

    def test_reference_contains_no_plaintext_and_equal_values_get_unrelated_ids(self):
        first = self.issuer.issue("email", "alice@example.com", principal=PRINCIPAL)
        second = self.issuer.issue("email", "alice@example.com", principal=PRINCIPAL)
        self.assertNotIn("alice@example.com", first.token)
        self.assertNotEqual(first.token, second.token)

    def test_valid_observed_reference_resolves_to_protected_file_only(self):
        reference = self.issuer.issue("email", "alice@example.com", principal=PRINCIPAL)
        self.observe(reference.token)
        self.authorization.grant(ISSUER_A, PRINCIPAL)
        model_content = f"Name,Email\nCustomer 42,{reference.token}\n"
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "customers.csv"
            result = self.sink().write(output, model_content)
            self.assertEqual(output.read_text(), "Name,Email\nCustomer 42,alice@example.com\n")
        self.assertEqual(result.model_facing_content, model_content)
        self.assertNotIn("alice@example.com", result.model_facing_content)

    def test_unobserved_forged_token_fails_closed(self):
        forged = "⟦sref:email:ATTACKER_CONTROLLED_IDENTIFIER⟧"
        with self.assertRaises(UnknownReference):
            self.sink().write(Path(tempfile.gettempdir()) / "forged.csv", forged)

    def test_unsupported_capabilities_do_not_create_trusted_provenance(self):
        reference = self.issuer.issue("email", "alice@example.com", principal=PRINCIPAL)
        client = SensitiveReferencesCapabilities(frozenset({"1"}), frozenset({"oauth-resolver-1"}), frozenset({"local-file-1"}))
        unsupported_server = SensitiveReferencesCapabilities(frozenset({"2"}), frozenset(), frozenset())
        self.assertIsNone(negotiate(client, unsupported_server))
        self.provenance.observe_mcp_result(ISSUER_A, extension_negotiated=False, result={"email": reference.token})
        with self.assertRaises(UnknownReference):
            self.provenance.issuer_for(reference.token)

    def test_capability_intersection_retains_only_common_profiles(self):
        client = SensitiveReferencesCapabilities(frozenset({"1"}), frozenset({"oauth-resolver-1", "other"}), frozenset({"local-file-1"}))
        server = SensitiveReferencesCapabilities(frozenset({"1"}), frozenset({"oauth-resolver-1"}), frozenset({"local-file-1", "other"}))
        agreed = negotiate(client, server)
        self.assertEqual(agreed.version, "1")
        self.assertEqual(agreed.resolver_profiles, frozenset({"oauth-resolver-1"}))
        self.assertEqual(agreed.sink_profiles, frozenset({"local-file-1"}))

    def test_capability_settings_round_trip_and_reject_unknown_fields(self):
        capabilities = SensitiveReferencesCapabilities.from_settings({"versions": ["1"], "resolver_profiles": ["oauth-resolver-1"], "sink_profiles": ["local-file-1"]})
        self.assertEqual(capabilities.to_settings()["versions"], ["1"])
        with self.assertRaises(CapabilitySettingsError):
            SensitiveReferencesCapabilities.from_settings({"versions": ["1"], "issuer": "model-editable"})

    def test_wrong_issuer_does_not_resolve(self):
        reference = self.issuer.issue("email", "alice@example.com", principal=PRINCIPAL)
        self.authorization.grant(ISSUER_A, PRINCIPAL)
        with self.assertRaises(ResolutionError):
            self.resolver.resolve(ISSUER_B, [reference.token], self._context())

    def test_ambiguous_issuer_fails_closed(self):
        reference = self.issuer.issue("email", "alice@example.com", principal=PRINCIPAL)
        self.observe(reference.token)
        self.provenance.observe_mcp_result(ISSUER_B, extension_negotiated=True, result={"email": reference.token})
        with self.assertRaises(AmbiguousReference):
            self.provenance.issuer_for(reference.token)

    def test_unknown_and_revoked_references_fail_closed(self):
        reference = self.issuer.issue("email", "alice@example.com", principal=PRINCIPAL)
        self.authorization.grant(ISSUER_A, PRINCIPAL)
        with self.assertRaises(ResolutionError):
            self.resolver.resolve(ISSUER_A, ["⟦sref:email:UNKNOWN_REFERENCE_VALUE_01⟧"], self._context())
        self.issuer.revoke(reference.token)
        with self.assertRaises(ResolutionError):
            self.resolver.resolve(ISSUER_A, [reference.token], self._context())

    def test_expired_reference_fails_closed(self):
        reference = self.issuer.issue("email", "alice@example.com", principal=PRINCIPAL, expires_at=datetime.now(timezone.utc) - timedelta(seconds=1))
        self.authorization.grant(ISSUER_A, PRINCIPAL)
        with self.assertRaises(ResolutionError):
            self.resolver.resolve(ISSUER_A, [reference.token], self._context())

    def test_batch_is_all_or_nothing(self):
        valid = self.issuer.issue("email", "alice@example.com", principal=PRINCIPAL)
        self.observe(valid.token)
        self.authorization.grant(ISSUER_A, PRINCIPAL)
        unknown = "⟦sref:email:UNKNOWN_REFERENCE_VALUE_01⟧"
        self.provenance.observe_mcp_result(ISSUER_A, extension_negotiated=True, result={"email": unknown})
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "customers.csv"
            output.write_text("unchanged")
            with self.assertRaises(ResolutionError):
                self.sink().write(output, f"{valid.token},{unknown}")
            self.assertEqual(output.read_text(), "unchanged")

    def test_possession_without_resolver_authorization_fails(self):
        reference = self.issuer.issue("email", "alice@example.com", principal=PRINCIPAL)
        with self.assertRaises(ResolutionError):
            self.resolver.resolve(ISSUER_A, [reference.token], self._context())

    def test_downstream_echo_redaction_uses_only_values_resolved_in_this_operation(self):
        email = "alice@example.com"
        token = "⟦sref:email:AbCdEfGhIjKlMnOpQrStUvWx1234⟧"
        output = "wrote alice@example.com; unrelated person@example.com remains"
        redacted = redact_resolved_output(output, {token: email})
        self.assertIn(token, redacted)
        self.assertNotIn(email, redacted)
        self.assertIn("person@example.com", redacted)

    def _context(self):
        from sensitive_references.resolver import SinkContext
        return SinkContext("local_file", "ignored.csv", PRINCIPAL)


if __name__ == "__main__":
    unittest.main()
