"""In-memory issuer registry.  It stands in for a protected resource's mapping."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from .reference import SensitiveReference, make_token


@dataclass
class IssuedValue:
    reference: SensitiveReference
    plaintext: str
    principal: str
    revoked: bool = False
    expires_at: datetime | None = None


class InMemoryIssuer:
    def __init__(self, issuer: str) -> None:
        self.issuer = issuer
        self._issued: dict[str, IssuedValue] = {}

    def issue(self, kind: str, plaintext: str, *, principal: str, expires_at: datetime | None = None) -> SensitiveReference:
        reference = make_token(kind)
        self._issued[reference.token] = IssuedValue(reference, plaintext, principal, expires_at=expires_at)
        return reference

    def revoke(self, token: str) -> None:
        self._issued[token].revoked = True

    def value_for(self, token: str, *, principal: str) -> str:
        issued = self._issued.get(token)
        if issued is None:
            raise KeyError("unknown reference")
        if issued.revoked:
            raise PermissionError("revoked reference")
        if issued.expires_at is not None and issued.expires_at <= datetime.now(timezone.utc):
            raise PermissionError("expired reference")
        if issued.principal != principal:
            raise PermissionError("reference belongs to another principal")
        return issued.plaintext
