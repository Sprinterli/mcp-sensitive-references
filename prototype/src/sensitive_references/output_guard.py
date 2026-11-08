"""Redact known materialized values if a downstream action echoes them to the model."""

from __future__ import annotations

from base64 import b64encode, urlsafe_b64encode
from collections.abc import Mapping
from urllib.parse import quote


def redact_resolved_output(output: str, resolved_values: Mapping[str, str]) -> str:
    """Replace only values resolved in this protected operation with their original tokens.

    Longest-first replacement avoids a shorter resolved value corrupting a longer one.
    Callers retain the mapping outside model-visible output.
    """
    result = output
    for token, plaintext in sorted(resolved_values.items(), key=lambda item: len(item[1]), reverse=True):
        if plaintext:
            result = result.replace(plaintext, token)
    return result


def _encodings(value: str) -> set[str]:
    """The value and the encodings that the guard recognizes: percent-encoding and base64 (standard and
    URL-safe, with and without padding). A value that a program changes in another way is not found."""
    raw = value.encode()
    forms = {value, quote(value, safe="")}
    for encoded in (b64encode(raw).decode(), urlsafe_b64encode(raw).decode()):
        forms.update({encoded, encoded.rstrip("=")})
    return {f for f in forms if f}


class SessionMask:
    """The values that the host released in this session, kept so that later text is masked back.

    PROCESS-PROFILE.md, section 5, and DISPLAY-PROFILE.md, section 5, rule 2. The mapping stays in host
    memory; it never goes into model-visible text.
    """

    def __init__(self) -> None:
        self._values: dict[str, str] = {}

    def release(self, values: Mapping[str, str]) -> None:
        self._values.update(values)

    def held(self, reference: str) -> str | None:
        return self._values.get(reference)

    def mask(self, text: str) -> str:
        pairs = [(form, token) for token, value in self._values.items() if value for form in _encodings(value)]
        for form, token in sorted(pairs, key=lambda pair: len(pair[0]), reverse=True):
            text = text.replace(form, token)
        return text
