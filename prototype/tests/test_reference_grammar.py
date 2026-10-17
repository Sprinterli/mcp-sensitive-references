import unittest

from sensitive_references.reference import InvalidReference, parse_token


VALID = "⟦sref:email:AbCdEfGhIjKlMnOpQrStUvWx1234⟧"


class ReferenceGrammarTests(unittest.TestCase):
    def test_canonical_vector_is_valid(self):
        reference = parse_token(VALID)
        self.assertEqual(reference.kind, "email")
        self.assertEqual(reference.identifier, "AbCdEfGhIjKlMnOpQrStUvWx1234")

    def test_short_id_trailing_text_and_lookalike_brackets_are_not_tokens(self):
        for value in [
            "⟦sref:email:short⟧",
            VALID + " ",
            "［sref:email:AbCdEfGhIjKlMnOpQrStUvWx1234］",
        ]:
            with self.subTest(value=value), self.assertRaises(InvalidReference):
                parse_token(value)
