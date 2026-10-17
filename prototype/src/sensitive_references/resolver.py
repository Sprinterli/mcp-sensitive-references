"""Resolver abstraction; OAuth Resolver Profile can replace this authorization stub."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence

from .issuer import InMemoryIssuer


@dataclass(frozen=True)
class SinkContext:
    sink_type: str
    destination: str
    principal: str


class ResolutionError(RuntimeError):
    pass


class Resolver(Protocol):
    def resolve(self, issuer: str, references: Sequence[str], sink_context: SinkContext) -> dict[str, str]: ...


class ResolverAuthorization:
    """Separate authorization state proves a token alone cannot resolve."""

    def __init__(self) -> None:
        self._grants: set[tuple[str, str]] = set()

    def grant(self, issuer: str, principal: str) -> None:
        self._grants.add((issuer, principal))

    def allowed(self, issuer: str, principal: str) -> bool:
        return (issuer, principal) in self._grants


class InMemoryResolver:
    def __init__(self, issuers: dict[str, InMemoryIssuer], authorization: ResolverAuthorization) -> None:
        self._issuers = issuers
        self._authorization = authorization

    def resolve(self, issuer: str, references: Sequence[str], sink_context: SinkContext) -> dict[str, str]:
        if sink_context.sink_type != "local_file":
            raise ResolutionError("ineligible sink")
        if not self._authorization.allowed(issuer, sink_context.principal):
            raise ResolutionError("resolver lacks resolve-specific authorization")
        registry = self._issuers.get(issuer)
        if registry is None:
            raise ResolutionError("unknown issuer")
        # Build all values before returning any: callers cannot partially materialize a batch.
        try:
            return {token: registry.value_for(token, principal=sink_context.principal) for token in references}
        except (KeyError, PermissionError) as exc:
            raise ResolutionError(str(exc)) from exc
