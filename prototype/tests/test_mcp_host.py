"""The test host's checks, on results shaped as an MCP SDK client receives them.

No network and no MCP SDK: the host's checks take the result as a dict.

Each check in ``demo/mcp_host.py`` was disabled once (replaced by ``if False:``)
and these tests failed: the sentinel check, the non-canonical check, the
token-without-negotiation check, the provenance check, the isError check, the
refusal check; and ``public_endpoint`` returning the URL unchanged, and ``main``
without its catch.
"""

import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "demo"))
import mcp_host  # noqa: E402
from mcp_host import HostReport, _check, inspect_result, public_endpoint, refused  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from sensitive_references import ProvenanceStore  # noqa: E402

OPEN, CLOSE = "⟦", "⟧"
ISSUER = "https://issuer.example/mcp"
TOKEN = OPEN + "sref:email:AbCdEfGhIjKlMnOpQrStUvWx1234" + CLOSE
#: A server's own token form that is not a Sensitive Reference. Built from
#: parts, so that a host that resolves such tokens does not read this file
#: as one.
LEGACY = OPEN + "EMAIL" + "_1" + CLOSE
SENTINEL = "alice@example.com"


def _result(*texts, structured=None):
    return {"content": [{"type": "text", "text": t} for t in texts],
            "structuredContent": structured or {}, "isError": False}


def _negotiated():
    return HostReport(server=ISSUER, declared=True, advertised=True, negotiated_version="1")


class HostCheckTests(unittest.TestCase):
    def test_a_negotiated_result_with_canonical_tokens_passes_and_records_provenance(self):
        store = ProvenanceStore()
        call = inspect_result("read", _result(f"mail {TOKEN}", structured={"to": TOKEN}),
                              issuer=ISSUER, negotiated=True, provenance=store, sentinels=[SENTINEL])
        report = _negotiated()
        _check(report, call)

        self.assertEqual((call.canonical_tokens, call.distinct_tokens), (2, 1))
        self.assertEqual(store.issuer_for(TOKEN), ISSUER)
        self.assertTrue(report.ok, report.failures)

    def test_a_reference_like_string_that_is_not_canonical_fails(self):
        for spoiled in (TOKEN.replace("sref:", "SREF:"), OPEN + "sref:email:…" + CLOSE,
                        TOKEN.replace(OPEN, "［").replace(CLOSE, "］"), TOKEN[:-1]):
            with self.subTest(spoiled=spoiled):
                call = inspect_result("read", _result(f"see {spoiled}"), issuer=ISSUER, negotiated=True,
                                      provenance=ProvenanceStore(), sentinels=[])
                report = _negotiated()
                _check(report, call)
                self.assertFalse(report.ok)

    def test_a_sentinel_value_in_the_result_fails_and_is_not_reported(self):
        call = inspect_result("read", _result(f"mail {SENTINEL}"), issuer=ISSUER, negotiated=True,
                              provenance=ProvenanceStore(), sentinels=[SENTINEL])
        report = _negotiated()
        _check(report, call)

        self.assertEqual(call.sentinel_hits, 1)
        self.assertFalse(report.ok)
        self.assertNotIn(SENTINEL, repr(report))

    def test_a_sentinel_outside_the_text_blocks_fails_too(self):
        result = _result("nothing here")
        result["_meta"] = {"note": SENTINEL}
        call = inspect_result("read", result, issuer=ISSUER, negotiated=True,
                              provenance=ProvenanceStore(), sentinels=[SENTINEL])
        report = _negotiated()
        _check(report, call)

        self.assertFalse(report.ok)

    def test_a_failed_call_fails_when_success_is_expected(self):
        result = _result("refused")
        result["isError"] = True
        call = inspect_result("write", result, issuer=ISSUER, negotiated=True,
                              provenance=ProvenanceStore(), sentinels=[])
        lenient, strict = _negotiated(), _negotiated()
        _check(lenient, call)
        _check(strict, call, expect_success=True)

        self.assertTrue(lenient.ok)
        self.assertFalse(strict.ok)

    def test_without_negotiation_no_provenance_is_recorded_and_a_token_fails(self):
        store = ProvenanceStore()
        call = inspect_result("read", _result(TOKEN), issuer=ISSUER, negotiated=False,
                              provenance=store, sentinels=[])
        report = HostReport(server=ISSUER, declared=False, advertised=True)
        _check(report, call)

        self.assertEqual(call.observed_with_provenance, 0)
        self.assertFalse(report.ok, "a host that declared nothing must see no canonical token")

    def test_a_result_without_references_passes_for_a_host_that_declared_nothing(self):
        call = inspect_result("read", _result(f"mail {LEGACY}"), issuer=ISSUER, negotiated=False,
                              provenance=ProvenanceStore(), sentinels=[SENTINEL])
        report = HostReport(server=ISSUER, declared=False, advertised=True)
        _check(report, call)

        self.assertTrue(report.ok, report.failures)

    def test_a_token_seen_from_two_issuers_is_not_trusted(self):
        store = ProvenanceStore()
        store.observe_mcp_result("https://other.example/mcp", extension_negotiated=True, result={"t": TOKEN})
        call = inspect_result("read", _result(TOKEN), issuer=ISSUER, negotiated=True,
                              provenance=store, sentinels=[])
        report = _negotiated()
        _check(report, call)

        self.assertEqual(call.observed_with_provenance, 0)
        self.assertFalse(report.ok)


class RefusalTests(unittest.TestCase):
    """A server may report a refused resolution inside a successful result."""

    def _call(self, result):
        return inspect_result("write", result, issuer=ISSUER, negotiated=True,
                              provenance=ProvenanceStore(), sentinels=[])

    def test_a_structured_reference_refusal_fails_an_expected_success(self):
        body = '{"success": false, "error_code": "PII_REFERENCE_UNKNOWN", "message": "refused"}'
        for result in (_result(body), _result("done", structured={"code": "reference_revoked"})):
            with self.subTest(result=result):
                call = self._call(result)
                lenient, strict = _negotiated(), _negotiated()
                _check(lenient, call)
                _check(strict, call, expect_success=True)

                self.assertTrue(call.refused)
                self.assertTrue(lenient.ok)
                self.assertFalse(strict.ok)

    def test_ordinary_results_are_not_taken_for_refusals(self):
        for text in ('{"success": true, "data": {"posted": "a reference was used"}}',
                     "the reference is unknown to me, said the user",
                     '{"error_code": "RATE_LIMITED"}'):
            with self.subTest(text=text):
                self.assertFalse(refused(_result(text), [text]))

    def test_the_refusal_pattern_is_configuration(self):
        text = '{"error_code": "VENDOR_X_DENIED"}'
        self.assertFalse(refused(_result(text), [text]))
        self.assertTrue(refused(_result(text), [text], r"_DENIED$"))


class ReportSanitizingTests(unittest.TestCase):
    URL = "https://user:secret-password@mcp.example:8443/mcp?token=secret-token#secret-fragment"

    def test_the_endpoint_keeps_no_credential_query_or_fragment(self):
        self.assertEqual(public_endpoint(self.URL), "https://mcp.example:8443/mcp")

    def test_a_failed_run_reports_the_type_only_and_the_public_endpoint(self):
        async def _raise(args):
            raise ConnectionError(f"cannot reach {self.URL}")

        original, mcp_host.run = mcp_host.run, _raise
        printed = []
        try:
            import builtins
            builtins_print, builtins.print = builtins.print, lambda *a, **k: printed.append(" ".join(map(str, a)))
            try:
                code = mcp_host.main(["--url", self.URL, "--extension-id", "x/y", "--tool", "t"])
            finally:
                builtins.print = builtins_print
        finally:
            mcp_host.run = original
        output = "\n".join(printed)

        self.assertEqual(code, 1)
        self.assertIn("ConnectionError", output)
        for secret in ("secret-password", "secret-token", "secret-fragment", "user:"):
            self.assertNotIn(secret, output)


if __name__ == "__main__":
    unittest.main()
