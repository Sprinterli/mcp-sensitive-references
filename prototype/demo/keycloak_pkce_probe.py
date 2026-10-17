"""Headless Authorization Code + PKCE proof against the local E2E Keycloak.

All Keycloak objects, credentials, codes, and access tokens are ephemeral and never printed.
"""

from __future__ import annotations

import html
import os
import re
import secrets
import sys
from uuid import uuid4
from urllib.parse import urljoin, urlparse

import requests
from fastapi.testclient import TestClient

from sensitive_references.issuer import InMemoryIssuer
from sensitive_references.oidc import JwtResolverTokenVerifier, OidcMetadata, PkceResolverClient
from sensitive_references.oauth_profile import RESOLVE_SCOPE
from sensitive_references.resolve_http import create_resolve_app

BASE = os.environ.get("SREF_KEYCLOAK", "http://127.0.0.1:8180")
REALM = "mcpgate"
RESOURCE = "http://localhost:3002/mcp"
REDIRECT_URI = "http://127.0.0.1:8765/callback"


def _admin_headers() -> dict[str, str]:
    response = requests.post(
        f"{BASE}/realms/master/protocol/openid-connect/token",
        data={"grant_type": "password", "client_id": "admin-cli", "username": "admin", "password": "admin"},
        timeout=10,
    )
    response.raise_for_status()
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _id(items: list[dict], key: str, value: str) -> str:
    return next(item["id"] for item in items if item[key] == value)


def main() -> int:
    headers = _admin_headers()
    suffix = uuid4().hex[:10]
    scope_name = f"{RESOLVE_SCOPE}-{suffix}"
    client_name = f"sref-pkce-{suffix}"
    username = f"sref-user-{suffix}"
    password = secrets.token_urlsafe(24)
    scope_id = client_id = user_id = None
    try:
        created = requests.post(
            f"{BASE}/admin/realms/{REALM}/client-scopes",
            headers=headers,
            json={"name": scope_name, "protocol": "openid-connect", "attributes": {"include.in.token.scope": "true"}},
            timeout=10,
        )
        created.raise_for_status()
        scope_id = _id(requests.get(f"{BASE}/admin/realms/{REALM}/client-scopes", headers=headers, params={"search": scope_name}, timeout=10).json(), "name", scope_name)
        created = requests.post(
            f"{BASE}/admin/realms/{REALM}/clients",
            headers=headers,
            json={
                "clientId": client_name,
                "enabled": True,
                "publicClient": True,
                "standardFlowEnabled": True,
                "directAccessGrantsEnabled": False,
                "fullScopeAllowed": False,
                "defaultClientScopes": ["profile", scope_name],
                "redirectUris": [REDIRECT_URI],
            },
            timeout=10,
        )
        created.raise_for_status()
        client_id = _id(requests.get(f"{BASE}/admin/realms/{REALM}/clients", headers=headers, params={"clientId": client_name}, timeout=10).json(), "clientId", client_name)
        requests.post(
            f"{BASE}/admin/realms/{REALM}/clients/{client_id}/protocol-mappers/models",
            headers=headers,
            json={"name": "sref-resource-audience", "protocol": "openid-connect", "protocolMapper": "oidc-audience-mapper", "config": {"included.custom.audience": RESOURCE, "access.token.claim": "true", "id.token.claim": "false"}},
            timeout=10,
        ).raise_for_status()
        requests.post(
            f"{BASE}/admin/realms/{REALM}/clients/{client_id}/protocol-mappers/models",
            headers=headers,
            json={"name": "sref-subject", "protocol": "openid-connect", "protocolMapper": "oidc-usermodel-property-mapper", "config": {"user.attribute": "username", "claim.name": "sub", "jsonType.label": "String", "access.token.claim": "true", "id.token.claim": "true", "userinfo.token.claim": "true"}},
            timeout=10,
        ).raise_for_status()
        created = requests.post(
            f"{BASE}/admin/realms/{REALM}/users",
            headers=headers,
            json={"username": username, "email": f"{username}@example.com", "firstName": "Sensitive", "lastName": "Reference", "enabled": True, "emailVerified": True, "requiredActions": []},
            timeout=10,
        )
        created.raise_for_status()
        user_id = _id(requests.get(f"{BASE}/admin/realms/{REALM}/users", headers=headers, params={"username": username}, timeout=10).json(), "username", username)
        requests.put(
            f"{BASE}/admin/realms/{REALM}/users/{user_id}/reset-password",
            headers=headers,
            json={"type": "password", "value": password, "temporary": False},
            timeout=10,
        ).raise_for_status()

        metadata = OidcMetadata.discover(f"{BASE}/realms/{REALM}")
        resolver = PkceResolverClient(metadata, client_name, REDIRECT_URI, resource=RESOURCE, resolve_scope=scope_name, identity_scopes="openid profile")
        pending = resolver.begin_authorization()
        browser = requests.Session()
        login_page = browser.get(pending.authorization_url, timeout=10)
        login_page.raise_for_status()
        # Keycloak 26 marks auth cookies Secure even in this HTTP-only local container. A real
        # deployment uses HTTPS; the headless harness changes only its in-memory cookie policy.
        for cookie in browser.cookies:
            cookie.secure = False
        form = re.search(r'<form[^>]+id="kc-form-login"[^>]+action="([^"]+)"', login_page.text)
        if not form:
            raise RuntimeError("Keycloak login form was not found")
        action = html.unescape(form.group(1))
        submitted = browser.post(action, data={"username": username, "password": password, "credentialId": ""}, headers={"Referer": login_page.url}, timeout=10, allow_redirects=False)
        for _ in range(5):
            location = submitted.headers.get("Location", "")
            if location.startswith(REDIRECT_URI):
                break
            if submitted.status_code not in (302, 303) or not location:
                break
            submitted = browser.get(urljoin(action, location), headers={"Referer": action}, timeout=10, allow_redirects=False)
        if submitted.status_code not in (302, 303) or not submitted.headers.get("Location", "").startswith(REDIRECT_URI):
            title = re.search(r"<title>([^<]+)</title>", submitted.text)
            error = re.search(r"(?:kc-feedback-text|alert-error)[^>]*>\s*([^<]+)", submitted.text)
            fields = re.findall(r'<input[^>]+name="([^"]+)"', login_page.text)
            raise RuntimeError(f"Keycloak login did not reach callback (status={submitted.status_code}, page={title.group(1) if title else 'unknown'}, error={error.group(1).strip() if error else 'none'}, action_host={urlparse(action).netloc}, form_fields={fields})")
        access_token = resolver.complete_authorization(submitted.headers["Location"], pending)
        claims = JwtResolverTokenVerifier(metadata, audience=RESOURCE, required_scope=scope_name).verify(access_token)
        subject = claims.get("sub")
        if not subject or scope_name not in set(claims.get("scope", "").split()):
            raise RuntimeError(f"resolved token lacks expected binding (subject={bool(subject)}, scope={scope_name in set(claims.get('scope', '').split())}, claim_names={sorted(claims)})")
        registry = InMemoryIssuer(RESOURCE)
        reference = registry.issue("email", "alice@example.com", principal=subject)
        resolved = TestClient(create_resolve_app(registry, JwtResolverTokenVerifier(metadata, audience=RESOURCE, required_scope=scope_name))).post(
            "/sensitive-references/resolve",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"references": [reference.token], "sink_type": "local_file", "destination": "customers.csv"},
        )
        if not resolved.is_success:
            raise RuntimeError("PKCE-issued resolver token was rejected by the protected resolve endpoint")
        print("verified Authorization Code + PKCE resolver path: state, code exchange, JWKS signature, audience, subject, scope")
        return 0
    finally:
        if user_id:
            requests.delete(f"{BASE}/admin/realms/{REALM}/users/{user_id}", headers=headers, timeout=10)
        if client_id:
            requests.delete(f"{BASE}/admin/realms/{REALM}/clients/{client_id}", headers=headers, timeout=10)
        if scope_id:
            requests.delete(f"{BASE}/admin/realms/{REALM}/client-scopes/{scope_id}", headers=headers, timeout=10)


if __name__ == "__main__":
    sys.exit(main())
