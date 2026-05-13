#!/usr/bin/env python3
"""TestTable CSV row models."""

from __future__ import annotations

from dataclasses import dataclass, field


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
