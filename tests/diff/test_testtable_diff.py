#!/usr/bin/env python3
"""Tests for testtable_diff.py."""

import pytest

from ate_smt7_diff.diff.testtable_diff import diff_testtable_suites, diff_testtables
from ate_smt7_diff.models import TestTableRow, TestTableRowDiff, TestTableSuiteDiff


class TestDiffTestTableSuites:
    def test_no_changes_returns_none(self) -> None:
        rows = {
            ("SuiteA", "test1", "100"): TestTableRow(
                suite_name="SuiteA", test_name="test1", test_number="100",
                columns={"Lsl": "10", "Usl": "20"}
            ),
        }
        result = diff_testtable_suites("SuiteA", rows, rows)
        assert result is None

    def test_added_rows(self) -> None:
        old_rows = {
            ("SuiteA", "test1", "100"): TestTableRow(
                suite_name="SuiteA", test_name="test1", test_number="100",
                columns={"Lsl": "10"}
            ),
        }
        new_rows = {
            ("SuiteA", "test1", "100"): TestTableRow(
                suite_name="SuiteA", test_name="test1", test_number="100",
                columns={"Lsl": "10"}
            ),
            ("SuiteA", "test2", "101"): TestTableRow(
                suite_name="SuiteA", test_name="test2", test_number="101",
                columns={"Lsl": "15"}
            ),
        }
        result = diff_testtable_suites("SuiteA", old_rows, new_rows)
        assert result is not None
        assert len(result.rows_added) == 1
        assert result.rows_added[0].test_name == "test2"
        assert len(result.rows_removed) == 0
        assert len(result.rows_changed) == 0

    def test_removed_rows(self) -> None:
        old_rows = {
            ("SuiteA", "test1", "100"): TestTableRow(
                suite_name="SuiteA", test_name="test1", test_number="100",
                columns={"Lsl": "10"}
            ),
            ("SuiteA", "test2", "101"): TestTableRow(
                suite_name="SuiteA", test_name="test2", test_number="101",
                columns={"Lsl": "15"}
            ),
        }
        new_rows = {
            ("SuiteA", "test1", "100"): TestTableRow(
                suite_name="SuiteA", test_name="test1", test_number="100",
                columns={"Lsl": "10"}
            ),
        }
        result = diff_testtable_suites("SuiteA", old_rows, new_rows)
        assert result is not None
        assert len(result.rows_added) == 0
        assert len(result.rows_removed) == 1
        assert result.rows_removed[0].test_name == "test2"
        assert len(result.rows_changed) == 0

    def test_changed_columns(self) -> None:
        old_rows = {
            ("SuiteA", "test1", "100"): TestTableRow(
                suite_name="SuiteA", test_name="test1", test_number="100",
                columns={"Lsl": "10", "Usl": "20"}
            ),
        }
        new_rows = {
            ("SuiteA", "test1", "100"): TestTableRow(
                suite_name="SuiteA", test_name="test1", test_number="100",
                columns={"Lsl": "12", "Usl": "20"}
            ),
        }
        result = diff_testtable_suites("SuiteA", old_rows, new_rows)
        assert result is not None
        assert len(result.rows_added) == 0
        assert len(result.rows_removed) == 0
        assert len(result.rows_changed) == 1
        changed = result.rows_changed[0]
        assert changed.test_name == "test1"
        assert changed.changed == {"Lsl": ("10", "12")}

    def test_multiple_column_changes(self) -> None:
        old_rows = {
            ("SuiteA", "test1", "100"): TestTableRow(
                suite_name="SuiteA", test_name="test1", test_number="100",
                columns={"Lsl": "10", "Usl": "20", "Units": "V"}
            ),
        }
        new_rows = {
            ("SuiteA", "test1", "100"): TestTableRow(
                suite_name="SuiteA", test_name="test1", test_number="100",
                columns={"Lsl": "12", "Usl": "25", "Units": "V"}
            ),
        }
        result = diff_testtable_suites("SuiteA", old_rows, new_rows)
        assert result is not None
        changed = result.rows_changed[0]
        assert changed.changed == {"Lsl": ("10", "12"), "Usl": ("20", "25")}

    def test_added_column(self) -> None:
        old_rows = {
            ("SuiteA", "test1", "100"): TestTableRow(
                suite_name="SuiteA", test_name="test1", test_number="100",
                columns={"Lsl": "10"}
            ),
        }
        new_rows = {
            ("SuiteA", "test1", "100"): TestTableRow(
                suite_name="SuiteA", test_name="test1", test_number="100",
                columns={"Lsl": "10", "Usl": "20"}
            ),
        }
        result = diff_testtable_suites("SuiteA", old_rows, new_rows)
        assert result is not None
        changed = result.rows_changed[0]
        assert changed.changed == {"Usl": ("", "20")}

    def test_removed_column(self) -> None:
        old_rows = {
            ("SuiteA", "test1", "100"): TestTableRow(
                suite_name="SuiteA", test_name="test1", test_number="100",
                columns={"Lsl": "10", "Usl": "20"}
            ),
        }
        new_rows = {
            ("SuiteA", "test1", "100"): TestTableRow(
                suite_name="SuiteA", test_name="test1", test_number="100",
                columns={"Lsl": "10"}
            ),
        }
        result = diff_testtable_suites("SuiteA", old_rows, new_rows)
        assert result is not None
        changed = result.rows_changed[0]
        assert changed.changed == {"Usl": ("20", "")}


class TestDiffTestTables:
    def test_diff_multiple_suites(self) -> None:
        old_rows_by_suite = {
            "SuiteA": {
                ("SuiteA", "test1", "100"): TestTableRow(
                    suite_name="SuiteA", test_name="test1", test_number="100",
                    columns={"Lsl": "10"}
                ),
            },
            "SuiteB": {
                ("SuiteB", "test1", "200"): TestTableRow(
                    suite_name="SuiteB", test_name="test1", test_number="200",
                    columns={"Lsl": "5"}
                ),
            },
        }
        new_rows_by_suite = {
            "SuiteA": {
                ("SuiteA", "test1", "100"): TestTableRow(
                    suite_name="SuiteA", test_name="test1", test_number="100",
                    columns={"Lsl": "15"}
                ),
            },
            "SuiteB": {
                ("SuiteB", "test1", "200"): TestTableRow(
                    suite_name="SuiteB", test_name="test1", test_number="200",
                    columns={"Lsl": "5"}
                ),
            },
        }
        result = diff_testtables(["SuiteA", "SuiteB"], old_rows_by_suite, new_rows_by_suite)
        assert len(result) == 1
        assert result[0].suite_name == "SuiteA"
        assert len(result[0].rows_changed) == 1

    def test_empty_old_rows(self) -> None:
        old_rows_by_suite = {"SuiteA": {}}
        new_rows_by_suite = {
            "SuiteA": {
                ("SuiteA", "test1", "100"): TestTableRow(
                    suite_name="SuiteA", test_name="test1", test_number="100",
                    columns={"Lsl": "10"}
                ),
            },
        }
        result = diff_testtables(["SuiteA"], old_rows_by_suite, new_rows_by_suite)
        assert len(result) == 1
        assert len(result[0].rows_added) == 1
        assert len(result[0].rows_removed) == 0

    def test_empty_new_rows(self) -> None:
        old_rows_by_suite = {
            "SuiteA": {
                ("SuiteA", "test1", "100"): TestTableRow(
                    suite_name="SuiteA", test_name="test1", test_number="100",
                    columns={"Lsl": "10"}
                ),
            },
        }
        new_rows_by_suite = {"SuiteA": {}}
        result = diff_testtables(["SuiteA"], old_rows_by_suite, new_rows_by_suite)
        assert len(result) == 1
        assert len(result[0].rows_added) == 0
        assert len(result[0].rows_removed) == 1

    def test_both_empty_rows_returns_none(self) -> None:
        old_rows = {}
        new_rows = {}
        result = diff_testtable_suites("SuiteA", old_rows, new_rows)
        assert result is None

    def test_suite_missing_from_both_dicts(self) -> None:
        result = diff_testtables(
            ["SuiteA"],
            old_rows_by_suite={},
            new_rows_by_suite={},
        )
        assert result == []

    def test_empty_string_values_not_reported(self) -> None:
        old_rows = {
            ("SuiteA", "test1", "100"): TestTableRow(
                suite_name="SuiteA", test_name="test1", test_number="100",
                columns={"Lsl": "", "Usl": ""}
            ),
        }
        new_rows = {
            ("SuiteA", "test1", "100"): TestTableRow(
                suite_name="SuiteA", test_name="test1", test_number="100",
                columns={"Lsl": "", "Usl": ""}
            ),
        }
        result = diff_testtable_suites("SuiteA", old_rows, new_rows)
        assert result is None

    def test_test_number_change_treated_as_changed(self) -> None:
        old_rows = {
            ("SuiteA", "test1", "100"): TestTableRow(
                suite_name="SuiteA", test_name="test1", test_number="100",
                columns={"Suite name": "SuiteA", "Test name": "test1", "Test number": "100", "Lsl": "10"}
            ),
        }
        new_rows = {
            ("SuiteA", "test1", "200"): TestTableRow(
                suite_name="SuiteA", test_name="test1", test_number="200",
                columns={"Suite name": "SuiteA", "Test name": "test1", "Test number": "200", "Lsl": "10"}
            ),
        }
        result = diff_testtable_suites("SuiteA", old_rows, new_rows)
        assert result is not None
        assert len(result.rows_added) == 0
        assert len(result.rows_removed) == 0
        assert len(result.rows_changed) == 1
        changed = result.rows_changed[0]
        assert changed.test_name == "test1"
        assert changed.test_number == "200"
        assert changed.changed == {"Test number": ("100", "200")}

    def test_test_number_and_column_change(self) -> None:
        old_rows = {
            ("SuiteA", "test1", "100"): TestTableRow(
                suite_name="SuiteA", test_name="test1", test_number="100",
                columns={"Suite name": "SuiteA", "Test name": "test1", "Test number": "100", "Lsl": "10", "Usl": "20"}
            ),
        }
        new_rows = {
            ("SuiteA", "test1", "200"): TestTableRow(
                suite_name="SuiteA", test_name="test1", test_number="200",
                columns={"Suite name": "SuiteA", "Test name": "test1", "Test number": "200", "Lsl": "15", "Usl": "20"}
            ),
        }
        result = diff_testtable_suites("SuiteA", old_rows, new_rows)
        assert result is not None
        assert len(result.rows_changed) == 1
        changed = result.rows_changed[0]
        assert changed.changed == {
            "Lsl": ("10", "15"),
            "Test number": ("100", "200"),
        }
