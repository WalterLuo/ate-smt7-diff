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
from typing import Optional

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
    group_path: tuple[str, ...]
    line_number: int
    is_branch: bool


@dataclass(frozen=True)
class FlowDiff:
    """Difference result for a single test occurrence."""

    suite_name: str
    diff_type: DiffType
    old_index: int | None
    new_index: int | None
    old_group_path: tuple[str, ...]
    new_group_path: tuple[str, ...]


@dataclass
class DiffReport:
    """Complete diff report between two flows."""

    old_file: str
    new_file: str
    old_tests: list[TestItem]
    new_tests: list[TestItem]
    diffs: list[FlowDiff]
    suite_config_report: Optional["SuiteConfigReport"] = None
    old_suite_views: dict[str, "SuiteConfigView"] | None = None
    new_suite_views: dict[str, "SuiteConfigView"] | None = None
    level_spec_diffs: list["LevelSpecDiff"] | None = None
    eqnset_diffs: list["EqnSetDiff"] | None = None
    timing_spec_diffs: list["TimingSpecDiff"] | None = None
    timing_eqnset_diffs: list["TimingEqnSetDiff"] | None = None
    timing_wavetbl_diffs: list["WaveTblDiff"] | None = None
    testtable_diffs: list["TestTableSuiteDiff"] | None = None
    vector_diffs: list["VectorSuiteDiff"] | None = None
    testmethod_diffs: list["TestMethodDiff"] | None = None

    @cached_property
    def added(self) -> list[str]:
        return sorted({d.suite_name for d in self.diffs if d.diff_type == DiffType.ADDED})

    @cached_property
    def removed(self) -> list[str]:
        return sorted({d.suite_name for d in self.diffs if d.diff_type == DiffType.REMOVED})

    @cached_property
    def moved(self) -> list[str]:
        return sorted({d.suite_name for d in self.diffs if d.diff_type == DiffType.MOVED})

    @cached_property
    def unchanged(self) -> list[str]:
        return sorted({d.suite_name for d in self.diffs if d.diff_type == DiffType.UNCHANGED})

    @cached_property
    def order_changed(self) -> list[str]:
        from ate_smt7_diff.diff.flow_diff import compute_order_changes

        return compute_order_changes(self.old_tests, self.new_tests)


# ---------------------------------------------------------------------------
# Suite config models (from suite_config.py)
# ---------------------------------------------------------------------------


@dataclass
class SuiteConfigDiff:
    """Configuration differences for a single test suite."""

    suite_name: str
    changed: dict[str, tuple[str, str]] = field(default_factory=dict)
    added: dict[str, str] = field(default_factory=dict)
    removed: dict[str, str] = field(default_factory=dict)

    @property
    def has_changes(self) -> bool:
        return bool(self.changed or self.added or self.removed)


@dataclass
class SuiteConfigReport:
    """Complete suite configuration diff report."""

    old_file: str
    new_file: str
    diffs: list[SuiteConfigDiff]
    common_suites: list[str]
    skipped_suites: list[str]

    @cached_property
    def suites_with_changes(self) -> list[str]:
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


@dataclass(frozen=True)
class TestTableRow:
    """A single row from a testtable CSV file."""

    suite_name: str
    test_name: str
    test_number: str
    columns: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class TestTableRowDiff:
    """Column-level changes for a single row with matching key."""

    test_name: str
    test_number: str
    changed: dict[str, tuple[str, str]] = field(default_factory=dict)


@dataclass(frozen=True)
class TestTableSuiteDiff:
    """Diff result for all testtable rows belonging to one suite."""

    suite_name: str
    rows_added: tuple[TestTableRow, ...] = field(default_factory=tuple)
    rows_removed: tuple[TestTableRow, ...] = field(default_factory=tuple)
    rows_changed: tuple[TestTableRowDiff, ...] = field(default_factory=tuple)

    @property
    def has_changes(self) -> bool:
        return bool(self.rows_added or self.rows_removed or self.rows_changed)


# ---------------------------------------------------------------------------
# Vector / Pattern models
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class VectorPatternMapping:
    """A single pattern-to-file mapping from the vector file."""

    pattern_name: str
    mapped_file: str | None
    is_direct: bool


@dataclass(frozen=True)
class VectorSuiteMapping:
    """Resolved vector mappings for a single suite.

    ``path`` is the absolute resolved directory where mapped files live.
    """

    suite_name: str
    seqlbl: str
    path: str
    pattern_mappings: tuple[VectorPatternMapping, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class VectorFileDateChange:
    """A single file whose modification date differs."""

    file_path: str
    old_mtime: float
    new_mtime: float


@dataclass(frozen=True)
class VectorSuiteDiff:
    """Diff result for vector mappings of a single suite."""

    suite_name: str
    diff_type: str
    old_mappings: tuple[VectorPatternMapping, ...] | None = None
    new_mappings: tuple[VectorPatternMapping, ...] | None = None
    file_date_changes: tuple[VectorFileDateChange, ...] = field(default_factory=tuple)

    @property
    def has_changes(self) -> bool:
        return bool(self.diff_type in ("changed", "added", "removed", "file_date_changed"))


@dataclass(frozen=True)
class TestMethodInfo:
    """Resolved testmethod metadata and source file for a single suite."""

    tm_id: str
    testmethod_class: str
    file_path: Path | None = None
    content: str | None = None


@dataclass(frozen=True)
class TestMethodDiff:
    """Diff result for a suite's testmethod reference and optional source diff."""

    suite_name: str
    diff_type: str  # unchanged, tm_id_changed, class_changed, both_changed, file_changed, file_not_found
    old_tm_id: str | None = None
    new_tm_id: str | None = None
    old_class: str | None = None
    new_class: str | None = None
    file_diff: tuple[str, ...] = field(default_factory=tuple)

    @property
    def has_changes(self) -> bool:
        return self.diff_type != "unchanged"


@dataclass(frozen=True)
class ProgramContext:
    """Parsed context section from a flow file with resolved file paths."""

    program_root: Path
    config_file: str | None  # pin config file (no subdir)
    levels_file: str | None  # level file in levels/
    timing_file: str | None  # timing file in timing/
    vector_file: str | None  # pattern file in vectors/
    testtable_file: str | None  # testtable file in testtable/

    @property
    def levels_path(self) -> Path | None:
        if self.levels_file:
            return self.program_root / "levels" / self.levels_file
        return None

    @property
    def timing_path(self) -> Path | None:
        if self.timing_file:
            return self.program_root / "timing" / self.timing_file
        return None

    @property
    def vector_path(self) -> Path | None:
        if self.vector_file:
            return self.program_root / "vectors" / self.vector_file
        return None

    @property
    def testtable_path(self) -> Path | None:
        if self.testtable_file:
            return self.program_root / "testtable" / self.testtable_file
        return None

    @property
    def config_path(self) -> Path | None:
        if self.config_file:
            return self.program_root / self.config_file
        return None

    def all_paths(self) -> dict[str, Path | None]:
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
    flow_config: dict[str, str]
    timing_spec_set: str | None
    level_eqn_set: int | None
    level_spec_set: int | None
    level_levset: int | None
    timing_snippet: str | None
    level_snippet: str | None
    level_specs: dict[str, LevelSpec] | None
    eqnset_block: EqnSetBlock | None = None
    timing_eqn_set: int | None = None
    timing_spec_index: int | None = None
    timing_specs: dict[str, TimingSpec] | None = None
    timing_eqnset_block: TimingEqnSetBlock | None = None
    timing_spec_eqnsets: list[tuple[int, str]] | None = None
    timing_eqnset_blocks: dict[int, TimingEqnSetBlock] = field(default_factory=dict)
    timing_wavetbl_names: tuple[str, ...] = field(default_factory=tuple)
    timing_wavetbl_blocks: dict[str, WaveTblBlock] = field(default_factory=dict)
    testtable_rows: dict[tuple[str, str, str], "TestTableRow"] | None = None
    vector_mappings: VectorSuiteMapping | None = None
    testmethod: TestMethodInfo | None = None


@dataclass
class BatchDiffReport:
    """Aggregated diff report for multiple flow file pairs."""

    old_package: str
    new_package: str
    pairs: list[tuple[str, str, DiffReport]] = field(default_factory=list)

    @property
    def total_pairs(self) -> int:
        return len(self.pairs)

    @property
    def pairs_with_changes(self) -> list[tuple[str, str, DiffReport]]:
        return [
            (o, n, r)
            for o, n, r in self.pairs
            if r.added or r.removed or r.moved or r.order_changed
        ]
