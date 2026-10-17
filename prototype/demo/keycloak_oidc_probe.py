"""One-shot E2E proof: Keycloak issues a resolver token; the PoC verifies it via JWKS.

It creates isolated realm objects and deletes them in ``finally``.  It never prints tokens or
client secrets.  The local E2E Keycloak is deliberately the only supported target.
"""

from __future__ import annotations

import os
import socket
import sys
import threading
import time
from uuid import uuid4

import requests
import uvicorn

from sensitive_references.http_resolver import HttpResolver, ResolverEndpoint
from sensitive_references.issuer import InMemoryIssuer
from sensitive_references.oidc import JwtResolverTokenVerifier, OidcMetadata
from sensitive_references.oauth_profile import RESOLVE_SCOPE
from sensitive_references.resolve_http import create_resolve_app

BASE = os.environ.get("SREF_KEYCLOAK", "http://127.0.0.1:8180")
REALM = "mcpgate"
RESOURCE = "http://localhost:3002/mcp"


def admin_token() -> str:
    response = requests.post(
        f"{BASE}/realms/master/protocol/openid-connect/token",
        data={"grant_type": "password", "client_id": "admin-cli", "username": "admin", "password": "admin"},
        timeout=10,
    )
    response.raise_for_status()
    return response.json()["access_token"]


def main() -> int:
    token = admin_token()
    headers = {"Authorization": f"Bearer {token}"}
    client_id = f"sref-resolver-poc-{uuid4().hex[:10]}"
    scope_name = f"{RESOLVE_SCOPE}-{uuid4().hex[:10]}"
    client_uuid = scope_uuid = None
    try:
        scope = requests.post(
            f"{BASE}/admin/realms/{REALM}/client-scopes",
            headers=headers,
            json={"name": scope_name, "protocol": "openid-connect", "attributes": {"include.in.token.scope": "true"}},
            timeout=10,
        )
        scope.raise_for_status()
        scopes = requests.get(f"{BASE}/admin/realms/{REALM}/client-scopes", headers=headers, params={"search": scope_name}, timeout=10).json()
        scope_uuid = next(item["id"] for item in scopes if item["name"] == scope_name)
        client = requests.post(
            f"{BASE}/admin/realms/{REALM}/clients",
            headers=headers,
            json={
                "clientId": client_id,
                "enabled": True,
                "publicClient": False,
                "serviceAccountsEnabled": True,
                "standardFlowEnabled": True,
                "fullScopeAllowed": False,
                "defaultClientScopes": [scope_name],
                "redirectUris": ["http://127.0.0.1:8765/callback"],
            },
            timeout=10,
        )
        client.raise_for_status()
        clients = requests.get(f"{BASE}/admin/realms/{REALM}/clients", headers=headers, params={"clientId": client_id}, timeout=10).json()
        client_uuid = next(item["id"] for item in clients if item["clientId"] == client_id)
        mapper = requests.post(
            f"{BASE}/admin/realms/{REALM}/clients/{client_uuid}/protocol-mappers/models",
            headers=headers,
            json={
                "name": "sref-resource-audience",
                "protocol": "openid-connect",
                "protocolMapper": "oidc-audience-mapper",
                "config": {"included.custom.audience": RESOURCE, "access.token.claim": "true", "id.token.claim": "false"},
            },
            timeout=10,
        )
        mapper.raise_for_status()
        secret = requests.get(f"{BASE}/admin/realms/{REALM}/clients/{client_uuid}/client-secret", headers=headers, timeout=10).json()["value"]
        issued = requests.post(
            f"{BASE}/realms/{REALM}/protocol/openid-connect/token",
            data={"grant_type": "client_credentials", "client_id": client_id, "client_secret": secret, "scope": scope_name},
            timeout=10,
        )
        issued.raise_for_status()
        access_token = issued.json()["access_token"]
        metadata = OidcMetadata.discover(f"{BASE}/realms/{REALM}")
        verifier = JwtResolverTokenVerifier(metadata, audience=RESOURCE, required_scope=scope_name)
        claims = verifier.verify(access_token)
        # The temporary scope name proves scope propagation; policy scope follows in a real realm.
        if scope_name not in set(claims.get("scope", "").split()):
            raise RuntimeError("Keycloak did not propagate the temporary resolver scope")
        registry = InMemoryIssuer(RESOURCE)
        reference = registry.issue("email", "alice@example.com", principal=claims["sub"])
        app = create_resolve_app(registry, verifier)
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            port = listener.getsockname()[1]
        server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error"))
        thread = threading.Thread(target=server.run, daemon=True)
        thread.start()
        try:
            for _ in range(50):
                if server.started:
                    break
                time.sleep(0.02)
            else:
                raise RuntimeError("resolver endpoint did not start")
            resolved = HttpResolver({RESOURCE: ResolverEndpoint(f"http://127.0.0.1:{port}/sensitive-references/resolve", lambda: access_token)}).resolve(
                RESOURCE,
                [reference.token],
                type("Context", (), {"sink_type": "local_file", "destination": "customers.csv", "principal": claims["sub"]})(),
            )
            if resolved.get(reference.token) != "alice@example.com":
                raise RuntimeError("resolve endpoint did not materialize the issued value")
        finally:
            server.should_exit = True
            thread.join(timeout=5)
        print("verified complete Keycloak resolver path: issuer-bound HTTP endpoint, signature, audience, scope, subject binding")
        return 0
    finally:
        if client_uuid:
            requests.delete(f"{BASE}/admin/realms/{REALM}/clients/{client_uuid}", headers=headers, timeout=10)
        if scope_uuid:
            requests.delete(f"{BASE}/admin/realms/{REALM}/client-scopes/{scope_uuid}", headers=headers, timeout=10)


if __name__ == "__main__":
    sys.exit(main())
