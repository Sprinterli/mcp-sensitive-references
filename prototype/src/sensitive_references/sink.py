"""A protected local-file sink that keeps plaintext out of its model-facing result."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import tempfile

from .provenance import ProvenanceStore
from .reference import find_tokens
from .resolver import Resolver, SinkContext


@dataclass(frozen=True)
class WriteResult:
    path: Path
    model_facing_content: str


class ProtectedFileSink:
    def __init__(self, provenance: ProvenanceStore, resolver: Resolver, *, principal: str) -> None:
        self._provenance = provenance
        self._resolver = resolver
        self._principal = principal

    def write(self, destination: Path, model_content: str) -> WriteResult:
        references = find_tokens(model_content)
        by_issuer: dict[str, list[str]] = {}
        for reference in references:
            issuer = self._provenance.issuer_for(reference.token)
            by_issuer.setdefault(issuer, []).append(reference.token)

        replacements: dict[str, str] = {}
        context = SinkContext("local_file", str(destination), self._principal)
        for issuer, tokens in by_issuer.items():
            replacements.update(self._resolver.resolve(issuer, tokens, context))

        materialized = model_content
        for token, plaintext in replacements.items():
            materialized = materialized.replace(token, plaintext)

        destination.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix=".sref-", dir=destination.parent, text=True)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
                handle.write(materialized)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, destination)
        except Exception:
            Path(temporary).unlink(missing_ok=True)
            raise
        return WriteResult(destination, model_content)
