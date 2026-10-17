"""Host-owned trusted observations from negotiated MCP results."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from .reference import find_tokens


class UnknownReference(LookupError):
    pass


class AmbiguousReference(LookupError):
    pass


@dataclass(frozen=True)
class Observation:
    token: str
    issuer: str
    first_observed: datetime


class ProvenanceStore:
    """Only an authenticated, negotiated result can add a trusted observation."""

    def __init__(self) -> None:
        self._observations: dict[str, dict[str, Observation]] = {}

    def observe_mcp_result(self, issuer: str, *, extension_negotiated: bool, result: Any) -> None:
        if not extension_negotiated:
            return
        for value in self._strings(result):
            for reference in find_tokens(value):
                by_issuer = self._observations.setdefault(reference.token, {})
                by_issuer.setdefault(
                    issuer,
                    Observation(reference.token, issuer, datetime.now(timezone.utc)),
                )

    def issuer_for(self, token: str) -> str:
        by_issuer = self._observations.get(token)
        if not by_issuer:
            raise UnknownReference("reference was never observed in a trusted MCP result")
        if len(by_issuer) != 1:
            raise AmbiguousReference("reference has more than one trusted issuer")
        return next(iter(by_issuer))

    @staticmethod
    def _strings(value: Any):
        if isinstance(value, str):
            yield value
        elif isinstance(value, dict):
            for nested in value.values():
                yield from ProvenanceStore._strings(nested)
        elif isinstance(value, list):
            for nested in value:
                yield from ProvenanceStore._strings(nested)
