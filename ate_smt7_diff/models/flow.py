#!/usr/bin/env python3
"""Flow diff models and top-level diff report."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from functools import cached_property

from ate_smt7_diff.models.level import EqnSetDiff, LevelSpecDiff
from ate_smt7_diff.models.suite import SuiteConfigReport, SuiteConfigView
from ate_smt7_diff.models.testmethod import TestMethodDiff
from ate_smt7_diff.models.testtable import TestTableSuiteDiff
from ate_smt7_diff.models.timing import TimingEqnSetDiff, TimingSpecDiff
from ate_smt7_diff.models.vector import VectorSuiteDiff
from ate_smt7_diff.models.wavetable import WaveTblDiff


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
    suite_config_report: SuiteConfigReport | None = None
    old_suite_views: dict[str, SuiteConfigView] | None = None
    new_suite_views: dict[str, SuiteConfigView] | None = None
    level_spec_diffs: list[LevelSpecDiff] | None = None
    eqnset_diffs: list[EqnSetDiff] | None = None
    timing_spec_diffs: list[TimingSpecDiff] | None = None
    timing_eqnset_diffs: list[TimingEqnSetDiff] | None = None
    timing_wavetbl_diffs: list[WaveTblDiff] | None = None
    testtable_diffs: list[TestTableSuiteDiff] | None = None
    vector_diffs: list[VectorSuiteDiff] | None = None
    testmethod_diffs: list[TestMethodDiff] | None = None

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
