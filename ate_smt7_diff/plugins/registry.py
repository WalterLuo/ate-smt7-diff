#!/usr/bin/env python3
"""Global plugin registry."""

from __future__ import annotations

from ate_smt7_diff.plugins import DiffPlugin

_registry: dict[str, DiffPlugin] = {}


def register(name: str, plugin: DiffPlugin) -> None:
    """Register a diff plugin."""
    if name in _registry:
        raise ValueError(f"Plugin '{name}' is already registered")
    _registry[name] = plugin


def get(name: str) -> DiffPlugin | None:
    """Retrieve a registered plugin by name."""
    return _registry.get(name)


def list_plugins() -> list[str]:
    """Return names of all registered plugins."""
    return list(_registry.keys())


def is_registered(name: str) -> bool:
    """Check whether a plugin is registered."""
    return name in _registry


def clear() -> None:
    """Clear all registered plugins (useful for testing)."""
    _registry.clear()
