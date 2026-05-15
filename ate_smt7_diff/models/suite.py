#!/usr/bin/env python3
"""Suite configuration and hydrated view models."""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import cached_property

from ate_smt7_diff.models.level import EqnSetBlock, LevelSpec
from ate_smt7_diff.models.testmethod import TestMethodInfo
from ate_smt7_diff.models.testtable import TestTableRow
from ate_smt7_diff.models.timing import TimingEqnSetBlock, TimingSpec
from ate_smt7_diff.models.vector import VectorSuiteMapping
from ate_smt7_diff.models.wavetable import WaveTblBlock


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


@dataclass
class SuiteConfigView:
    """Complete configuration view for a single test suite."""

    suite_name: str
    flow_config: dict[str, str]
    timing_spec_set: str | None
    level_eqn_set: int | None
    level_spec_set: int | None
    timing_snippet: str | None
    level_snippet: str | None
    level_specs: dict[str, LevelSpec] | None
    eqnset_block: EqnSetBlock | None = None
    timing_eqn_set: int | None = None
    timing_specs: dict[str, TimingSpec] | None = None
    timing_eqnset_block: TimingEqnSetBlock | None = None
    timing_spec_eqnsets: list[tuple[int, str]] | None = None
    timing_eqnset_blocks: dict[int, TimingEqnSetBlock] = field(default_factory=dict)
    timing_wavetbl_names: tuple[str, ...] = field(default_factory=tuple)
    timing_wavetbl_blocks: dict[str, WaveTblBlock] = field(default_factory=dict)
    testtable_rows: dict[tuple[str, str, str], TestTableRow] | None = None
    vector_mappings: VectorSuiteMapping | None = None
    testmethod: TestMethodInfo | None = None
