"""Local feasibility model for the OAuth Resolver Profile, not an OAuth implementation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Sequence

from .issuer import InMemoryIssuer
from .resolver import ResolutionError, SinkContext

RESOLVE_SCOPE = "sensitive-references.resolve"


@dataclass(frozen=True)
class ResolverAccessToken:
    """Claims the protected resource must validate before releasing plaintext."""

    issuer: str
    subject: str
    audience: str
    scopes: frozenset[str]
    expires_at: datetime


class OAuthResolverProfile:
    """Models a separately authorized resolver client with a resource-bound token."""

    def __init__(self, issuers: dict[str, InMemoryIssuer], tokens: dict[tuple[str, str], ResolverAccessToken]) -> None:
        self._issuers = issuers
        self._tokens = tokens

    def resolve(self, issuer: str, references: Sequence[str], sink_context: SinkContext) -> dict[str, str]:
        token = self._tokens.get((issuer, sink_context.principal))
        now = datetime.now(timezone.utc)
        if token is None:
            raise ResolutionError("resolver has no separately authorized access token")
        if token.issuer != issuer or token.audience != issuer:
            raise ResolutionError("resolver token is not bound to this protected resource")
        if token.subject != sink_context.principal:
            raise ResolutionError("resolver token subject does not match sink principal")
        if RESOLVE_SCOPE not in token.scopes:
            raise ResolutionError("resolver token lacks resolve-specific scope")
        if token.expires_at <= now:
            raise ResolutionError("resolver token is expired")
        registry = self._issuers.get(issuer)
        if registry is None:
            raise ResolutionError("unknown issuer")
        try:
            return {token: registry.value_for(token, principal=sink_context.principal) for token in references}
        except (KeyError, PermissionError) as exc:
            raise ResolutionError(str(exc)) from exc
