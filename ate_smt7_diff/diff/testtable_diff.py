#!/usr/bin/env python3
"""
Testtable diff algorithms.
Compares rows between old and new testtable files per suite.
Rows are matched by (suite_name, test_name); test_number is treated
as a regular column and reported in changed when it differs.
"""

from typing import Dict, List, Optional, Tuple

from ate_smt7_diff.models import TestTableRow, TestTableRowDiff, TestTableSuiteDiff


def _rows_by_test_name(
    rows: Dict[Tuple[str, str, str], TestTableRow]
) -> Dict[Tuple[str, str], TestTableRow]:
    """Re-index rows by (suite_name, test_name)."""
    result: Dict[Tuple[str, str], TestTableRow] = {}
    for key, row in rows.items():
        name_key = (key[0], key[1])
        result[name_key] = row
    return result


def diff_testtable_suites(
    suite_name: str,
    old_rows: Dict[Tuple[str, str, str], TestTableRow],
    new_rows: Dict[Tuple[str, str, str], TestTableRow],
) -> Optional[TestTableSuiteDiff]:
    """Compare testtable rows for a single suite.

    Rows are matched by (suite_name, test_name).  test_number is treated
    as a regular column.  Suite name and Test name are excluded from
    column-level change detection because they are the matching keys.

    Returns None if there are no differences.
    """
    old_by_name = _rows_by_test_name(old_rows)
    new_by_name = _rows_by_test_name(new_rows)

    old_names = set(old_by_name.keys())
    new_names = set(new_by_name.keys())

    added = tuple(new_by_name[k] for k in sorted(new_names - old_names))
    removed = tuple(old_by_name[k] for k in sorted(old_names - new_names))

    changed_rows: List[TestTableRowDiff] = []
    for k in sorted(old_names & new_names):
        old_row = old_by_name[k]
        new_row = new_by_name[k]
        column_changes: Dict[str, Tuple[str, str]] = {}
        all_cols = set(old_row.columns.keys()) | set(new_row.columns.keys())
        for col in sorted(all_cols):
            if col in ("Suite name", "Test name"):
                continue
            old_val = old_row.columns.get(col, "")
            new_val = new_row.columns.get(col, "")
            if old_val != new_val:
                column_changes[col] = (old_val, new_val)
        if column_changes:
            changed_rows.append(
                TestTableRowDiff(
                    test_name=k[1],
                    test_number=new_row.test_number,
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
