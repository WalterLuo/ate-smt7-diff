#!/usr/bin/env python3
"""WAVETBL block models."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class WaveTblRow:
    """A single row within a WAVETBL PINS group."""

    label: str
    edge_spec: str
    state: str


@dataclass(frozen=True)
class WaveTblPinsGroup:
    """A PINS group within a WAVETBL block."""

    pins_name: str
    rows: tuple[WaveTblRow, ...] = field(default_factory=tuple)
    brk: str = ""
    f: str = ""


@dataclass(frozen=True)
class WaveTblBlock:
    """Complete WAVETBL block from timing file."""

    name: str
    pins_groups: dict[str, WaveTblPinsGroup] = field(default_factory=dict)


@dataclass(frozen=True)
class WaveTblPinsGroupDiff:
    """Diff result for a single PINS group comparison."""

    pins_name: str
    rows_added: tuple[WaveTblRow, ...] = field(default_factory=tuple)
    rows_removed: tuple[WaveTblRow, ...] = field(default_factory=tuple)
    rows_changed: tuple[tuple[WaveTblRow, WaveTblRow], ...] = field(default_factory=tuple)
    brk_old: str = ""
    brk_new: str = ""
    f_old: str = ""
    f_new: str = ""

    @property
    def has_changes(self) -> bool:
        return bool(
            self.rows_added
            or self.rows_removed
            or self.rows_changed
            or self.brk_old != self.brk_new
            or self.f_old != self.f_new
        )


@dataclass(frozen=True)
class WaveTblDiff:
    """Diff result for a WAVETBL block comparison."""

    suite_name: str
    wavetbl_name: str
    pins_groups_added: dict[str, WaveTblPinsGroup] = field(default_factory=dict)
    pins_groups_removed: dict[str, WaveTblPinsGroup] = field(default_factory=dict)
    pins_groups_changed: dict[str, WaveTblPinsGroupDiff] = field(default_factory=dict)
    old_block: WaveTblBlock | None = None
    new_block: WaveTblBlock | None = None
    replaced_from: str | None = None

    @property
    def has_changes(self) -> bool:
        return bool(
            self.pins_groups_added
            or self.pins_groups_removed
            or self.pins_groups_changed
            or self.old_block
            or self.new_block
            or self.replaced_from
        )
