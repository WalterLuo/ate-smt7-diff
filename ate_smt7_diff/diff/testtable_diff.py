#!/usr/bin/env python3
"""
Testtable diff algorithms.
Compares rows between old and new testtable files per suite.
"""

from typing import Dict, List, Optional, Tuple

from ate_smt7_diff.models import TestTableRow, TestTableRowDiff, TestTableSuiteDiff


def diff_testtable_suites(
    suite_name: str,
    old_rows: Dict[Tuple[str, str, str], TestTableRow],
    new_rows: Dict[Tuple[str, str, str], TestTableRow],
) -> Optional[TestTableSuiteDiff]:
    """Compare testtable rows for a single suite.

    Returns None if there are no differences.
    """
    old_keys = set(old_rows.keys())
    new_keys = set(new_rows.keys())

    added = tuple(new_rows[k] for k in sorted(new_keys - old_keys))
    removed = tuple(old_rows[k] for k in sorted(old_keys - new_keys))

    changed_rows: List[TestTableRowDiff] = []
    for k in sorted(old_keys & new_keys):
        old_row = old_rows[k]
        new_row = new_rows[k]
        column_changes: Dict[str, Tuple[str, str]] = {}
        all_cols = set(old_row.columns.keys()) | set(new_row.columns.keys())
        for col in sorted(all_cols):
            old_val = old_row.columns.get(col, "")
            new_val = new_row.columns.get(col, "")
            if old_val != new_val:
                column_changes[col] = (old_val, new_val)
        if column_changes:
            changed_rows.append(
                TestTableRowDiff(
                    test_name=k[1],
                    test_number=k[2],
                    changed=column_changes,
                )
            )

    if not added and not removed and not changed_rows:
        return None

    return TestTableSuiteDiff(
        suite_name=suite_name,
        rows_added=added,
        rows_removed=removed,
        rows_changed=tuple(changed_rows),
    )


def diff_testtables(
    common_suites: List[str],
    old_rows_by_suite: Dict[str, Dict[Tuple[str, str, str], TestTableRow]],
    new_rows_by_suite: Dict[str, Dict[Tuple[str, str, str], TestTableRow]],
) -> List[TestTableSuiteDiff]:
    """Compare testtables for all common suites.

    Returns a list of TestTableSuiteDiff with changes only.
    """
    diffs: List[TestTableSuiteDiff] = []
    for suite_name in common_suites:
        old_rows = old_rows_by_suite.get(suite_name, {})
        new_rows = new_rows_by_suite.get(suite_name, {})
        diff = diff_testtable_suites(suite_name, old_rows, new_rows)
        if diff is not None:
            diffs.append(diff)
    return diffs
