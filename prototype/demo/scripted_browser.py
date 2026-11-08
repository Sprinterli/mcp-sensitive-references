"""A scripted browser for the prototype issuer (``IssuerHttp``): for tests and the headless demo.

It keeps the session cookie, signs in with a demo account, reads the consent page,
and posts the decision with the ``Origin`` header of the issuer, as a real browser
does. Optionally it presses "Use another account" once and signs in with a second
account. It follows the final redirect to the loopback callback of the host. It
records each consent page that it saw.
"""

from __future__ import annotations

import http.client
import re
from urllib.parse import urlencode, urlsplit

_NONCE = re.compile(r'name="nonce" value="([^"]+)"')


class ScriptedBrowser:
    def __init__(self, account: str, password: str, *, decision: str = "approve",
                 switch_to: tuple[str, str] | None = None) -> None:
        self.account, self.password = account, password
        self.decision = decision
        self.switch_to = switch_to
        self.cookie: str | None = None
        self.pages: list[str] = []
        self.callbacks: list[str] = []

    def _request(self, method: str, url: str, form: dict[str, str] | None = None):
        parts = urlsplit(url)
        connection = http.client.HTTPConnection(parts.hostname, parts.port, timeout=10)
        headers = {}
        if self.cookie:
            headers["Cookie"] = self.cookie
        body = None
        if form is not None:
            body = urlencode(form)
            headers["Content-Type"] = "application/x-www-form-urlencoded"
            headers["Origin"] = f"{parts.scheme}://{parts.netloc}"
        target = parts.path + (f"?{parts.query}" if parts.query else "")
        connection.request(method, target, body=body, headers=headers)
        response = connection.getresponse()
        data = response.read().decode("utf-8", "replace")
        cookie = response.getheader("Set-Cookie")
        if cookie:
            value = cookie.split(";", 1)[0]
            self.cookie = None if value.endswith("=") else value
        location = response.getheader("Location")
        connection.close()
        return response.status, location, data

    def __call__(self, url: str) -> None:
        """``open_browser`` of the host: run the whole page flow for ``url``."""
        origin = "{0.scheme}://{0.netloc}".format(urlsplit(url))
        method, form, target = "GET", None, url
        for _ in range(12):
            status, location, data = self._request(method, target, form)
            method, form = "GET", None
            if status == 302 and location:
                if urlsplit(location).path == "/callback":
                    self.callbacks.append(location)
                    self._request("GET", location)
                    return
                if urlsplit(location).path == "/login":
                    request = dict(p.split("=", 1) for p in urlsplit(location).query.split("&"))["request"]
                    method, target = "POST", origin + "/login"
                    form = {"request": request, "account": self.account, "password": self.password}
                    continue
                target = location if location.startswith("http") else origin + location
                continue
            match = _NONCE.search(data) if status == 200 else None
            if match is None:
                return
            self.pages.append(data)
            if self.switch_to is not None:
                self.account, self.password = self.switch_to
                self.switch_to = None
                method, target, form = "POST", origin + "/switch-account", {"nonce": match.group(1)}
                continue
            method, target = "POST", origin + "/consent"
            form = {"nonce": match.group(1), "decision": self.decision}
