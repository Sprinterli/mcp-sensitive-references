"""Redact known materialized values if a downstream action echoes them to the model."""

from __future__ import annotations

from collections.abc import Mapping


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
