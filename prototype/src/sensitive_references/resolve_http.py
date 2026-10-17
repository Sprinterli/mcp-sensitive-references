"""Minimal non-model HTTP resolve endpoint for an OAuth Resolver Profile PoC."""

from __future__ import annotations

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from .issuer import InMemoryIssuer
from .resolver import ResolutionError, SinkContext


class ResolveRequest(BaseModel):
    references: list[str] = Field(min_length=1, max_length=100)
    sink_type: str
    destination: str


def create_resolve_app(issuer: InMemoryIssuer, verifier) -> FastAPI:
    app = FastAPI(title="Sensitive References resolver PoC")

    @app.post("/sensitive-references/resolve")
    def resolve(request: ResolveRequest, authorization: str | None = Header(default=None)) -> dict[str, dict[str, str]]:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(401, "missing resolver authorization")
        try:
            claims = verifier.verify(authorization.removeprefix("Bearer "))
            principal = claims["sub"]
            context = SinkContext(request.sink_type, request.destination, principal)
            if context.sink_type != "local_file":
                raise ResolutionError("ineligible sink")
            # Build before returning: invalid/revoked refs produce no partial response body.
            values = {token: issuer.value_for(token, principal=principal) for token in request.references}
            return {"values": values}
        except (PermissionError, KeyError, ResolutionError) as exc:
            raise HTTPException(403, str(exc)) from exc

    return app
