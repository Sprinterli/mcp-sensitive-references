import json
from pathlib import Path
import unittest

from jsonschema import Draft202012Validator, ValidationError


SCHEMA_PATH = Path(__file__).resolve().parents[1] / "schema" / "sensitive-references-settings.schema.json"


class SettingsSchemaTests(unittest.TestCase):
    def test_schema_accepts_candidate_settings_and_rejects_unrecognized_fields(self):
        schema = json.loads(SCHEMA_PATH.read_text())
        Draft202012Validator.check_schema(schema)
        validator = Draft202012Validator(schema)
        validator.validate({"versions": ["1"], "resolver_profiles": ["oauth-resolver-1"], "sink_profiles": ["local-file-1"]})
        with self.assertRaises(ValidationError):
            validator.validate({"versions": ["1"], "issuer": "untrusted"})
