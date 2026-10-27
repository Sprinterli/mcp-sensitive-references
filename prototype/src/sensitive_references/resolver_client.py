"""Host-side client for the OAuth Resolver Profile (``oauth-resolver-1``).

Stdlib only. It discovers the protected resource and its authorization server,
gets a resolver token (cache, refresh, or Authorization Code + PKCE S256 with a
loopback redirect and dynamic client registration), and calls the resolve
endpoint for one issuer. Nothing here is specific to one server.

The resolver token is a second credential. It is never the MCP agent token, it
goes only to the resolve endpoint (on the origin of the resource) and the
authorization server, and
no error text of this module holds a token, a reference or a value.
"""

from __future__ import annotations

from base64 import urlsafe_b64encode
from dataclasses import dataclass
from hashlib import sha256
from functools import partial
import http.client
from http.server import BaseHTTPRequestHandler, HTTPServer
import hmac
import ipaddress
import json
import os
from pathlib import Path
import re
import secrets
import socket
import tempfile
import threading
import time
from typing import Any, Callable, Sequence
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit
from urllib.request import HTTPHandler, HTTPRedirectHandler, HTTPSHandler, ProxyHandler, Request, build_opener

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


class _PinnedHTTPConnection(http.client.HTTPConnection):
    # Connects to the address that the fetch policy checked, not to a new DNS answer (DNS rebinding).
    def __init__(self, *args, address: str, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._address = address

    def connect(self) -> None:
        self.sock = socket.create_connection((self._address, self.port), self.timeout)


class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    # TLS still verifies the certificate for the host name of the URL.
    def __init__(self, *args, address: str, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._address = address

    def connect(self) -> None:
        sock = socket.create_connection((self._address, self.port), self.timeout)
        self.sock = self._context.wrap_socket(sock, server_hostname=self.host)


def _pinned_address(req: Request) -> str:
    address = getattr(req, "pinned_address", None)
    if not address:
        raise URLError("no checked address for the request")
    return address


class _PinnedHTTP(HTTPHandler):
    def http_open(self, req):
        return self.do_open(partial(_PinnedHTTPConnection, address=_pinned_address(req)), req)


class _PinnedHTTPS(HTTPSHandler):
    def https_open(self, req):
        return self.do_open(partial(_PinnedHTTPSConnection, address=_pinned_address(req)), req,
                            context=self._context)


def _new_opener():
    # No redirect (SC-01, SC-04) and no proxy from the environment: the fetch policy checks the
    # address that the request goes to, and a proxy would choose another one. The connection goes
    # to the checked address (``Request.pinned_address``); without one the request fails.
    return build_opener(ProxyHandler({}), _NoRedirect, _PinnedHTTP, _PinnedHTTPS)


_OPENER = _new_opener()


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


#: Never a target, also not in local mode: link-local (with the cloud-metadata address 169.254.169.254),
#: unspecified ("this network") and the limited broadcast address. Multicast is tested by ``is_multicast``.
_NEVER = tuple(ipaddress.ip_network(n) for n in (
    "169.254.0.0/16", "fe80::/10", "0.0.0.0/8", "::/128", "255.255.255.255/32"))
_NAT64 = ipaddress.ip_network("64:ff9b::/96")
_COMPATIBLE = ipaddress.ip_network("::/96")


def _ip(address: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address:
    return ipaddress.ip_address(address.split("%", 1)[0])


def _embedded_ipv4(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> ipaddress.IPv4Address | None:
    """The IPv4 address in an IPv4-mapped, IPv4-compatible, NAT64 (64:ff9b::/96) or 6to4 address."""
    if not isinstance(ip, ipaddress.IPv6Address):
        return None
    if ip.ipv4_mapped is not None:
        return ip.ipv4_mapped
    if ip.sixtofour is not None:
        return ip.sixtofour
    if ip in _NAT64 or (ip in _COMPATIBLE and int(ip) > 1):
        return ipaddress.IPv4Address(int(ip) & 0xFFFFFFFF)
    return None


def non_public_address(address: str) -> bool:
    """True when ``address`` (an IP literal) is not globally reachable.

    Not globally reachable: ``is_global`` is false (the IANA IPv4 and IPv6 Special-Purpose Address
    Registries, as Python 3.13 or later implements them), a multicast address, an IPv6 site-local address
    (fec0::/10, RFC 3879), or an address whose embedded IPv4 address (IPv4-mapped, IPv4-compatible,
    NAT64 64:ff9b::/96, 6to4) is not globally reachable.
    """
    ip = _ip(address)
    if not ip.is_global or ip.is_multicast or (isinstance(ip, ipaddress.IPv6Address) and ip.is_site_local):
        return True
    embedded = _embedded_ipv4(ip)
    return embedded is not None and non_public_address(str(embedded))


def never_a_target(address: str) -> bool:
    """True for a link-local, unspecified, broadcast or multicast address, also an embedded one."""
    ip = _ip(address)
    embedded = _embedded_ipv4(ip)
    return any(i.is_multicast or any(i in n for n in _NEVER if i.version == n.version)
               for i in (ip, embedded) if i is not None)


def _lookup(host: str) -> list[str]:
    """The addresses of ``host`` from DNS. Tests replace this function."""
    return [info[4][0] for info in socket.getaddrinfo(host, None, proto=socket.IPPROTO_TCP)]


def _addresses(host: str | None) -> list[str] | None:
    """The addresses of ``host``: the literal, or the DNS answer. None if the name does not resolve."""
    if not host:
        return None
    if host.lower() == "localhost":
        return ["127.0.0.1", "::1"]
    try:
        return [str(_ip(host))]
    except ValueError:
        pass
    try:
        return _lookup(host) or None
    except OSError:
        return None


class FetchPolicy:
    """The fetch policy of the host for one MCP URL (SC-01, D11, RFC 9728 section 7.7).

    ``_exchange`` applies it before each request, and the discovery of the
    authorization server applies it to the endpoints that the host uses. The
    host resolves each host name by DNS. If one address is not globally
    reachable, or the name does not resolve, the host refuses the URL.

    Local mode: only if the operator sets ``allow_local`` and all addresses of
    the MCP host are not globally reachable. The constructor resolves the MCP
    host once (at connection) and keeps the result. In local mode the host
    allows a non-public target only on the MCP origin or on an origin of
    ``local_origins`` (exact scheme, host and port), and never a link-local,
    unspecified, broadcast or multicast address. ``_exchange`` connects to
    an address that ``targets`` checked, so a second DNS answer cannot change
    the target (DNS rebinding).
    """

    def __init__(self, mcp_url: str, *, allow_local: bool = False,
                 local_origins: Sequence[str] = ()) -> None:
        self.protected_resource = mcp_url
        self.mcp_addresses = _addresses(urlsplit(mcp_url).hostname)
        self.local = bool(allow_local and self.mcp_addresses
                          and all(non_public_address(a) for a in self.mcp_addresses))
        self.local_origins = frozenset({origin(mcp_url), *(origin(o) for o in local_origins)})

    def check(self, url: str, what: str) -> str:
        self.targets(url, what)
        return url

    def targets(self, url: str, what: str) -> list[str]:
        """The checked addresses of ``url``. The request connects to one of them."""
        addresses = _addresses(urlsplit(url).hostname)
        if addresses is not None and not any(non_public_address(a) for a in addresses):
            return addresses
        if (self.local and addresses is not None and origin(url) in self.local_origins
                and not any(never_a_target(a) for a in addresses)):
            return addresses
        raise ResolverClientError(
            "forbidden_target", f"the {what} URL is on a non-public address or does not resolve")


def origin(url: str) -> tuple[str, str, int | None]:
    parts = urlsplit(url)
    port = parts.port or {"https": 443, "http": 80}.get(parts.scheme)
    return parts.scheme, (parts.hostname or ""), port


def _exchange(method: str, url: str, *, policy: FetchPolicy, body: bytes | None = None,
              headers: dict[str, str] | None = None, timeout: float = 10.0,
              read: bool = True) -> tuple[int, Any, bytes]:
    """One request without redirects. Returns the status, the headers and the body.

    ``policy`` checks the target before the request. With ``read=False`` the
    body of a success answer is not read (a stream could hold the call open).
    """
    addresses = policy.targets(url, "request")
    request = Request(url, data=body, method=method, headers=headers or {})
    request.pinned_address = addresses[0]
    try:
        with _OPENER.open(request, timeout=timeout) as response:  # nosec B310: URLs pass require_secure
            return response.status, response.headers, (response.read() if read else b"")
    except HTTPError as error:
        try:
            return error.code, error.headers, error.read()
        finally:
            error.close()
    except (URLError, OSError) as error:
        raise ResolverClientError("unreachable", f"the server did not answer ({type(error).__name__})") from None


def http_json(method: str, url: str, *, policy: FetchPolicy, body: bytes | None = None,
              headers: dict[str, str] | None = None, timeout: float = 10.0) -> tuple[int, Any]:
    """One request without redirects. Returns the status and the JSON body (or None)."""
    status, _, raw = _exchange(method, url, policy=policy, body=body, headers=headers, timeout=timeout)
    try:
        return status, json.loads(raw) if raw else None
    except ValueError:
        return status, None


def _form(url: str, fields: dict[str, str], timeout: float, policy: FetchPolicy) -> tuple[int, Any]:
    return http_json("POST", url, policy=policy, body=urlencode(fields).encode(), timeout=timeout,
                     headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"})


# ---------------------------------------------------------------- discovery


def _well_known(url: str, suffix: str, *, insert: bool, strip_slash: bool = False) -> str:
    """The well-known URL of ``url``.

    ``insert``: RFC 9728 section 3.1 and RFC 8414 section 3.1. The well-known
    string goes between the host and the path and query. For RFC 9728 only a
    path of "/" alone is removed; the query and a trailing slash of a longer
    path stay. With ``strip_slash`` (RFC 8414 section 3.1, an issuer) the host
    removes any terminating "/" of the path. Else OpenID Connect Discovery 1.0
    section 4: append to the path.
    """
    parts = urlsplit(url)
    if insert:
        path = parts.path.rstrip("/") if strip_slash else ("" if parts.path == "/" else parts.path)
        return urlunsplit((parts.scheme, parts.netloc, f"/.well-known/{suffix}{path}", parts.query, ""))
    return urlunsplit((parts.scheme, parts.netloc, f"{parts.path.rstrip('/')}/.well-known/{suffix}", "", ""))


def protected_resource_metadata_url(resource: str) -> str:
    """The path-inserted RFC 9728 well-known URL of ``resource`` (section 3.1)."""
    return _well_known(resource, "oauth-protected-resource", insert=True)


def require_resource_identifier(resource: str) -> str:
    """A resource identifier as RFC 9728 section 1.2 allows it: secure, without a fragment.

    The string is returned as given. User information is refused, because it is a credential.
    """
    require_secure(resource, "protected resource")
    if "#" in resource:
        raise ResolverClientError("invalid_resource", "the protected-resource identifier holds a fragment")
    return resource


@dataclass(frozen=True)
class ProtectedResource:
    resource: str
    authorization_servers: tuple[str, ...]
    #: True when the metadata holds the discovery object. Then the four members below are set and valid.
    discovery: bool = False
    resolve_endpoint: str | None = None
    resolve_scope: str | None = None
    resolver_profiles: tuple[str, ...] | None = None
    sink_profiles: tuple[str, ...] | None = None


#: The ``resource_metadata`` parameter of a ``WWW-Authenticate`` challenge (RFC 9728, section 5.1).
_RESOURCE_METADATA = re.compile(r'(?i)(?:^|[\s,])resource_metadata\s*=\s*"([^"]*)"')


def challenge_metadata_url(resource: str, *, policy: FetchPolicy | None = None,
                           timeout: float = 10.0) -> str | None:
    """The metadata URL that the resource names in the ``WWW-Authenticate`` header of its 401 answer
    to a request without a token (RFC 9728, section 5.1). None if the answer names none."""
    policy = policy or FetchPolicy(resource)
    status, headers, _ = _exchange("POST", resource, policy=policy, body=b"{}", timeout=timeout, read=False, headers={
        "Content-Type": "application/json", "Accept": "application/json, text/event-stream"})
    if status != 401 or headers is None:
        return None
    for value in headers.get_all("WWW-Authenticate") or []:
        match = _RESOURCE_METADATA.search(value)
        if match:
            return match.group(1)
    return None


def _metadata_document(url: str, timeout: float, policy: FetchPolicy) -> dict[str, Any] | None:
    status, document = http_json("GET", url, policy=policy, headers={"Accept": "application/json"},
                                 timeout=timeout)
    return document if status == 200 and isinstance(document, dict) else None


def _discovery_object(document: dict[str, Any]) -> dict[str, Any] | None:
    """The ``sensitive_references`` object, or None when the metadata has none.

    A present object must have all four members with the right types (SC-02). The
    host does not put a default in place of a missing or malformed member.
    """
    if DISCOVERY_FIELD not in document:
        return None
    extra = document[DISCOVERY_FIELD]
    if not isinstance(extra, dict):
        raise ResolverClientError("malformed_discovery", "the discovery object is not a JSON object")
    for name in ("resolve_endpoint", "resolve_scope"):
        if not isinstance(extra.get(name), str) or not extra[name]:
            raise ResolverClientError("malformed_discovery", f"the discovery object has no valid {name}")
    for name in ("resolver_profiles", "sink_profiles"):
        value = extra.get(name)
        if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
            raise ResolverClientError("malformed_discovery", f"the discovery object has no valid {name}")
    return extra


def discover_protected_resource(resource: str, *, use_challenge: bool = True, policy: FetchPolicy | None = None,
                                timeout: float = 10.0) -> ProtectedResource | None:
    """RFC 9728 metadata of ``resource``.

    The order is the order of the MCP authorization specification. First, if
    ``use_challenge`` is set, the ``resource_metadata`` URL of the 401 answer of
    ``resource`` itself (section 5.1). If the answer names a URL, the host uses
    that URL only. Else the path-inserted well-known URL of ``resource``
    (section 3.1). The host tries no other URL, also not the origin root (SC-01
    differs here from the MCP fallback). The metadata ``resource`` must be
    identical to ``resource`` as an exact string (section 3.3). Returns None
    when no metadata exists. A URL that the challenge names must pass
    ``policy`` (section 7.7) and must give a document, because the challenge
    says that metadata exists. A present discovery object that is malformed is
    refused.
    """
    require_resource_identifier(resource)
    policy = policy or FetchPolicy(resource)
    named = challenge_metadata_url(resource, policy=policy, timeout=timeout) if use_challenge else None
    if named is not None:
        document = _metadata_document(require_secure(named, "protected-resource metadata"), timeout, policy)
        if document is None:
            raise ResolverClientError("metadata_unavailable", "the metadata URL of the challenge gave no document")
    else:
        document = _metadata_document(protected_resource_metadata_url(resource), timeout, policy)
    if document is None:
        return None
    if document.get("resource") != resource:
        raise ResolverClientError("wrong_issuer", "the protected-resource metadata names another resource")
    servers = document.get("authorization_servers") or []
    servers = tuple(s for s in servers if isinstance(s, str)) if isinstance(servers, list) else ()
    extra = _discovery_object(document)
    if extra is None:
        return ProtectedResource(resource=resource, authorization_servers=servers)
    return ProtectedResource(
        resource=resource,
        authorization_servers=servers,
        discovery=True,
        resolve_endpoint=extra["resolve_endpoint"],
        resolve_scope=extra["resolve_scope"],
        resolver_profiles=tuple(extra["resolver_profiles"]),
        sink_profiles=tuple(extra["sink_profiles"]),
    )


@dataclass(frozen=True)
class AuthorizationServer:
    issuer: str
    authorization_endpoint: str
    token_endpoint: str
    registration_endpoint: str | None = None
    iss_parameter_supported: bool = False


def authorization_server_metadata_urls(issuer: str) -> list[str]:
    """The metadata URLs of ``issuer`` in order: RFC 8414 section 3.1, the inserted OpenID
    Connect form (RFC 8414 section 5), and OpenID Connect Discovery 1.0 section 4."""
    candidates = [_well_known(issuer, "oauth-authorization-server", insert=True, strip_slash=True),
                  _well_known(issuer, "openid-configuration", insert=True, strip_slash=True),
                  _well_known(issuer, "openid-configuration", insert=False)]
    return list(dict.fromkeys(candidates))


def discover_authorization_server(issuer: str, *, policy: FetchPolicy, timeout: float = 10.0) -> AuthorizationServer:
    """RFC 8414 metadata, then OpenID Connect discovery. The ``issuer`` must match exactly.

    Each request passes ``policy``. Each endpoint of the metadata must pass it too, also the
    authorization endpoint, which only the browser opens (RFC 9728 section 7.7).
    """
    require_secure(issuer, "authorization server")
    for url in authorization_server_metadata_urls(issuer):
        status, document = http_json("GET", url, policy=policy, headers={"Accept": "application/json"},
                                     timeout=timeout)
        if status != 200 or not isinstance(document, dict):
            continue
        if document.get("issuer") != issuer:
            raise ResolverClientError("wrong_authorization_server", "the authorization server metadata names another issuer")
        # Absent, malformed or without S256: no proof of PKCE support, so no authorization.
        methods = document.get("code_challenge_methods_supported")
        if not isinstance(methods, list) or "S256" not in methods:
            raise ResolverClientError("no_pkce_s256", "the authorization server does not advertise PKCE S256")
        def endpoint(name: str, what: str) -> str:
            return policy.check(require_secure(document[name], what), what)

        return AuthorizationServer(
            issuer=issuer,
            authorization_endpoint=endpoint("authorization_endpoint", "authorization endpoint"),
            token_endpoint=endpoint("token_endpoint", "token endpoint"),
            registration_endpoint=(endpoint("registration_endpoint", "registration endpoint")
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
                 clock: Callable[[], float] = time.time, policy: FetchPolicy | None = None) -> None:
        self.resource = resource
        self.policy = policy or FetchPolicy(resource)
        self.authorization_server = authorization_server
        self.scope = scope
        self.cache = cache
        self._metadata_provider = metadata or (lambda: discover_authorization_server(
            authorization_server, policy=self.policy, timeout=timeout))
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
            "resource": self.resource, "scope": self.scope}, self.timeout, self.policy)
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
        status, document = http_json("POST", endpoint, policy=self.policy, body=body, timeout=self.timeout,
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
            "client_id": client_id, "code_verifier": verifier, "resource": self.resource}, self.timeout,
            self.policy)
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
            status, document = http_json("POST", endpoint.url, policy=endpoint.credential.policy, body=body,
                                         timeout=self._timeout, headers={
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
