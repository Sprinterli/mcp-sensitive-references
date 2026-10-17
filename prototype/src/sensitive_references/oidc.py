"""OIDC discovery, PKCE construction, and JWT verification for oauth-resolver-1."""

from __future__ import annotations

from dataclasses import dataclass
from base64 import urlsafe_b64encode
from hashlib import sha256
import json
import secrets
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import Request, urlopen

import jwt

from .oauth_profile import RESOLVE_SCOPE


@dataclass(frozen=True)
class OidcMetadata:
    issuer: str
    authorization_endpoint: str
    token_endpoint: str
    jwks_uri: str

    @classmethod
    def discover(cls, issuer: str) -> "OidcMetadata":
        url = issuer.rstrip("/") + "/.well-known/openid-configuration"
        with urlopen(url, timeout=5) as response:  # nosec B310: issuer is host-configured discovery
            document = json.load(response)
        return cls(
            issuer=document["issuer"],
            authorization_endpoint=document["authorization_endpoint"],
            token_endpoint=document["token_endpoint"],
            jwks_uri=document["jwks_uri"],
        )


@dataclass(frozen=True)
class PkceAuthorization:
    authorization_url: str
    state: str
    code_verifier: str


class PkceResolverClient:
    """Creates an Authorization Code + PKCE request; token exchange stays outside model context."""

    def __init__(self, metadata: OidcMetadata, client_id: str, redirect_uri: str, *, resource: str, resolve_scope: str = RESOLVE_SCOPE, identity_scopes: str = "openid") -> None:
        self.metadata = metadata
        self.client_id = client_id
        self.redirect_uri = redirect_uri
        self.resource = resource
        self.resolve_scope = resolve_scope
        self.identity_scopes = identity_scopes

    def begin_authorization(self) -> PkceAuthorization:
        verifier = secrets.token_urlsafe(48)
        challenge = urlsafe_b64encode(sha256(verifier.encode()).digest()).rstrip(b"=").decode()
        state = secrets.token_urlsafe(24)
        query = urlencode(
            {
                "response_type": "code",
                "client_id": self.client_id,
                "redirect_uri": self.redirect_uri,
                "scope": f"{self.identity_scopes} {self.resolve_scope}",
                "resource": self.resource,
                "state": state,
                "code_challenge": challenge,
                "code_challenge_method": "S256",
            }
        )
        return PkceAuthorization(f"{self.metadata.authorization_endpoint}?{query}", state, verifier)

    def complete_authorization(self, callback_url: str, authorization: PkceAuthorization) -> str:
        """Validate the browser callback and exchange the code without exposing the token to a model."""
        parameters = parse_qs(urlparse(callback_url).query)
        if parameters.get("state") != [authorization.state]:
            raise PermissionError("OAuth callback state did not match")
        code = parameters.get("code", [None])[0]
        if not code:
            raise PermissionError("OAuth callback did not contain an authorization code")
        payload = urlencode(
            {
                "grant_type": "authorization_code",
                "client_id": self.client_id,
                "redirect_uri": self.redirect_uri,
                "code": code,
                "code_verifier": authorization.code_verifier,
                "resource": self.resource,
            }
        ).encode()
        request = Request(self.metadata.token_endpoint, data=payload, headers={"Content-Type": "application/x-www-form-urlencoded"})
        with urlopen(request, timeout=10) as response:  # nosec B310: issuer is host-configured discovery
            document = json.load(response)
        return document["access_token"]


class JwtResolverTokenVerifier:
    """Resource-server checks for a Keycloak/other OIDC-issued resolver access token."""

    def __init__(self, metadata: OidcMetadata, *, audience: str, required_scope: str = RESOLVE_SCOPE) -> None:
        self.metadata = metadata
        self.audience = audience
        self.required_scope = required_scope
        self._jwks = jwt.PyJWKClient(metadata.jwks_uri)

    def verify(self, bearer_token: str) -> dict[str, Any]:
        signing_key = self._jwks.get_signing_key_from_jwt(bearer_token)
        claims = jwt.decode(
            bearer_token,
            signing_key.key,
            algorithms=["RS256"],
            audience=self.audience,
            issuer=self.metadata.issuer,
        )
        scopes = set(claims.get("scope", "").split())
        if self.required_scope not in scopes:
            raise PermissionError("missing resolve-specific scope")
        return claims
