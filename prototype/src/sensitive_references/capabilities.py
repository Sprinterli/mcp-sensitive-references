"""Semantic extension negotiation; outer MCP capability-map syntax remains an SEP decision."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class CapabilitySettingsError(ValueError):
    pass


@dataclass(frozen=True)
class SensitiveReferencesCapabilities:
    versions: frozenset[str]
    resolver_profiles: frozenset[str]
    sink_profiles: frozenset[str]

    @classmethod
    def from_settings(cls, settings: dict[str, Any]) -> "SensitiveReferencesCapabilities":
        allowed = {"versions", "resolver_profiles", "sink_profiles"}
        if set(settings) - allowed or not isinstance(settings.get("versions"), list) or not settings["versions"]:
            raise CapabilitySettingsError("settings require non-empty versions and no unknown properties")
        values = {name: settings.get(name, []) for name in allowed}
        if not all(isinstance(item, str) for group in values.values() for item in group):
            raise CapabilitySettingsError("capability settings values must be string arrays")
        return cls(frozenset(values["versions"]), frozenset(values["resolver_profiles"]), frozenset(values["sink_profiles"]))

    def to_settings(self) -> dict[str, list[str]]:
        return {
            "versions": sorted(self.versions),
            "resolver_profiles": sorted(self.resolver_profiles),
            "sink_profiles": sorted(self.sink_profiles),
        }


@dataclass(frozen=True)
class NegotiatedSensitiveReferences:
    version: str
    resolver_profiles: frozenset[str]
    sink_profiles: frozenset[str]


def negotiate(client: SensitiveReferencesCapabilities, server: SensitiveReferencesCapabilities) -> NegotiatedSensitiveReferences | None:
    versions = client.versions & server.versions
    if not versions:
        return None
    # v1 has one compatible semantic version; a later protocol defines version ordering.
    version = sorted(versions)[-1]
    return NegotiatedSensitiveReferences(
        version=version,
        resolver_profiles=client.resolver_profiles & server.resolver_profiles,
        sink_profiles=client.sink_profiles & server.sink_profiles,
    )
