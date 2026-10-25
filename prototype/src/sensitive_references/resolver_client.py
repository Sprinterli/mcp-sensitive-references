"""Host-side client for the OAuth Resolver Profile (``oauth-resolver-1``).

Stdlib only. It discovers the protected resource and its authorization server,
gets a resolver token (cache, refresh, or Authorization Code + PKCE S256 with a
loopback redirect and dynamic client registration), and calls the resolve
endpoint for one issuer. Nothing here is specific to one server.

The resolver token is a second credential. It is never the MCP agent token, it
goes only to the configured resolve endpoint and the authorization server, and
no error text of this module holds a token, a reference or a value.
"""

from __future__ import annotations

from base64 import urlsafe_b64encode
from dataclasses import dataclass
from hashlib import sha256
from http.server import BaseHTTPRequestHandler, HTTPServer
import hmac
import ipaddress
import json
import os
from pathlib import Path
import re
import secrets
import tempfile
import threading
import time
from typing import Any, Callable, Sequence
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from .oauth_profile import RESOLVE_SCOPE
from .resolver import ResolutionError, SinkContext

RESOLVER_PROFILE = "oauth-resolver-1"
SINK_PROFILE = "local-file-1"
#: The provisional field of RFC 9728 protected-resource metadata (not in concept 0.5).
DISCOVERY_FIELD = "sensitive_references"
MAX_BATCH = 100
#: A cached access token counts as expired this many seconds before its stated end.
EXPIRY_SKEW = 30
_CODE = re.compile(r"[A-Za-z0-9_.-]{1,64}")


class ResolverClientError(ResolutionError):
    """A failure with a short, safe code. The message never holds a credential or a value."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


# ---------------------------------------------------------------- HTTP


class _NoRedirect(HTTPRedirectHandler):
    # A redirect could carry the Authorization header to another origin.
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: D401
        return None


_OPENER = build_opener(_NoRedirect)


def _is_loopback(host: str | None) -> bool:
    if host is None:
        return False
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def require_secure(url: str, what: str) -> str:
    """Allow ``https``, or ``http`` on a loopback host only."""
    parts = urlsplit(url)
    if parts.scheme == "https" or (parts.scheme == "http" and _is_loopback(parts.hostname)):
        if parts.username or parts.password:
            raise ResolverClientError("insecure_url", f"the {what} URL holds credentials")
        return url
    raise ResolverClientError("insecure_url", f"the {what} URL is not https or loopback http")


def origin(url: str) -> tuple[str, str, int | None]:
    parts = urlsplit(url)
    port = parts.port or {"https": 443, "http": 80}.get(parts.scheme)
    return parts.scheme, (parts.hostname or ""), port


def http_json(method: str, url: str, *, body: bytes | None = None, headers: dict[str, str] | None = None,
              timeout: float = 10.0) -> tuple[int, Any]:
    """One request without redirects. Returns the status and the JSON body (or None)."""
    request = Request(url, data=body, method=method, headers=headers or {})
    try:
        with _OPENER.open(request, timeout=timeout) as response:  # nosec B310: URLs pass require_secure
            status, raw = response.status, response.read()
    except HTTPError as error:
        try:
            status, raw = error.code, error.read()
        finally:
            error.close()
    except (URLError, OSError) as error:
        raise ResolverClientError("unreachable", f"the server did not answer ({type(error).__name__})") from None
    try:
        return status, json.loads(raw) if raw else None
    except ValueError:
        return status, None


def _form(url: str, fields: dict[str, str], timeout: float) -> tuple[int, Any]:
    return http_json("POST", url, body=urlencode(fields).encode(), timeout=timeout,
                     headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"})


# ---------------------------------------------------------------- discovery


def _well_known(url: str, suffix: str, *, insert: bool) -> str:
    parts = urlsplit(url)
    path = parts.path.rstrip("/")
    full = f"/.well-known/{suffix}{path}" if insert else f"{path}/.well-known/{suffix}"
    return urlunsplit((parts.scheme, parts.netloc, full, "", ""))


@dataclass(frozen=True)
class ProtectedResource:
    resource: str
    authorization_servers: tuple[str, ...]
    resolve_endpoint: str | None = None
    resolve_scope: str | None = None
    resolver_profiles: tuple[str, ...] | None = None
    sink_profiles: tuple[str, ...] | None = None


def discover_protected_resource(resource: str, *, timeout: float = 10.0) -> ProtectedResource | None:
    """RFC 9728 metadata of ``resource``: path-inserted URL first, then the root URL.

    Returns None when no metadata exists. The metadata is refused when its
    ``resource`` is not exactly ``resource`` (RFC 9728, section 3.3).
    """
    require_secure(resource, "protected resource")
    candidates = [_well_known(resource, "oauth-protected-resource", insert=True)]
    root = urlunsplit((*urlsplit(resource)[:2], "/.well-known/oauth-protected-resource", "", ""))
    if root not in candidates:
        candidates.append(root)
    for url in candidates:
        status, document = http_json("GET", url, headers={"Accept": "application/json"}, timeout=timeout)
        if status != 200 or not isinstance(document, dict):
            continue
        if document.get("resource") != resource:
            raise ResolverClientError("wrong_issuer", "the protected-resource metadata names another resource")
        servers = document.get("authorization_servers") or []
        extra = document.get(DISCOVERY_FIELD)
        extra = extra if isinstance(extra, dict) else {}

        def _list(name):
            value = extra.get(name)
            return tuple(v for v in value if isinstance(v, str)) if isinstance(value, list) else None

        return ProtectedResource(
            resource=resource,
            authorization_servers=tuple(s for s in servers if isinstance(s, str)),
            resolve_endpoint=extra.get("resolve_endpoint") if isinstance(extra.get("resolve_endpoint"), str) else None,
            resolve_scope=extra.get("resolve_scope") if isinstance(extra.get("resolve_scope"), str) else None,
            resolver_profiles=_list("resolver_profiles"),
            sink_profiles=_list("sink_profiles"),
        )
    return None


@dataclass(frozen=True)
class AuthorizationServer:
    issuer: str
    authorization_endpoint: str
    token_endpoint: str
    registration_endpoint: str | None = None
    iss_parameter_supported: bool = False


def discover_authorization_server(issuer: str, *, timeout: float = 10.0) -> AuthorizationServer:
    """RFC 8414 metadata, then OpenID Connect discovery. The ``issuer`` must match exactly."""
    require_secure(issuer, "authorization server")
    candidates = [_well_known(issuer, "oauth-authorization-server", insert=True),
                  _well_known(issuer, "openid-configuration", insert=True),
                  _well_known(issuer, "openid-configuration", insert=False)]
    for url in dict.fromkeys(candidates):
        status, document = http_json("GET", url, headers={"Accept": "application/json"}, timeout=timeout)
        if status != 200 or not isinstance(document, dict):
            continue
        if document.get("issuer") != issuer:
            raise ResolverClientError("wrong_authorization_server", "the authorization server metadata names another issuer")
        methods = document.get("code_challenge_methods_supported")
        if methods is not None and "S256" not in methods:
            raise ResolverClientError("no_pkce_s256", "the authorization server does not support PKCE S256")
        return AuthorizationServer(
            issuer=issuer,
            authorization_endpoint=require_secure(document["authorization_endpoint"], "authorization endpoint"),
            token_endpoint=require_secure(document["token_endpoint"], "token endpoint"),
            registration_endpoint=(require_secure(document["registration_endpoint"], "registration endpoint")
                                   if document.get("registration_endpoint") else None),
            iss_parameter_supported=bool(document.get("authorization_response_iss_parameter_supported")),
        )
    raise ResolverClientError("no_authorization_server", "no authorization server metadata found")


# ---------------------------------------------------------------- token cache


class TokenCache:
    """A JSON file with mode 0600. A file that others can read is refused, not repaired."""

    def __init__(self, path: Path | str | None) -> None:
        self.path = Path(path).expanduser() if path else None

    def _read_all(self) -> dict[str, Any]:
        if self.path is None or not self.path.exists():
            return {}
        if self.path.stat().st_mode & 0o077:
            raise ResolverClientError("token_cache_permissions", "the resolver token cache is readable by others")
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except ValueError:
            return {}
        return data if isinstance(data, dict) else {}

    def load(self, key: str) -> dict[str, Any] | None:
        entry = self._read_all().get(key)
        return entry if isinstance(entry, dict) else None

    def store(self, key: str, entry: dict[str, Any] | None) -> None:
        if self.path is None:
            return
        data = self._read_all()
        if entry is None:
            data.pop(key, None)
        else:
            data[key] = entry
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix=".sref-tokens-", dir=self.path.parent)
        try:
            os.fchmod(fd, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(data, handle)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self.path)
        except Exception:
            Path(temporary).unlink(missing_ok=True)
            raise


# ---------------------------------------------------------------- loopback


class _Callback(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        parts = urlsplit(self.path)
        if parts.path != "/callback":
            self.send_response(404)
            self.end_headers()
            return
        self.server.query = parse_qs(parts.query)  # type: ignore[attr-defined]
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"The resolver authorization is complete. You can close this window.\n")

    def log_message(self, *args):  # the query holds the code
        pass


def _pkce() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(48)
    return verifier, urlsafe_b64encode(sha256(verifier.encode()).digest()).rstrip(b"=").decode()


# ---------------------------------------------------------------- credential


class OAuthResolverCredential:
    """The resolver token for one protected resource, one authorization server and one scope.

    ``access_token()`` returns a cached token, refreshes an expired one, or runs
    an interactive authorization. ``renew()`` gets one new token after the
    resolve endpoint refused the current one. ``source`` names where the last
    token came from: ``cache``, ``refresh`` or ``interactive``.
    """

    def __init__(self, *, resource: str, authorization_server: str, scope: str = RESOLVE_SCOPE,
                 cache: TokenCache, metadata: Callable[[], AuthorizationServer] | None = None,
                 open_browser: Callable[[str], Any] | None = None, interactive: bool = True,
                 client_id: str | None = None, client_name: str = "Sensitive References host",
                 authorization_timeout: float = 300.0, timeout: float = 10.0,
                 clock: Callable[[], float] = time.time) -> None:
        self.resource = resource
        self.authorization_server = authorization_server
        self.scope = scope
        self.cache = cache
        self._metadata_provider = metadata or (lambda: discover_authorization_server(authorization_server, timeout=timeout))
        self._metadata: AuthorizationServer | None = None
        self.open_browser = open_browser
        self.interactive = interactive
        self.client_id = client_id
        self.client_name = client_name
        self.authorization_timeout = authorization_timeout
        self.timeout = timeout
        self.clock = clock
        self.source: str | None = None
        self.key = json.dumps([resource, authorization_server, scope])

    def metadata(self) -> AuthorizationServer:
        if self._metadata is None:
            self._metadata = self._metadata_provider()
        return self._metadata

    # -- public

    def access_token(self) -> str:
        entry = self.cache.load(self.key)
        if entry and entry.get("access_token"):
            expires_at = entry.get("expires_at")
            if expires_at is None or self.clock() < expires_at - EXPIRY_SKEW:
                self.source = "cache"
                return entry["access_token"]
        return self.renew(entry)

    def renew(self, entry: dict[str, Any] | None = None) -> str:
        """One new token: refresh when a refresh token exists, else interactive authorization."""
        entry = entry if entry is not None else self.cache.load(self.key)
        if entry and entry.get("refresh_token"):
            try:
                return self._refresh(entry)
            except ResolverClientError:
                self.cache.store(self.key, None)
        if not self.interactive:
            raise ResolverClientError("unauthorized", "no valid resolver token and interactive authorization is off")
        return self._authorize()

    def forget_access_token(self) -> None:
        entry = self.cache.load(self.key)
        if entry:
            entry = {k: v for k, v in entry.items() if k not in ("access_token", "expires_at")}
            self.cache.store(self.key, entry)

    # -- token endpoint

    def _accept(self, document: Any, client_id: str, previous: dict[str, Any] | None) -> str:
        if not isinstance(document, dict) or not isinstance(document.get("access_token"), str):
            raise ResolverClientError("token_response", "the token endpoint returned no access token")
        if str(document.get("token_type", "")).lower() != "bearer":
            raise ResolverClientError("token_response", "the token endpoint returned no bearer token")
        granted = document.get("scope")
        if isinstance(granted, str) and self.scope not in granted.split():
            raise ResolverClientError("scope_not_granted", "the authorization server did not grant the resolve scope")
        entry = {"client_id": client_id, "access_token": document["access_token"]}
        if isinstance(document.get("expires_in"), (int, float)):
            entry["expires_at"] = self.clock() + float(document["expires_in"])
        # Refresh tokens rotate: a new one replaces the old one; without a new one keep the old one.
        refresh = document.get("refresh_token") or (previous or {}).get("refresh_token")
        if refresh:
            entry["refresh_token"] = refresh
        self.cache.store(self.key, entry)
        return document["access_token"]

    def _refresh(self, entry: dict[str, Any]) -> str:
        client_id = entry.get("client_id") or self.client_id
        status, document = _form(self.metadata().token_endpoint, {
            "grant_type": "refresh_token", "refresh_token": entry["refresh_token"], "client_id": client_id,
            "resource": self.resource, "scope": self.scope}, self.timeout)
        if status != 200:
            raise ResolverClientError("refresh_failed", "the refresh was refused")
        token = self._accept(document, client_id, {k: v for k, v in entry.items() if k != "refresh_token"})
        self.source = "refresh"
        return token

    # -- interactive authorization

    def _register(self, redirect_uri: str) -> str:
        if self.client_id:
            return self.client_id
        endpoint = self.metadata().registration_endpoint
        if not endpoint:
            raise ResolverClientError("no_client", "no client_id and no dynamic client registration")
        body = json.dumps({"client_name": self.client_name, "redirect_uris": [redirect_uri],
                           "grant_types": ["authorization_code", "refresh_token"], "response_types": ["code"],
                           "token_endpoint_auth_method": "none", "scope": self.scope}).encode()
        status, document = http_json("POST", endpoint, body=body, timeout=self.timeout,
                                     headers={"Content-Type": "application/json", "Accept": "application/json"})
        if status not in (200, 201) or not isinstance(document, dict) or not document.get("client_id"):
            raise ResolverClientError("registration_failed", "the dynamic client registration failed")
        return document["client_id"]

    def _authorize(self) -> str:
        metadata = self.metadata()
        server = HTTPServer(("127.0.0.1", 0), _Callback)
        server.query = None  # type: ignore[attr-defined]
        server.timeout = 0.2
        redirect_uri = f"http://127.0.0.1:{server.server_address[1]}/callback"
        try:
            client_id = self._register(redirect_uri)
            verifier, challenge = _pkce()
            state = secrets.token_urlsafe(24)
            url = metadata.authorization_endpoint + ("&" if "?" in metadata.authorization_endpoint else "?") + urlencode({
                "response_type": "code", "client_id": client_id, "redirect_uri": redirect_uri,
                "scope": self.scope, "resource": self.resource, "state": state,
                "code_challenge": challenge, "code_challenge_method": "S256"})
            stop = threading.Event()

            def _serve():
                while not stop.is_set() and server.query is None:  # type: ignore[attr-defined]
                    server.handle_request()

            if self.open_browser is None:
                raise ResolverClientError("no_browser", "no way to open the authorization page")
            thread = threading.Thread(target=_serve, daemon=True)
            thread.start()
            try:
                self.open_browser(url)
                thread.join(self.authorization_timeout)
            finally:
                stop.set()
                thread.join(1)
            query = server.query  # type: ignore[attr-defined]
        finally:
            server.server_close()
        if query is None:
            raise ResolverClientError("authorization_timeout", "the authorization did not complete in time")
        if not hmac.compare_digest((query.get("state") or [""])[0], state):
            raise ResolverClientError("state_mismatch", "the authorization callback state did not match")
        returned_iss = (query.get("iss") or [None])[0]
        if (returned_iss is not None or metadata.iss_parameter_supported) and returned_iss != metadata.issuer:
            raise ResolverClientError("issuer_mismatch", "the authorization callback came from another issuer")
        if query.get("error"):
            raise ResolverClientError("authorization_denied", "the authorization was denied")
        code = (query.get("code") or [None])[0]
        if not code:
            raise ResolverClientError("no_code", "the authorization callback held no code")
        status, document = _form(metadata.token_endpoint, {
            "grant_type": "authorization_code", "code": code, "redirect_uri": redirect_uri,
            "client_id": client_id, "code_verifier": verifier, "resource": self.resource}, self.timeout)
        if status != 200:
            raise ResolverClientError("token_exchange_failed", "the code exchange was refused")
        token = self._accept(document, client_id, None)
        self.source = "interactive"
        return token


# ---------------------------------------------------------------- resolver


@dataclass(frozen=True)
class ResolveEndpoint:
    url: str
    credential: OAuthResolverCredential


class OAuthHttpResolver:
    """``Resolver`` for ``ProtectedFileSink``: one resolve endpoint per trusted issuer.

    It sends only the resolver token, never ``agent_token``. A 401 gets one
    renewed token and one retry. Any other answer than a complete 200 batch is
    a failure, and the sink then writes nothing.
    """

    def __init__(self, endpoints: dict[str, ResolveEndpoint], *, agent_token: str | None = None,
                 timeout: float = 10.0) -> None:
        self._endpoints = endpoints
        self._agent_token = agent_token or None
        self._timeout = timeout
        self.requests = 0

    def resolve(self, issuer: str, references: Sequence[str], sink_context: SinkContext) -> dict[str, str]:
        endpoint = self._endpoints.get(issuer)
        if endpoint is None:
            raise ResolverClientError("wrong_issuer", "the issuer has no configured resolve endpoint")
        if sink_context.sink_type != "local_file":
            raise ResolverClientError("ineligible_sink", "the sink is not a local file")
        require_secure(endpoint.url, "resolve endpoint")
        unique = list(dict.fromkeys(references))
        values: dict[str, str] = {}
        # All batches resolve before the sink writes anything.
        for start in range(0, len(unique), MAX_BATCH):
            values.update(self._batch(endpoint, unique[start:start + MAX_BATCH], sink_context))
        return values

    def _batch(self, endpoint: ResolveEndpoint, batch: list[str], context: SinkContext) -> dict[str, str]:
        body = json.dumps({"references": batch, "sink_type": context.sink_type,
                           "destination": context.destination}).encode()
        token = endpoint.credential.access_token()
        renewed = False
        while True:
            if self._agent_token is not None and hmac.compare_digest(token, self._agent_token):
                raise ResolverClientError("agent_token", "the resolver token is the MCP agent token")
            self.requests += 1
            status, document = http_json("POST", endpoint.url, body=body, timeout=self._timeout, headers={
                "Authorization": f"Bearer {token}", "Content-Type": "application/json", "Accept": "application/json"})
            if status == 401 and not renewed:
                renewed = True
                endpoint.credential.forget_access_token()
                token = endpoint.credential.renew()
                continue
            break
        if status == 401:
            endpoint.credential.forget_access_token()
        if status != 200:
            code = document.get("error") if isinstance(document, dict) else None
            code = code if isinstance(code, str) and _CODE.fullmatch(code) else "error"
            raise ResolverClientError(code, f"the resolve endpoint refused the batch (HTTP {status}, {code})")
        values = document.get("values") if isinstance(document, dict) else None
        if (not isinstance(values, dict) or set(values) != set(batch)
                or not all(isinstance(v, str) for v in values.values())):
            raise ResolverClientError("malformed_batch", "the resolve endpoint returned an incomplete or extra batch")
        return values
