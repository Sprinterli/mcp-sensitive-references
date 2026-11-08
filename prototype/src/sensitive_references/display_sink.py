"""The ``display-1`` sink of the host (DISPLAY-PROFILE.md). Demo level.

The host shows the value of one reference on the screen of the person after an
explicit action of the person on that reference. ``UserAction`` stands for that
action. Only the user interface of the host makes one, from an input event; no
model output, tool result or text can make one, because no method takes text in
its place. One action resolves one reference, once.

The value goes to ``screen`` only. ``reveal`` and ``copy`` return no value, so the
value cannot reach a transcript through their result. The host keeps the value in
its ``SessionMask``, so that a paste of it is masked back (section 5, rule 2), and
does not resolve it again in the session (rule 4). A copy needs a second, separate
action on the shown value (rule 3).
"""

from __future__ import annotations

from typing import Callable

from .output_guard import SessionMask
from .provenance import AmbiguousReference, ProvenanceStore, UnknownReference
from .reference import InvalidReference, parse_token
from .resolver import ResolutionError, Resolver, SinkContext
from .sink_profiles import DISPLAY, SCREEN, SINK_TYPES

#: The default limit of resolve requests per session (section 4, rule 4).
DEFAULT_LIMIT = 20


class UserAction:
    """One explicit action of the person on one reference: ``reveal`` or ``copy``. Usable once."""

    __slots__ = ("reference", "kind", "used")

    def __init__(self, reference: str, kind: str = "reveal") -> None:
        if kind not in ("reveal", "copy"):
            raise ValueError("an action is reveal or copy")
        self.reference = reference
        self.kind = kind
        self.used = False


class DisplayRefused(Exception):
    """The sink refused the action. The message holds no reference and no value."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class DisplaySink:
    def __init__(self, provenance: ProvenanceStore, resolver: Resolver, *, mask: SessionMask,
                 screen: Callable[[str, str], None], clipboard: Callable[[str], None] | None = None,
                 principal: str = "resolver-token-subject", limit: int = DEFAULT_LIMIT) -> None:
        self._provenance = provenance
        self._resolver = resolver
        self._mask = mask
        self._screen = screen
        self._clipboard = clipboard
        self._principal = principal
        self._limit = limit
        self._shown: set[str] = set()
        self.requests = 0

    def _take(self, action: object, kind: str) -> str:
        if not isinstance(action, UserAction) or action.kind != kind:
            raise DisplayRefused("no_user_action")
        if action.used:
            raise DisplayRefused("action_used")
        action.used = True
        return action.reference

    def reveal(self, action: UserAction) -> None:
        """Show the value of ``action.reference`` on the screen. Returns nothing."""
        reference = self._take(action, "reveal")
        try:
            parse_token(reference)
            issuer = self._provenance.issuer_for(reference)
        except (InvalidReference, UnknownReference, AmbiguousReference):
            raise DisplayRefused("untrusted_reference") from None
        held = self._mask.held(reference)
        if held is None:
            if self.requests >= self._limit:
                raise DisplayRefused("session_limit")
            self.requests += 1
            try:
                values = self._resolver.resolve(issuer, [reference], SinkContext(SINK_TYPES[DISPLAY], SCREEN,
                                                                                  self._principal))
            except ResolutionError as error:
                raise DisplayRefused(getattr(error, "code", "resolution_failed")) from None
            if set(values) != {reference}:
                raise DisplayRefused("malformed_batch")
            self._mask.release(values)
            held = values[reference]
        self._shown.add(reference)
        self._screen(reference, held)

    def copy(self, action: UserAction) -> None:
        """Copy a shown value to the clipboard: a second action, after ``reveal``."""
        reference = self._take(action, "copy")
        held = self._mask.held(reference)
        if reference not in self._shown or held is None or self._clipboard is None:
            raise DisplayRefused("not_shown")
        self._clipboard(held)
