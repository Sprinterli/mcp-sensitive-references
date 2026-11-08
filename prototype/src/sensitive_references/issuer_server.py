"""A dependency-free issuer for ``oauth-resolver-1`` of Concept 0.7: authorization server and resolve endpoint.

Demo level. It keeps everything in memory, signs nobody in with a real identity
provider (accounts and passwords are demo fixtures), and has no persistence.
It implements the rules of RESOLVER-PROFILE.md that a server owns:

* the discovery object ``sensitive_references`` with ``sinks``, ``process_scope``
  and ``display_scope`` (section 4);
* the scope combinations of section 5.2 (``invalid_scope``), the granted set kept at
  a refresh (section 5.3) and ``403 insufficient_scope`` before any lookup (section 5.4);
* a consent page at every authorization request, with the account, an action to use
  another account, the client, the loopback host and port, the time, the resource and
  one line per sink scope (section 10);
* loopback redirect URIs with any port (section 9.2);
* references per person: a lookup only in the records of the token subject (section 12.2);
* ``account_hint`` in the token and the refresh answer (section 11.2);
* no value without its audit event, else ``503 audit_unavailable`` (section 15);
* revocation per device with an epoch per (principal, client) (section 10.4).

``IssuerServer`` works on plain values. ``IssuerHttp`` puts it on a stdlib HTTP server
for the demo and the end-to-end tests. No answer of this module holds a value outside
the ``200`` answer of the resolve endpoint.
"""

from __future__ import annotations

from base64 import urlsafe_b64encode
from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
import hmac
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import secrets
import threading
import time
from typing import Any, Callable, Iterable
from urllib.parse import parse_qs, urlencode, urlsplit

from .reference import _TOKEN_RE, make_token
from .sink_profiles import (
    DISPLAY,
    DISPLAY_SCOPE,
    LOCAL_FILE,
    PROCESS,
    PROCESS_SCOPE,
    RESOLVE_SCOPE,
    SCREEN,
    SINK_SCOPES,
    SINK_TYPES,
    scope_set,
)

#: The fixed text of a ``403 insufficient_scope`` answer per sink profile (section 5.4). No protected data.
INSUFFICIENT_SCOPE_TEXT = {
    LOCAL_FILE: "This sign-in does not allow real values. Sign in again and allow them on the consent page.",
    PROCESS: "This sign-in does not allow real values in commands. Sign in again and allow commands on the "
             "consent page.",
    DISPLAY: "This sign-in does not allow real values on your screen. Sign in again and allow the screen on "
             "the consent page.",
}
#: The consent line of each sink scope (PROCESS-PROFILE.md and DISPLAY-PROFILE.md, section 6, rule 3).
CONSENT_LINES = {
    PROCESS_SCOPE: "The program can put real values into commands that it runs on this computer. The program "
                   "says that it masks the command output before the AI sees it.",
    DISPLAY_SCOPE: "The program can show real values on your screen. The program says that it never gives "
                   "them to the AI.",
}
MIN_REFERENCES = 100
MAX_DESTINATION = 4096


class AuditUnavailable(RuntimeError):
    """The audit store cannot write an event."""


class AuditLog:
    """An in-memory audit store. ``fail`` makes every write fail (a broken store)."""

    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []
        self.fail = False

    def write(self, event: dict[str, Any]) -> None:
        if self.fail:
            raise AuditUnavailable("the audit store did not accept the event")
        self.events.append(dict(event))


def account_hint(account: str) -> str:
    """The masked account of section 11.2: at most three characters of the local part, never more than
    half of it, an ellipsis (U+2026), then the whole domain. Never the whole account name."""
    local, at, domain = account.rpartition("@")
    if not at:
        local, domain = account, ""
    keep = min(3, len(local) // 2)
    return f"{local[:keep]}…" + (f"@{domain}" if at else "")


def audit_destination(profile: str, destination: str) -> str:
    """What the audit event keeps of ``destination`` (PROCESS-PROFILE.md, section 6, rule 2).

    ``process-1``: the last path part if the destination holds no white space, else ``other``.
    ``display-1``: ``screen``. ``local-file-1``: a hash of the label, so no path is kept.
    """
    if profile == PROCESS:
        last = destination.replace("\\", "/").rsplit("/", 1)[-1]
        return last if last and not any(c.isspace() for c in destination) else "other"
    if profile == DISPLAY:
        return SCREEN
    return "sha256:" + sha256(destination.encode()).hexdigest()[:16]


def _loopback_redirect(uri: str) -> bool:
    """An ``http`` redirect URI on the IPv4 loopback literal (section 9.2; ``[::1]`` refused, OQ-15)."""
    parts = urlsplit(uri)
    try:
        port = parts.port
    except ValueError:
        return False
    return (parts.scheme == "http" and parts.hostname == "127.0.0.1" and port is not None
            and parts.netloc == f"127.0.0.1:{port}" and not parts.fragment)


def redirect_matches(registered: str, requested: str) -> bool:
    """Exact comparison, except any port for a loopback registration (RFC 8252 section 7.3)."""
    if registered == requested:
        return True
    if not (_loopback_redirect(registered) and _loopback_redirect(requested)):
        return False
    a, b = urlsplit(registered), urlsplit(requested)
    return (a.scheme, a.hostname, a.path, a.query) == (b.scheme, b.hostname, b.path, b.query)


@dataclass
class Record:
    value: str
    revoked: bool = False
    expires_at: float | None = None


@dataclass
class Response:
    status: int
    body: Any = None
    headers: dict[str, str] = field(default_factory=dict)
    #: For a consent page: what the page names, for tests (the HTML holds the same).
    page: dict[str, Any] | None = None


def _error(status: int, code: str, **extra) -> Response:
    return Response(status, {"error": code, **extra}, {"Cache-Control": "no-store"})


class IssuerServer:
    """One protected resource with its authorization server and resolve endpoint, on one origin."""

    def __init__(self, base: str, *, mcp_path: str = "/mcp",
                 sinks: Iterable[str] = (LOCAL_FILE, PROCESS, DISPLAY),
                 access_lifetime: float = 3600, approval_lifetime: float = 180 * 86400,
                 code_lifetime: float = 60, max_references: int = MIN_REFERENCES,
                 daily_quota: int | None = None, audit: AuditLog | None = None,
                 clock: Callable[[], float] = time.time) -> None:
        self.base = base.rstrip("/")
        self.origin = "{0.scheme}://{0.netloc}".format(urlsplit(self.base))
        self.resource = self.base + mcp_path
        self.resolve_endpoint = self.base + "/sensitive-references/resolve"
        self.sinks = tuple(sorted(sinks))
        if any(s not in SINK_TYPES for s in self.sinks) or max_references < MIN_REFERENCES:
            raise ValueError("an unknown sink profile or a limit below 100")
        self.access_lifetime = access_lifetime
        self.approval_lifetime = approval_lifetime
        self.code_lifetime = code_lifetime
        self.max_references = max_references
        self.daily_quota = daily_quota
        self.audit = audit or AuditLog()
        self.clock = clock
        self._lock = threading.RLock()
        self.passwords: dict[str, str] = {}
        self.admins: set[str] = set()
        self.blocked: set[str] = set()
        #: References per person: subject -> reference -> record (section 12.2).
        self.records: dict[str, dict[str, Record]] = {}
        self.clients: dict[str, dict[str, Any]] = {}
        self.sessions: dict[str, str] = {}               # browser session -> subject
        self.pending: dict[str, dict[str, Any]] = {}     # authorization request -> parameters
        self.nonces: dict[str, tuple[str, str]] = {}     # nonce -> (browser session, request)
        self.codes: dict[str, dict[str, Any]] = {}
        self.access: dict[str, dict[str, Any]] = {}
        self.refresh: dict[str, dict[str, Any]] = {}
        #: (subject, client, resource, scope set) -> expiry (section 10.3).
        self.approvals: dict[tuple[str, str, str, frozenset[str]], float] = {}
        #: (subject, client) -> epoch (section 10.4).
        self.epochs: dict[tuple[str, str], int] = {}
        self.used: dict[tuple[str, str], int] = {}       # (subject, day) -> released values
        #: Each read of a reference record. A refusal before the lookup leaves it unchanged.
        self.lookups = 0

    # ------------------------------------------------------------ fixtures

    def add_account(self, account: str, password: str, *, admin: bool = False) -> None:
        self.passwords[account] = password
        if admin:
            self.admins.add(account)

    def issue(self, subject: str, kind: str, value: str, *, expires_at: float | None = None) -> str:
        """A new reference of ``subject``. Equal values get unrelated identifiers."""
        token = make_token(kind).token
        self.records.setdefault(subject, {})[token] = Record(value, expires_at=expires_at)
        return token

    def revoke_reference(self, subject: str, token: str) -> None:
        self.records[subject][token].revoked = True

    # ------------------------------------------------------------ metadata

    def sink_scopes(self) -> dict[str, str]:
        return {SINK_SCOPES[p]: p for p in self.sinks if SINK_SCOPES[p]}

    def discovery(self) -> dict[str, Any]:
        obj: dict[str, Any] = {
            "resolve_endpoint": self.resolve_endpoint,
            "resolve_scope": RESOLVE_SCOPE,
            "resolver_profiles": ["oauth-resolver-1"],
            "sink_profiles": list(self.sinks),
            "sinks": {p: {"sink_type": SINK_TYPES[p], "scopes": list(scope_set(p))} for p in self.sinks},
            "status": "experimental",
        }
        if PROCESS in self.sinks:
            obj["process_scope"] = PROCESS_SCOPE
        if DISPLAY in self.sinks:
            obj["display_scope"] = DISPLAY_SCOPE
        if self.max_references != MIN_REFERENCES:
            obj["max_references"] = self.max_references
        return obj

    def protected_resource_metadata(self) -> dict[str, Any]:
        # The resolve scope and the sink scopes are not in scopes_supported (section 5.1).
        return {"resource": self.resource, "authorization_servers": [self.base], "scopes_supported": ["mcp"],
                "sensitive_references": self.discovery()}

    def authorization_server_metadata(self) -> dict[str, Any]:
        return {"issuer": self.base, "authorization_endpoint": f"{self.base}/authorize",
                "token_endpoint": f"{self.base}/token", "registration_endpoint": f"{self.base}/register",
                "response_types_supported": ["code"], "grant_types_supported": ["authorization_code", "refresh_token"],
                "code_challenge_methods_supported": ["S256"], "token_endpoint_auth_methods_supported": ["none"],
                "authorization_response_iss_parameter_supported": True}

    # ------------------------------------------------------------ registration

    def register(self, document: Any) -> Response:
        uris = document.get("redirect_uris") if isinstance(document, dict) else None
        if not isinstance(uris, list) or not uris or not all(isinstance(u, str) for u in uris):
            return _error(400, "invalid_redirect_uri")
        # Every sink of this server puts the value on the computer of the host: loopback only (section 9.2).
        if not all(_loopback_redirect(u) for u in uris):
            return _error(400, "invalid_redirect_uri")
        name = document.get("client_name")
        name = name if isinstance(name, str) and name.strip() else "an unnamed program"
        client_id = secrets.token_urlsafe(12)
        self.clients[client_id] = {"client_name": name[:200], "redirect_uris": list(uris)}
        return Response(201, {"client_id": client_id, "client_name": name[:200], "redirect_uris": uris,
                              "token_endpoint_auth_method": "none"}, {"Cache-Control": "no-store"})

    # ------------------------------------------------------------ scopes

    def check_scope(self, scope: str | None) -> frozenset[str] | None:
        """The requested scope set if section 5.2 accepts it, else None (``invalid_scope``)."""
        requested = frozenset((scope or "").split())
        if RESOLVE_SCOPE not in requested:
            return None
        if requested - {RESOLVE_SCOPE, "openid"} - set(self.sink_scopes()):
            return None
        return requested

    # ------------------------------------------------------------ authorization

    def _redirect(self, request: dict[str, Any], **answer: str) -> Response:
        query = urlencode({**answer, "state": request.get("state", ""), "iss": self.base})
        return Response(302, None, {"Location": f"{request['redirect_uri']}?{query}", "Cache-Control": "no-store"})

    def authorize(self, params: dict[str, str], session: str | None) -> Response:
        """``GET /authorize``. A valid request always gets the consent page (or the sign-in first)."""
        client = self.clients.get(params.get("client_id", ""))
        uri = params.get("redirect_uri", "")
        if client is None or not any(redirect_matches(r, uri) for r in client["redirect_uris"]):
            return _error(400, "invalid_request")       # never a redirect to an unchecked URI
        request = {k: params.get(k, "") for k in ("client_id", "redirect_uri", "state", "scope", "resource",
                                                  "code_challenge", "code_challenge_method", "response_type")}
        if request["response_type"] != "code" or request["code_challenge_method"] != "S256" \
                or not request["code_challenge"]:
            return self._redirect(request, error="invalid_request")
        if request["resource"] != self.resource:
            return self._redirect(request, error="invalid_target")
        scopes = self.check_scope(request["scope"])
        if scopes is None:
            return self._redirect(request, error="invalid_scope")
        request["scopes"] = scopes
        request["requested_at"] = self.clock()
        request_id = secrets.token_urlsafe(16)
        self.pending[request_id] = request
        return self.resume(request_id, session)

    def resume(self, request_id: str, session: str | None) -> Response:
        """The page of a pending request: the sign-in without a session, else the consent page."""
        request = self.pending.get(request_id)
        if request is None:
            return _error(400, "invalid_request")
        subject = self.sessions.get(session or "")
        if subject is None:
            return Response(302, None, {"Location": f"{self.base}/login?{urlencode({'request': request_id})}",
                                        "Cache-Control": "no-store"})
        if subject in self.blocked:
            del self.pending[request_id]
            return self._redirect(request, error="access_denied")
        # Section 10.1: a stored approval never replaces this page.
        nonce = secrets.token_urlsafe(24)
        self.nonces[nonce] = (session or "", request_id)
        loopback = urlsplit(request["redirect_uri"])
        page = {
            "account": subject,
            "client": self.clients[request["client_id"]]["client_name"],
            "loopback": f"{loopback.hostname}:{loopback.port}",
            "requested_at": datetime.fromtimestamp(request["requested_at"], timezone.utc)
                                    .strftime("%Y-%m-%d %H:%M:%S UTC"),
            "resource": self.resource,
            "sink_lines": [CONSENT_LINES[s] for s in sorted(request["scopes"]) if s in CONSENT_LINES],
            "nonce": nonce,
            "request": request_id,
        }
        csp = f"frame-ancestors 'none'; form-action 'self' http://{page['loopback']}"
        return Response(200, consent_html(page), {"Content-Type": "text/html; charset=utf-8",
                                                  "Content-Security-Policy": csp, "Cache-Control": "no-store",
                                                  "X-Frame-Options": "DENY"}, page)

    def login(self, form: dict[str, str], origin: str | None) -> tuple[Response, str | None]:
        """``POST /login`` (demo accounts). Returns the answer and the new browser session."""
        request_id = form.get("request", "")
        if origin != self.origin or request_id not in self.pending:
            return _error(400, "invalid_request"), None
        account, password = form.get("account", ""), form.get("password", "")
        expected = self.passwords.get(account)
        if expected is None or not hmac.compare_digest(expected, password):
            return Response(302, None, {"Location": f"{self.base}/login?{urlencode({'request': request_id, 'failed': '1'})}"}), None
        session = secrets.token_urlsafe(24)
        self.sessions[session] = account
        return Response(302, None, {"Location": f"{self.base}/authorize/resume?{urlencode({'request': request_id})}",
                                    "Cache-Control": "no-store"}), session

    def _spend_nonce(self, session: str | None, form: dict[str, str], origin: str | None) -> dict[str, Any] | None:
        """The pending request of a consent or switch post, or None. The nonce is single-use."""
        nonce = form.get("nonce", "")
        bound = self.nonces.pop(nonce, None) if nonce else None
        if bound is None or origin != self.origin:
            return None
        bound_session, request_id = bound
        if not session or not hmac.compare_digest(bound_session, session) or request_id not in self.pending:
            return None
        return {"id": request_id, **self.pending[request_id]}

    def consent(self, session: str | None, form: dict[str, str], origin: str | None) -> Response:
        """``POST /consent``: the decision of the user. Approve records the approval and issues a code."""
        request = self._spend_nonce(session, form, origin)
        subject = self.sessions.get(session or "")
        if request is None or subject is None:
            return _error(400, "invalid_request")
        del self.pending[request["id"]]
        if form.get("decision") != "approve":
            return self._redirect(request, error="access_denied")
        device = (subject, request["client_id"])
        with self._lock:
            epoch = self.epochs.setdefault(device, 0)
            approval = (subject, request["client_id"], request["resource"], request["scopes"])
            self.approvals[approval] = self.clock() + self.approval_lifetime
            code = secrets.token_urlsafe(24)
            self.codes[code] = {"subject": subject, "client_id": request["client_id"],
                                "redirect_uri": request["redirect_uri"], "resource": request["resource"],
                                "code_challenge": request["code_challenge"], "scopes": request["scopes"],
                                "approval": approval, "epoch": epoch,
                                "expires_at": self.clock() + self.code_lifetime}
        return self._redirect(request, code=code)

    def switch_account(self, session: str | None, form: dict[str, str], origin: str | None) -> Response:
        """``POST /switch-account``: end the browser session and return to the same request (section 10.2)."""
        request = self._spend_nonce(session, form, origin)
        if request is None:
            return _error(400, "invalid_request")
        self.sessions.pop(session or "", None)
        return Response(302, None, {"Location": f"{self.base}/login?{urlencode({'request': request['id']})}",
                                    "Cache-Control": "no-store", "Set-Cookie": _cookie("")})

    # ------------------------------------------------------------ credentials

    def _current(self, record: dict[str, Any]) -> bool:
        """The epoch of the device is readable and equal to the epoch of the credential, and the approval
        is live (sections 10.3 and 10.4)."""
        epoch = self.epochs.get((record["subject"], record["client_id"]))
        live = self.approvals.get(record["approval"], 0) > self.clock()
        return epoch is not None and epoch == record["epoch"] and live

    def _issue(self, grant: dict[str, Any]) -> Response | None:
        with self._lock:                                 # the epoch check and the write in one step
            if not self._current(grant):
                return None
            access, refresh = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
            common = {k: grant[k] for k in ("subject", "client_id", "resource", "scopes", "approval", "epoch")}
            self.access[access] = {**common, "expires_at": self.clock() + self.access_lifetime}
            self.refresh[refresh] = dict(common)
        return Response(200, {"access_token": access, "token_type": "Bearer", "expires_in": int(self.access_lifetime),
                              "refresh_token": refresh, "scope": " ".join(sorted(grant["scopes"])),
                              "account_hint": account_hint(grant["subject"])}, {"Cache-Control": "no-store"})

    def token(self, form: dict[str, str]) -> Response:
        grant_type = form.get("grant_type")
        if grant_type == "authorization_code":
            with self._lock:
                code = self.codes.pop(form.get("code", ""), None)
            if code is None or code["expires_at"] <= self.clock():
                return _error(400, "invalid_grant")
            verifier = form.get("code_verifier", "")
            challenge = urlsafe_b64encode(sha256(verifier.encode()).digest()).rstrip(b"=").decode()
            if (form.get("client_id") != code["client_id"] or form.get("redirect_uri") != code["redirect_uri"]
                    or not hmac.compare_digest(challenge, code["code_challenge"])
                    or form.get("resource", self.resource) != code["resource"]):
                return _error(400, "invalid_grant")
            return self._issue(code) or _error(400, "invalid_grant")
        if grant_type == "refresh_token":
            token = form.get("refresh_token", "")
            with self._lock:
                record = self.refresh.get(token)
                if record is None or form.get("client_id") != record["client_id"]:
                    return _error(400, "invalid_grant")
                # Section 5.3: a refresh keeps the granted set and never adds a scope.
                if "scope" in form and not set(form["scope"].split()) <= record["scopes"]:
                    return _error(400, "invalid_scope")
                del self.refresh[token]                  # rotation: single use
            return self._issue(record) or _error(400, "invalid_grant")
        return _error(400, "unsupported_grant_type")

    # ------------------------------------------------------------ devices (section 10.4)

    def _may_manage(self, actor: str, principal: str) -> None:
        if actor != principal and actor not in self.admins:
            raise PermissionError("only the person or an administrator manages these devices")

    def devices(self, actor: str, principal: str) -> list[dict[str, Any]]:
        self._may_manage(actor, principal)
        now = self.clock()
        rows: dict[str, set[str]] = {}
        for (subject, client, _, scopes), expires in self.approvals.items():
            if subject == principal and expires > now:
                rows.setdefault(client, set()).update(scopes)
        return [{"client_id": c, "client_name": self.clients.get(c, {}).get("client_name", ""),
                 "commands": PROCESS_SCOPE in s, "screen": DISPLAY_SCOPE in s} for c, s in sorted(rows.items())]

    def revoke_device(self, actor: str, principal: str, client_id: str) -> None:
        self._may_manage(actor, principal)
        device = (principal, client_id)
        with self._lock:
            # The epoch rises before the tokens stop: a refresh in flight cannot write a live credential.
            self.epochs[device] = self.epochs.get(device, 0) + 1
            for store in (self.access, self.refresh, self.codes):
                for key in [k for k, r in store.items() if (r["subject"], r["client_id"]) == device]:
                    del store[key]
            for key in [k for k in self.approvals if (k[0], k[1]) == device]:
                del self.approvals[key]

    def withdraw_approvals(self, subject: str) -> None:
        """The person withdraws every approval: refresh and live access tokens stop (section 10.3)."""
        with self._lock:
            for key in [k for k in self.approvals if k[0] == subject]:
                del self.approvals[key]

    # ------------------------------------------------------------ resolve

    def _unauthorized(self) -> Response:
        response = _error(401, "invalid_token")
        response.headers["WWW-Authenticate"] = 'Bearer error="invalid_token"'
        return response

    def _insufficient(self, profile: str) -> Response:
        scope = " ".join(scope_set(profile))
        text = INSUFFICIENT_SCOPE_TEXT[profile]
        response = _error(403, "insufficient_scope", error_description=text, scope=scope)
        response.headers["WWW-Authenticate"] = (f'Bearer error="insufficient_scope", scope="{scope}", '
                                                f'error_description="{text}"')
        return response

    def resolve(self, authorization: str | None, raw: bytes) -> Response:
        """``POST`` to the resolve endpoint (sections 5.4, 12, 13 and 15)."""
        token = (authorization or "").removeprefix("Bearer ") if (authorization or "").startswith("Bearer ") else ""
        record = self.access.get(token) if token else None
        if (record is None or record["expires_at"] <= self.clock() or record["resource"] != self.resource
                or not self._current(record)):
            return self._unauthorized()
        try:
            body = json.loads(raw)
        except ValueError:
            return _error(400, "invalid_request")
        references = body.get("references") if isinstance(body, dict) else None
        if (not isinstance(references, list) or not all(isinstance(r, str) for r in references)
                or not isinstance(body.get("sink_type"), str)):
            return _error(400, "invalid_request")
        profile = next((p for p in self.sinks if SINK_TYPES[p] == body["sink_type"]), None)
        if profile is None:
            return _error(403, "ineligible_sink")
        # Section 5.4: the scopes before any lookup; no value and no audit event.
        if not set(scope_set(profile)) <= record["scopes"]:
            return self._insufficient(profile)
        destination = body.get("destination")
        if (not isinstance(destination, str) or not 1 <= len(destination) <= MAX_DESTINATION
                or any(ord(c) < 0x20 or ord(c) == 0x7F for c in destination)):
            return _error(400, "invalid_request")
        unique = list(dict.fromkeys(references))
        if not unique:
            return _error(400, "invalid_request")
        if profile == DISPLAY and (destination != SCREEN or len(unique) != 1 or len(references) != 1):
            return _error(400, "invalid_request")
        if len(unique) > self.max_references:
            return _error(413, "too_many_references")
        subject = record["subject"]
        if subject in self.blocked:
            return _error(403, "not_enabled")
        day = datetime.fromtimestamp(self.clock(), timezone.utc).strftime("%Y-%m-%d")
        if self.daily_quota is not None and self.used.get((subject, day), 0) + len(unique) > self.daily_quota:
            return _error(429, "quota_exceeded")
        # Section 12.2: only the records of the token subject. A reference of another person is unknown.
        own = self.records.get(subject, {})
        reasons: dict[str, int] = {}
        values: dict[str, str] = {}
        now = self.clock()
        for reference in unique:
            if not _TOKEN_RE.fullmatch(reference):
                reasons["malformed"] = reasons.get("malformed", 0) + 1
                continue
            self.lookups += 1
            found = own.get(reference)
            reason = ("unknown" if found is None else "revoked" if found.revoked
                      else "expired" if found.expires_at is not None and found.expires_at <= now else None)
            if reason:
                reasons[reason] = reasons.get(reason, 0) + 1
            else:
                values[reference] = found.value
        if reasons:
            return _error(409, "unresolvable", reasons=reasons)
        event = {"subject": subject, "client_id": record["client_id"], "sink_profile": profile,
                 "values": len(values), "destination": audit_destination(profile, destination),
                 "references": [sha256(r.encode()).hexdigest()[:16] for r in values]}
        try:
            self.audit.write(event)                      # section 15: the event before the values
        except AuditUnavailable:
            return _error(503, "audit_unavailable")
        self.used[(subject, day)] = self.used.get((subject, day), 0) + len(values)
        return Response(200, {"values": values}, {"Cache-Control": "no-store"})


# ---------------------------------------------------------------- pages


def consent_html(page: dict[str, Any]) -> str:
    e = {k: escape(str(v)) for k, v in page.items() if not isinstance(v, list)}
    lines = "".join(f"<li>{escape(line)}</li>" for line in page["sink_lines"])
    sinks = f"<p>It also asks for this:</p><ul>{lines}</ul>" if lines else ""
    hidden = f'<input type="hidden" name="nonce" value="{e["nonce"]}">'
    return (
        "<!doctype html><html><head><meta charset='utf-8'><title>Allow real values</title></head><body>"
        f"<h1>Allow real values for {e['client']}?</h1>"
        f"<p>Signed in as <strong>{e['account']}</strong>.</p>"
        f"<form method='post' action='/switch-account'>{hidden}<button>Use another account</button></form>"
        f"<p>Program: <strong>{e['client']}</strong> (the name comes from the program).</p>"
        f"<p>It waits on this computer at <strong>{e['loopback']}</strong>.</p>"
        f"<p>Request time: {e['requested_at']}.</p>"
        f"<p>Data source: {e['resource']}.</p>"
        "<p>The program can get the real values of references that this data source gave to you.</p>"
        f"{sinks}"
        "<p>Approve only a sign-in that you started in this program.</p>"
        f"<form method='post' action='/consent'>{hidden}"
        "<button name='decision' value='approve'>Allow</button>"
        "<button name='decision' value='deny'>Deny</button></form></body></html>")


def login_html(request_id: str, failed: bool) -> str:
    note = "<p>The account or the password is wrong.</p>" if failed else ""
    return ("<!doctype html><html><head><meta charset='utf-8'><title>Sign in</title></head><body>"
            f"<h1>Sign in</h1>{note}<form method='post' action='/login'>"
            f"<input type='hidden' name='request' value='{escape(request_id)}'>"
            "<label>Account <input name='account'></label> <label>Password <input name='password' "
            "type='password'></label> <button>Sign in</button></form></body></html>")


# ---------------------------------------------------------------- HTTP

_COOKIE = "sref_session"


def _cookie(value: str) -> str:
    return f"{_COOKIE}={value}; Path=/; HttpOnly; SameSite=Lax" + ("" if value else "; Max-Age=0")


class IssuerHttp:
    """``IssuerServer`` on a loopback stdlib HTTP server. ``POST /mcp`` answers 401 with the challenge."""

    def __init__(self, host: str = "127.0.0.1", port: int = 0, **options) -> None:
        self._http = ThreadingHTTPServer((host, port), self._handler())
        self.base = f"http://{host}:{self._http.server_address[1]}"
        self.issuer = IssuerServer(self.base, **options)
        self._thread = threading.Thread(target=self._http.serve_forever, daemon=True)
        self._thread.start()

    def close(self) -> None:
        self._http.shutdown()
        self._http.server_close()

    def _handler(self):
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):  # a query can hold a code
                pass

            def _session(self) -> str | None:
                for part in (self.headers.get("Cookie") or "").split(";"):
                    name, _, value = part.strip().partition("=")
                    if name == _COOKIE and value:
                        return value
                return None

            def _send(self, response: Response, cookie: str | None = None) -> None:
                body = response.body
                if isinstance(body, str):
                    data = body.encode()
                    kind = response.headers.get("Content-Type", "text/plain; charset=utf-8")
                else:
                    data = json.dumps(body).encode() if body is not None else b""
                    kind = "application/json"
                self.send_response(response.status)
                for k, v in response.headers.items():
                    if k != "Content-Type":
                        self.send_header(k, v)
                if cookie is not None:
                    self.send_header("Set-Cookie", _cookie(cookie))
                self.send_header("Content-Type", kind)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def _form(self) -> dict[str, str]:
                raw = self.rfile.read(int(self.headers.get("Content-Length") or 0)).decode()
                return {k: v[0] for k, v in parse_qs(raw).items()}

            def do_GET(self):  # noqa: N802
                issuer = outer.issuer
                parts = urlsplit(self.path)
                query = {k: v[0] for k, v in parse_qs(parts.query).items()}
                if parts.path == "/.well-known/oauth-protected-resource" + urlsplit(issuer.resource).path:
                    return self._send(Response(200, issuer.protected_resource_metadata()))
                if parts.path == "/.well-known/oauth-authorization-server":
                    return self._send(Response(200, issuer.authorization_server_metadata()))
                if parts.path == "/authorize":
                    return self._send(issuer.authorize(query, self._session()))
                if parts.path == "/authorize/resume":
                    return self._send(issuer.resume(query.get("request", ""), self._session()))
                if parts.path == "/login":
                    return self._send(Response(200, login_html(query.get("request", ""), "failed" in query),
                                               {"Content-Type": "text/html; charset=utf-8",
                                                "Content-Security-Policy": "frame-ancestors 'none'"}))
                return self._send(_error(404, "not_found"))

            def do_POST(self):  # noqa: N802
                issuer = outer.issuer
                path = urlsplit(self.path).path
                origin = self.headers.get("Origin")
                if path == "/mcp":
                    metadata = issuer.base + "/.well-known/oauth-protected-resource" + urlsplit(issuer.resource).path
                    return self._send(Response(401, {"error": "invalid_token"}, {
                        "WWW-Authenticate": f'Bearer error="invalid_token", resource_metadata="{metadata}"'}))
                if path == "/register":
                    try:
                        document = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)))
                    except ValueError:
                        document = None
                    return self._send(issuer.register(document))
                if path == "/login":
                    response, session = issuer.login(self._form(), origin)
                    return self._send(response, session)
                if path == "/consent":
                    return self._send(issuer.consent(self._session(), self._form(), origin))
                if path == "/switch-account":
                    return self._send(issuer.switch_account(self._session(), self._form(), origin))
                if path == "/token":
                    return self._send(issuer.token(self._form()))
                if path == urlsplit(issuer.resolve_endpoint).path:
                    raw = self.rfile.read(int(self.headers.get("Content-Length") or 0))
                    return self._send(issuer.resolve(self.headers.get("Authorization"), raw))
                return self._send(_error(404, "not_found"))

        return Handler
