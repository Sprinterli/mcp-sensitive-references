"""Canonical v1 text-token parsing.  Tokens carry no issuer or authority."""

from __future__ import annotations

from dataclasses import dataclass
import re
import secrets

_TOKEN_RE = re.compile(r"⟦sref:([A-Za-z0-9_-]{1,32}):([A-Za-z0-9_-]{20,128})⟧")


@dataclass(frozen=True)
class SensitiveReference:
    token: str
    kind: str
    identifier: str


class InvalidReference(ValueError):
    pass


def new_identifier() -> str:
    """Return a generation-safe opaque ID; never derive it from plaintext."""
    return secrets.token_urlsafe(24)


def make_token(kind: str, identifier: str | None = None) -> SensitiveReference:
    identifier = identifier or new_identifier()
    token = f"⟦sref:{kind}:{identifier}⟧"
    return parse_token(token)


def parse_token(token: str) -> SensitiveReference:
    match = _TOKEN_RE.fullmatch(token)
    if not match:
        raise InvalidReference("not a canonical Sensitive Reference token")
    return SensitiveReference(token=token, kind=match.group(1), identifier=match.group(2))


def find_tokens(text: str) -> list[SensitiveReference]:
    return [SensitiveReference(match.group(0), match.group(1), match.group(2)) for match in _TOKEN_RE.finditer(text)]
