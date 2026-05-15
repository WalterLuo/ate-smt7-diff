#!/usr/bin/env python3
"""
Testtable diff algorithms.
Compares rows between old and new testtable files per suite.
Only USL and LSL column changes are reported for matching test items.
"""

from ate_smt7_diff.models import TestTableRow, TestTableRowDiff, TestTableSuiteDiff


def _rows_by_test_name(
    rows: dict[tuple[str, str, str], TestTableRow],
) -> dict[tuple[str, str], TestTableRow]:
    """Re-index rows by (suite_name, test_name)."""
    result: dict[tuple[str, str], TestTableRow] = {}
    for key, row in rows.items():
        name_key = (key[0], key[1])
        result[name_key] = row
    return result


def _get_limit_value(columns: dict[str, str], target: str) -> str:
    """Get column value by case-insensitive target name (e.g. 'usl', 'lsl')."""
    target_lower = target.lower()
    for col, val in columns.items():
        if col.strip().lower() == target_lower:
            return val
    return ""


def diff_testtable_suites(
    suite_name: str,
    old_rows: dict[tuple[str, str, str], TestTableRow],
    new_rows: dict[tuple[str, str, str], TestTableRow],
) -> TestTableSuiteDiff | None:
    """Compare testtable rows for a single suite.

    Only rows present in both old and new are compared.
    Only USL and LSL column changes are reported.

    Returns None if there are no USL/LSL differences.
    """
    old_by_name = _rows_by_test_name(old_rows)
    new_by_name = _rows_by_test_name(new_rows)

    old_names = set(old_by_name.keys())
    new_names = set(new_by_name.keys())

    changed_rows: list[TestTableRowDiff] = []
    for k in sorted(old_names & new_names):
        old_row = old_by_name[k]
        new_row = new_by_name[k]
        column_changes: dict[str, tuple[str, str]] = {}

        old_usl = _get_limit_value(old_row.columns, "usl")
        new_usl = _get_limit_value(new_row.columns, "usl")
        if old_usl != new_usl:
            column_changes["USL"] = (old_usl, new_usl)

        old_lsl = _get_limit_value(old_row.columns, "lsl")
        new_lsl = _get_limit_value(new_row.columns, "lsl")
        if old_lsl != new_lsl:
            column_changes["LSL"] = (old_lsl, new_lsl)

        if column_changes:
            changed_rows.append(
                TestTableRowDiff(
                    test_name=k[1],
                    test_number=new_row.test_number,
                    changed=column_changes,
                )
            )

    if not changed_rows:
        return None

    return TestTableSuiteDiff(
        suite_name=suite_name,
        rows_added=(),
        rows_removed=(),
        rows_changed=tuple(changed_rows),
    )


def diff_testtables(
    common_suites: list[str],
    old_rows_by_suite: dict[str, dict[tuple[str, str, str], TestTableRow]],
    new_rows_by_suite: dict[str, dict[tuple[str, str, str], TestTableRow]],
) -> list[TestTableSuiteDiff]:
    """Compare testtables for all common suites.

    Returns a list of TestTableSuiteDiff with changes only.
    """
    diffs: list[TestTableSuiteDiff] = []
    for suite_name in common_suites:
        old_rows = old_rows_by_suite.get(suite_name, {})
        new_rows = new_rows_by_suite.get(suite_name, {})
        diff = diff_testtable_suites(suite_name, old_rows, new_rows)
        if diff is not None:
            diffs.append(diff)
    return diffs
