#!/usr/bin/env python3
"""Level specification and EQNSET models."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class LevelSpec:
    """Parsed level spec entry from a SPECSET block."""

    actual: str = ""
    min: str = ""
    max: str = ""
    units: str = ""
    comment: str = ""


@dataclass(frozen=True)
class DpsPinConfig:
    """Parsed DPSPINS entry from an EQNSET block.

    Known fields are exposed as attributes; any unknown fields
    discovered during parsing are stored in ``extra``.
    """

    vout: str = ""
    ilimit: str = ""
    t_ms: str = ""
    vout_frc_rng: str = ""
    iout_clamp_rng: str = ""
    offcurr: str = ""
    extra: dict[str, str] = field(default_factory=dict)

    def all_fields(self) -> dict[str, str]:
        """Return all non-empty fields (known + extra) as a flat dict."""
        result: dict[str, str] = {}
        for key in ("vout", "ilimit", "t_ms", "vout_frc_rng", "iout_clamp_rng", "offcurr"):
            val = getattr(self, key)
            if val:
                result[key] = val
        result.update(self.extra)
        return result


@dataclass(frozen=True)
class LevelSetPinConfig:
    """Parsed PINS entry within a LEVELSET block.

    Known fields are exposed as attributes; any unknown fields
    discovered during parsing are stored in ``extra``.
    """

    vih: str = ""
    vil: str = ""
    voh: str = ""
    vol: str = ""
    extra: dict[str, str] = field(default_factory=dict)

    def all_fields(self) -> dict[str, str]:
        """Return all non-empty fields (known + extra) as a flat dict."""
        result: dict[str, str] = {}
        for key in ("vih", "vil", "voh", "vol"):
            val = getattr(self, key)
            if val:
                result[key] = val
        result.update(self.extra)
        return result


@dataclass(frozen=True)
class EqnSetBlock:
    """Parsed EQNSET block from the EQSP LEV,EQN region."""

    eqnset_index: int
    eqnset_name: str
    specs: dict[str, LevelSpec] = field(default_factory=dict)
    dpspins: dict[str, DpsPinConfig] = field(default_factory=dict)
    levelsets: dict[int, dict[str, LevelSetPinConfig]] = field(default_factory=dict)


@dataclass(frozen=True)
class EqnSetDiff:
    """Diff result for an EQNSET block comparison."""

    suite_name: str
    eqnset_index: int
    eqnset_name: str
    dpspins_added: dict[str, DpsPinConfig] = field(default_factory=dict)
    dpspins_removed: dict[str, DpsPinConfig] = field(default_factory=dict)
    dpspins_changed: dict[str, tuple[DpsPinConfig, DpsPinConfig]] = field(default_factory=dict)
    levelsets_added: dict[int, dict[str, LevelSetPinConfig]] = field(default_factory=dict)
    levelsets_removed: dict[int, dict[str, LevelSetPinConfig]] = field(default_factory=dict)
    levelsets_changed: dict[int, dict[str, tuple[LevelSetPinConfig, LevelSetPinConfig]]] = field(
        default_factory=dict
    )

    @property
    def has_changes(self) -> bool:
        return bool(
            self.dpspins_added
            or self.dpspins_removed
            or self.dpspins_changed
            or self.levelsets_added
            or self.levelsets_removed
            or self.levelsets_changed
        )


@dataclass(frozen=True)
class LevelSpecDiff:
    """Level spec differences for a single test suite."""

    suite_name: str
    added: dict[str, LevelSpec] = field(default_factory=dict)
    removed: dict[str, LevelSpec] = field(default_factory=dict)
    changed: dict[str, tuple[LevelSpec, LevelSpec]] = field(default_factory=dict)

    @property
    def has_changes(self) -> bool:
        return bool(self.added or self.removed or self.changed)
