"""Host-side HTTP adapter for the OAuth Resolver Profile."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Callable, Sequence
from urllib.request import Request, urlopen

from .resolver import ResolutionError, SinkContext


@dataclass(frozen=True)
class ResolverEndpoint:
    url: str
    access_token: Callable[[], str]


class HttpResolver:
    """Endpoints are configured per trusted issuer; references never choose a URL."""

    def __init__(self, endpoints: dict[str, ResolverEndpoint]) -> None:
        self._endpoints = endpoints

    def resolve(self, issuer: str, references: Sequence[str], sink_context: SinkContext) -> dict[str, str]:
        endpoint = self._endpoints.get(issuer)
        if endpoint is None:
            raise ResolutionError("issuer has no trusted resolver endpoint")
        payload = json.dumps(
            {"references": list(references), "sink_type": sink_context.sink_type, "destination": sink_context.destination}
        ).encode()
        request = Request(
            endpoint.url,
            data=payload,
            headers={"Authorization": f"Bearer {endpoint.access_token()}", "Content-Type": "application/json"},
        )
        try:
            with urlopen(request, timeout=10) as response:  # nosec B310: URL is issuer-bound host configuration
                document = json.load(response)
        except Exception as exc:
            raise ResolutionError("resolver endpoint denied or failed") from exc
        values = document.get("values")
        if not isinstance(values, dict) or set(values) != set(references) or not all(isinstance(value, str) for value in values.values()):
            raise ResolutionError("resolver returned an incomplete or malformed batch")
        return values
