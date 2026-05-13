#!/usr/bin/env python3
"""Timing specification and EQNSET models."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class TimingSpec:
    """Parsed timing spec parameter from a SPECIFICATION or EQSP block."""

    value: str = ""
    units: str = ""
    comment: str = ""


@dataclass(frozen=True)
class TimingPinConfig:
    """Parsed PINS group entry from an EQNSET block.

    Known edges are exposed as attributes; any unknown edges
    discovered during parsing are stored in ``extra``.
    """

    d1: str = ""
    d2: str = ""
    d3: str = ""
    r1: str = ""
    r2: str = ""
    r3: str = ""
    extra: dict[str, str] = field(default_factory=dict)

    def all_fields(self) -> dict[str, str]:
        """Return all non-empty fields (known + extra) as a flat dict."""
        result: dict[str, str] = {}
        for key in ("d1", "d2", "d3", "r1", "r2", "r3"):
            val = getattr(self, key)
            if val:
                result[key] = val
        result.update(self.extra)
        return result


@dataclass(frozen=True)
class TimingSetConfig:
    """Parsed TIMINGSET entry from an EQNSET block."""

    index: int
    name: str
    period: str = ""
    extra: dict[str, str] = field(default_factory=dict)

    def all_fields(self) -> dict[str, str]:
        """Return all non-empty fields as a flat dict."""
        result: dict[str, str] = {}
        if self.period:
            result["period"] = self.period
        result.update(self.extra)
        return result


@dataclass(frozen=True)
class TimingEqnSetBlock:
    """Parsed EQSP TIM,EQN block from timing file."""

    eqnset_index: int
    eqnset_name: str
    specset_index: int
    specset_name: str
    specs: dict[str, TimingSpec] = field(default_factory=dict)
    pins_groups: dict[str, TimingPinConfig] = field(default_factory=dict)
    timingsets: dict[int, TimingSetConfig] = field(default_factory=dict)


@dataclass(frozen=True)
class TimingSpecDiff:
    """Diff result for timing spec comparison."""

    suite_name: str
    spec_type: str
    spec_name: str
    added: dict[str, TimingSpec] = field(default_factory=dict)
    removed: dict[str, TimingSpec] = field(default_factory=dict)
    changed: dict[str, tuple[TimingSpec, TimingSpec]] = field(default_factory=dict)
    replaced_from: str | None = None
    old_specs: dict[str, TimingSpec] | None = None
    new_specs: dict[str, TimingSpec] | None = None

    @property
    def has_changes(self) -> bool:
        return bool(self.added or self.removed or self.changed or self.replaced_from)


@dataclass(frozen=True)
class TimingEqnSetDiff:
    """Diff result for timing EQNSET block comparison."""

    suite_name: str
    eqnset_index: int
    eqnset_name: str
    specs_added: dict[str, TimingSpec] = field(default_factory=dict)
    specs_removed: dict[str, TimingSpec] = field(default_factory=dict)
    specs_changed: dict[str, tuple[TimingSpec, TimingSpec]] = field(default_factory=dict)
    pins_added: dict[str, TimingPinConfig] = field(default_factory=dict)
    pins_removed: dict[str, TimingPinConfig] = field(default_factory=dict)
    pins_changed: dict[str, tuple[TimingPinConfig, TimingPinConfig]] = field(default_factory=dict)
    timingsets_added: dict[int, TimingSetConfig] = field(default_factory=dict)
    timingsets_removed: dict[int, TimingSetConfig] = field(default_factory=dict)
    timingsets_changed: dict[int, tuple[TimingSetConfig, TimingSetConfig]] = field(
        default_factory=dict
    )
    old_block: TimingEqnSetBlock | None = None
    new_block: TimingEqnSetBlock | None = None
    replaced_from_index: int = 0
    replaced_from_name: str = ""

    @property
    def has_changes(self) -> bool:
        return bool(
            self.specs_added
            or self.specs_removed
            or self.specs_changed
            or self.pins_added
            or self.pins_removed
            or self.pins_changed
            or self.timingsets_added
            or self.timingsets_removed
            or self.timingsets_changed
            or self.old_block
            or self.new_block
            or self.replaced_from_name
        )
