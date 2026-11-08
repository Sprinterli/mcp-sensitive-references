"""The sink profiles of Concept 0.7 and their scopes (RESOLVER-PROFILE.md, sections 4 and 5)."""

from __future__ import annotations

RESOLVE_SCOPE = "sensitive-references.resolve"
#: The sink scope of ``process-1`` (PROCESS-PROFILE.md, section 1).
PROCESS_SCOPE = "sensitive-references.resolve.process"
#: The sink scope of ``display-1`` (DISPLAY-PROFILE.md, section 1).
DISPLAY_SCOPE = "sensitive-references.resolve.display"

LOCAL_FILE = "local-file-1"
#: The neutral identifier of the draft (OQ-21). The prototype publishes no other identifier.
PROCESS = "process-1"
DISPLAY = "display-1"

#: The wire value of ``sink_type`` for each sink profile (RESOLVER-PROFILE.md, section 12.1).
SINK_TYPES = {LOCAL_FILE: "local_file", PROCESS: "process", DISPLAY: "display"}
#: The sink scope of each sink profile; ``local-file-1`` needs none.
SINK_SCOPES = {LOCAL_FILE: None, PROCESS: PROCESS_SCOPE, DISPLAY: DISPLAY_SCOPE}
#: The fixed destination of ``display-1`` (DISPLAY-PROFILE.md, section 3).
SCREEN = "screen"


def scope_set(profile: str, resolve_scope: str = RESOLVE_SCOPE) -> tuple[str, ...]:
    """The whole scope set that a token needs for ``profile``: the resolve scope and its sink scope."""
    sink = SINK_SCOPES[profile]
    return (resolve_scope,) if sink is None else (resolve_scope, sink)
