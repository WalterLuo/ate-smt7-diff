#!/usr/bin/env python3
"""
Central data models for the SMT7 diff engine.
All dataclasses and enums live here to avoid circular imports
and provide a single source of truth for the domain model.
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from functools import cached_property
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# Flow diff models (from smt7_flow_diff.py)
# ---------------------------------------------------------------------------

class DiffType(Enum):
    ADDED = auto()
    REMOVED = auto()
    MOVED = auto()
    UNCHANGED = auto()


@dataclass(frozen=True)
class TestItem:
    """A single test execution in the flow."""
    suite_name: str
    group_path: Tuple[str, ...]
    line_number: int
    is_branch: bool


@dataclass(frozen=True)
class FlowDiff:
    """Difference result for a single test occurrence."""
    suite_name: str
    diff_type: DiffType
    old_index: Optional[int]
    new_index: Optional[int]
    old_group_path: Tuple[str, ...]
    new_group_path: Tuple[str, ...]


@dataclass
class DiffReport:
    """Complete diff report between two flows."""
    old_file: str
    new_file: str
    old_tests: List[TestItem]
    new_tests: List[TestItem]
    diffs: List[FlowDiff]
    suite_config_report: Optional["SuiteConfigReport"] = None
    old_suite_views: Optional[Dict[str, "SuiteConfigView"]] = None
    new_suite_views: Optional[Dict[str, "SuiteConfigView"]] = None
    level_spec_diffs: Optional[List["LevelSpecDiff"]] = None
    eqnset_diffs: Optional[List["EqnSetDiff"]] = None
    timing_spec_diffs: Optional[List["TimingSpecDiff"]] = None
    timing_eqnset_diffs: Optional[List["TimingEqnSetDiff"]] = None
    timing_wavetbl_diffs: Optional[List["WaveTblDiff"]] = None

    @cached_property
    def added(self) -> List[str]:
        return sorted({d.suite_name for d in self.diffs if d.diff_type == DiffType.ADDED})

    @cached_property
    def removed(self) -> List[str]:
        return sorted({d.suite_name for d in self.diffs if d.diff_type == DiffType.REMOVED})

    @cached_property
    def moved(self) -> List[str]:
        return sorted({d.suite_name for d in self.diffs if d.diff_type == DiffType.MOVED})

    @cached_property
    def unchanged(self) -> List[str]:
        return sorted({d.suite_name for d in self.diffs if d.diff_type == DiffType.UNCHANGED})

    @cached_property
    def order_changed(self) -> List[str]:
        from ate_smt7_diff.diff.flow_diff import compute_order_changes
        return compute_order_changes(self.old_tests, self.new_tests)


# ---------------------------------------------------------------------------
# Suite config models (from suite_config.py)
# ---------------------------------------------------------------------------

@dataclass
class SuiteConfigDiff:
    """Configuration differences for a single test suite."""
    suite_name: str
    changed: Dict[str, Tuple[str, str]] = field(default_factory=dict)
    added: Dict[str, str] = field(default_factory=dict)
    removed: Dict[str, str] = field(default_factory=dict)

    @property
    def has_changes(self) -> bool:
        return bool(self.changed or self.added or self.removed)


@dataclass
class SuiteConfigReport:
    """Complete suite configuration diff report."""
    old_file: str
    new_file: str
    diffs: List[SuiteConfigDiff]
    common_suites: List[str]
    skipped_suites: List[str]

    @cached_property
    def suites_with_changes(self) -> List[str]:
        return [d.suite_name for d in self.diffs if d.has_changes]


# ---------------------------------------------------------------------------
# Level / EQNSET models (from program_loader.py)
# ---------------------------------------------------------------------------

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
    extra: Dict[str, str] = field(default_factory=dict)

    def all_fields(self) -> Dict[str, str]:
        """Return all non-empty fields (known + extra) as a flat dict."""
        result: Dict[str, str] = {}
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
    extra: Dict[str, str] = field(default_factory=dict)

    def all_fields(self) -> Dict[str, str]:
        """Return all non-empty fields (known + extra) as a flat dict."""
        result: Dict[str, str] = {}
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
    specs: Dict[str, LevelSpec] = field(default_factory=dict)
    dpspins: Dict[str, DpsPinConfig] = field(default_factory=dict)
    levelsets: Dict[int, Dict[str, LevelSetPinConfig]] = field(default_factory=dict)


@dataclass(frozen=True)
class EqnSetDiff:
    """Diff result for an EQNSET block comparison."""
    suite_name: str
    eqnset_index: int
    eqnset_name: str
    dpspins_added: Dict[str, DpsPinConfig] = field(default_factory=dict)
    dpspins_removed: Dict[str, DpsPinConfig] = field(default_factory=dict)
    dpspins_changed: Dict[str, Tuple[DpsPinConfig, DpsPinConfig]] = field(default_factory=dict)
    levelsets_added: Dict[int, Dict[str, LevelSetPinConfig]] = field(default_factory=dict)
    levelsets_removed: Dict[int, Dict[str, LevelSetPinConfig]] = field(default_factory=dict)
    levelsets_changed: Dict[int, Dict[str, Tuple[LevelSetPinConfig, LevelSetPinConfig]]] = field(default_factory=dict)

    @property
    def has_changes(self) -> bool:
        return bool(
            self.dpspins_added or self.dpspins_removed or self.dpspins_changed
            or self.levelsets_added or self.levelsets_removed or self.levelsets_changed
        )


@dataclass(frozen=True)
class LevelSpecDiff:
    """Level spec differences for a single test suite."""
    suite_name: str
    added: Dict[str, LevelSpec] = field(default_factory=dict)
    removed: Dict[str, LevelSpec] = field(default_factory=dict)
    changed: Dict[str, Tuple[LevelSpec, LevelSpec]] = field(default_factory=dict)

    @property
    def has_changes(self) -> bool:
        return bool(self.added or self.removed or self.changed)


# ---------------------------------------------------------------------------
# Timing spec models
# ---------------------------------------------------------------------------

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
    extra: Dict[str, str] = field(default_factory=dict)

    def all_fields(self) -> Dict[str, str]:
        """Return all non-empty fields (known + extra) as a flat dict."""
        result: Dict[str, str] = {}
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
    extra: Dict[str, str] = field(default_factory=dict)

    def all_fields(self) -> Dict[str, str]:
        """Return all non-empty fields as a flat dict."""
        result: Dict[str, str] = {}
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
    specs: Dict[str, TimingSpec] = field(default_factory=dict)
    pins_groups: Dict[str, TimingPinConfig] = field(default_factory=dict)
    timingsets: Dict[int, TimingSetConfig] = field(default_factory=dict)


@dataclass(frozen=True)
class TimingSpecDiff:
    """Diff result for timing spec comparison."""
    suite_name: str
    spec_type: str
    spec_name: str
    added: Dict[str, TimingSpec] = field(default_factory=dict)
    removed: Dict[str, TimingSpec] = field(default_factory=dict)
    changed: Dict[str, Tuple[TimingSpec, TimingSpec]] = field(default_factory=dict)
    eqnsets_old: Tuple[Tuple[int, str], ...] = ()
    eqnsets_new: Tuple[Tuple[int, str], ...] = ()

    @property
    def has_changes(self) -> bool:
        return bool(
            self.added or self.removed or self.changed
            or self.eqnsets_old or self.eqnsets_new
        )


@dataclass(frozen=True)
class TimingEqnSetDiff:
    """Diff result for timing EQNSET block comparison."""
    suite_name: str
    eqnset_index: int
    eqnset_name: str
    specs_added: Dict[str, TimingSpec] = field(default_factory=dict)
    specs_removed: Dict[str, TimingSpec] = field(default_factory=dict)
    specs_changed: Dict[str, Tuple[TimingSpec, TimingSpec]] = field(default_factory=dict)
    pins_added: Dict[str, TimingPinConfig] = field(default_factory=dict)
    pins_removed: Dict[str, TimingPinConfig] = field(default_factory=dict)
    pins_changed: Dict[str, Tuple[TimingPinConfig, TimingPinConfig]] = field(default_factory=dict)
    timingsets_added: Dict[int, TimingSetConfig] = field(default_factory=dict)
    timingsets_removed: Dict[int, TimingSetConfig] = field(default_factory=dict)
    timingsets_changed: Dict[int, Tuple[TimingSetConfig, TimingSetConfig]] = field(default_factory=dict)

    @property
    def has_changes(self) -> bool:
        return bool(
            self.specs_added or self.specs_removed or self.specs_changed
            or self.pins_added or self.pins_removed or self.pins_changed
            or self.timingsets_added or self.timingsets_removed or self.timingsets_changed
        )


# ---------------------------------------------------------------------------
# Timing wavetable models
# ---------------------------------------------------------------------------

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
    rows: Tuple[WaveTblRow, ...] = field(default_factory=tuple)
    brk: str = ""
    f: str = ""


@dataclass(frozen=True)
class WaveTblBlock:
    """Complete WAVETBL block from timing file."""
    name: str
    pins_groups: Dict[str, WaveTblPinsGroup] = field(default_factory=dict)


@dataclass(frozen=True)
class WaveTblPinsGroupDiff:
    """Diff result for a single PINS group comparison."""
    pins_name: str
    rows_added: Tuple[WaveTblRow, ...] = field(default_factory=tuple)
    rows_removed: Tuple[WaveTblRow, ...] = field(default_factory=tuple)
    rows_changed: Tuple[Tuple[WaveTblRow, WaveTblRow], ...] = field(default_factory=tuple)
    brk_old: str = ""
    brk_new: str = ""
    f_old: str = ""
    f_new: str = ""

    @property
    def has_changes(self) -> bool:
        return bool(
            self.rows_added or self.rows_removed or self.rows_changed
            or self.brk_old != self.brk_new
            or self.f_old != self.f_new
        )


@dataclass(frozen=True)
class WaveTblDiff:
    """Diff result for a WAVETBL block comparison."""
    suite_name: str
    wavetbl_name: str
    pins_groups_added: Dict[str, WaveTblPinsGroup] = field(default_factory=dict)
    pins_groups_removed: Dict[str, WaveTblPinsGroup] = field(default_factory=dict)
    pins_groups_changed: Dict[str, WaveTblPinsGroupDiff] = field(default_factory=dict)
    old_block: Optional[WaveTblBlock] = None
    new_block: Optional[WaveTblBlock] = None
    replaced_from: Optional[str] = None

    @property
    def has_changes(self) -> bool:
        return bool(
            self.pins_groups_added or self.pins_groups_removed or self.pins_groups_changed
            or self.old_block or self.new_block or self.replaced_from
        )


@dataclass(frozen=True)
class ProgramContext:
    """Parsed context section from a flow file with resolved file paths."""
    program_root: Path
    config_file: Optional[str]      # pin config file (no subdir)
    levels_file: Optional[str]      # level file in levels/
    timing_file: Optional[str]      # timing file in timing/
    vector_file: Optional[str]      # pattern file in vectors/
    testtable_file: Optional[str]   # testtable file in testtable/

    @property
    def levels_path(self) -> Optional[Path]:
        if self.levels_file:
            return self.program_root / "levels" / self.levels_file
        return None

    @property
    def timing_path(self) -> Optional[Path]:
        if self.timing_file:
            return self.program_root / "timing" / self.timing_file
        return None

    @property
    def vector_path(self) -> Optional[Path]:
        if self.vector_file:
            return self.program_root / "vectors" / self.vector_file
        return None

    @property
    def testtable_path(self) -> Optional[Path]:
        if self.testtable_file:
            return self.program_root / "testtable" / self.testtable_file
        return None

    @property
    def config_path(self) -> Optional[Path]:
        if self.config_file:
            return self.program_root / self.config_file
        return None

    def all_paths(self) -> Dict[str, Optional[Path]]:
        """Return all resolved paths as a dict."""
        return {
            "levels": self.levels_path,
            "timing": self.timing_path,
            "vectors": self.vector_path,
            "testtable": self.testtable_path,
            "config": self.config_path,
        }


@dataclass
class SuiteConfigView:
    """Complete configuration view for a single test suite."""
    suite_name: str
    flow_config: Dict[str, str]
    timing_spec_set: Optional[str]
    level_eqn_set: Optional[int]
    level_spec_set: Optional[int]
    level_levset: Optional[int]
    timing_snippet: Optional[str]
    level_snippet: Optional[str]
    level_specs: Optional[Dict[str, LevelSpec]]
    eqnset_block: Optional[EqnSetBlock] = None
    timing_eqn_set: Optional[int] = None
    timing_spec_index: Optional[int] = None
    timing_specs: Optional[Dict[str, TimingSpec]] = None
    timing_eqnset_block: Optional[TimingEqnSetBlock] = None
    timing_spec_eqnsets: Optional[List[Tuple[int, str]]] = None
    timing_eqnset_blocks: Dict[int, TimingEqnSetBlock] = field(default_factory=dict)
    timing_wavetbl_names: Tuple[str, ...] = field(default_factory=tuple)
    timing_wavetbl_blocks: Dict[str, WaveTblBlock] = field(default_factory=dict)
