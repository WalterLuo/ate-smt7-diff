#!/usr/bin/env python3
"""Tests for testtable_diff.py."""

from ate_smt7_diff.diff.testtable_diff import diff_testtable_suites, diff_testtables
from ate_smt7_diff.models import TestTableRow


class TestDiffTestTableSuites:
    def test_no_changes_returns_none(self) -> None:
        rows = {
            ("SuiteA", "test1", "100"): TestTableRow(
                suite_name="SuiteA",
                test_name="test1",
                test_number="100",
                columns={"Lsl": "10", "Usl": "20"},
            ),
        }
        result = diff_testtable_suites("SuiteA", rows, rows)
        assert result is None

    def test_no_changes_ignores_non_limit_columns(self) -> None:
        old_rows = {
            ("SuiteA", "test1", "100"): TestTableRow(
                suite_name="SuiteA",
                test_name="test1",
                test_number="100",
                columns={"Lsl": "10", "Usl": "20", "Units": "V"},
            ),
        }
        new_rows = {
            ("SuiteA", "test1", "100"): TestTableRow(
                suite_name="SuiteA",
                test_name="test1",
                test_number="100",
                columns={"Lsl": "10", "Usl": "20", "Units": "A"},
            ),
        }
        result = diff_testtable_suites("SuiteA", old_rows, new_rows)
        assert result is None

    def test_added_rows_ignored(self) -> None:
        old_rows = {
            ("SuiteA", "test1", "100"): TestTableRow(
                suite_name="SuiteA", test_name="test1", test_number="100", columns={"Lsl": "10"}
            ),
        }
        new_rows = {
            ("SuiteA", "test1", "100"): TestTableRow(
                suite_name="SuiteA", test_name="test1", test_number="100", columns={"Lsl": "10"}
            ),
            ("SuiteA", "test2", "101"): TestTableRow(
                suite_name="SuiteA", test_name="test2", test_number="101", columns={"Lsl": "15"}
            ),
        }
        result = diff_testtable_suites("SuiteA", old_rows, new_rows)
        assert result is None

    def test_removed_rows_ignored(self) -> None:
        old_rows = {
            ("SuiteA", "test1", "100"): TestTableRow(
                suite_name="SuiteA", test_name="test1", test_number="100", columns={"Lsl": "10"}
            ),
            ("SuiteA", "test2", "101"): TestTableRow(
                suite_name="SuiteA", test_name="test2", test_number="101", columns={"Lsl": "15"}
            ),
        }
        new_rows = {
            ("SuiteA", "test1", "100"): TestTableRow(
                suite_name="SuiteA", test_name="test1", test_number="100", columns={"Lsl": "10"}
            ),
        }
        result = diff_testtable_suites("SuiteA", old_rows, new_rows)
        assert result is None

    def test_lsl_changed(self) -> None:
        old_rows = {
            ("SuiteA", "test1", "100"): TestTableRow(
                suite_name="SuiteA",
                test_name="test1",
                test_number="100",
                columns={"Lsl": "10", "Usl": "20"},
            ),
        }
        new_rows = {
            ("SuiteA", "test1", "100"): TestTableRow(
                suite_name="SuiteA",
                test_name="test1",
                test_number="100",
                columns={"Lsl": "12", "Usl": "20"},
            ),
        }
        result = diff_testtable_suites("SuiteA", old_rows, new_rows)
        assert result is not None
        assert len(result.rows_added) == 0
        assert len(result.rows_removed) == 0
        assert len(result.rows_changed) == 1
        changed = result.rows_changed[0]
        assert changed.test_name == "test1"
        assert changed.changed == {"LSL": ("10", "12")}

    def test_usl_changed(self) -> None:
        old_rows = {
            ("SuiteA", "test1", "100"): TestTableRow(
                suite_name="SuiteA",
                test_name="test1",
                test_number="100",
                columns={"Lsl": "10", "Usl": "20"},
            ),
        }
        new_rows = {
            ("SuiteA", "test1", "100"): TestTableRow(
                suite_name="SuiteA",
                test_name="test1",
                test_number="100",
                columns={"Lsl": "10", "Usl": "25"},
            ),
        }
        result = diff_testtable_suites("SuiteA", old_rows, new_rows)
        assert result is not None
        changed = result.rows_changed[0]
        assert changed.changed == {"USL": ("20", "25")}

    def test_both_usl_and_lsl_changed(self) -> None:
        old_rows = {
            ("SuiteA", "test1", "100"): TestTableRow(
                suite_name="SuiteA",
                test_name="test1",
                test_number="100",
                columns={"Lsl": "10", "Usl": "20", "Units": "V"},
            ),
        }
        new_rows = {
            ("SuiteA", "test1", "100"): TestTableRow(
                suite_name="SuiteA",
                test_name="test1",
                test_number="100",
                columns={"Lsl": "12", "Usl": "25", "Units": "V"},
            ),
        }
        result = diff_testtable_suites("SuiteA", old_rows, new_rows)
        assert result is not None
        changed = result.rows_changed[0]
        assert changed.changed == {"LSL": ("10", "12"), "USL": ("20", "25")}

    def test_usl_added(self) -> None:
        old_rows = {
            ("SuiteA", "test1", "100"): TestTableRow(
                suite_name="SuiteA", test_name="test1", test_number="100", columns={"Lsl": "10"}
            ),
        }
        new_rows = {
            ("SuiteA", "test1", "100"): TestTableRow(
                suite_name="SuiteA",
                test_name="test1",
                test_number="100",
                columns={"Lsl": "10", "Usl": "20"},
            ),
        }
        result = diff_testtable_suites("SuiteA", old_rows, new_rows)
        assert result is not None
        changed = result.rows_changed[0]
        assert changed.changed == {"USL": ("", "20")}

    def test_usl_removed(self) -> None:
        old_rows = {
            ("SuiteA", "test1", "100"): TestTableRow(
                suite_name="SuiteA",
                test_name="test1",
                test_number="100",
                columns={"Lsl": "10", "Usl": "20"},
            ),
        }
        new_rows = {
            ("SuiteA", "test1", "100"): TestTableRow(
                suite_name="SuiteA", test_name="test1", test_number="100", columns={"Lsl": "10"}
            ),
        }
        result = diff_testtable_suites("SuiteA", old_rows, new_rows)
        assert result is not None
        changed = result.rows_changed[0]
        assert changed.changed == {"USL": ("20", "")}

    def test_case_insensitive_column_names(self) -> None:
        old_rows = {
            ("SuiteA", "test1", "100"): TestTableRow(
                suite_name="SuiteA",
                test_name="test1",
                test_number="100",
                columns={"lsl": "10", "usl": "20"},
            ),
        }
        new_rows = {
            ("SuiteA", "test1", "100"): TestTableRow(
                suite_name="SuiteA",
                test_name="test1",
                test_number="100",
                columns={"lsl": "12", "usl": "20"},
            ),
        }
        result = diff_testtable_suites("SuiteA", old_rows, new_rows)
        assert result is not None
        changed = result.rows_changed[0]
        assert changed.changed == {"LSL": ("10", "12")}

    def test_empty_string_values_not_reported(self) -> None:
        old_rows = {
            ("SuiteA", "test1", "100"): TestTableRow(
                suite_name="SuiteA",
                test_name="test1",
                test_number="100",
                columns={"Lsl": "", "Usl": ""},
            ),
        }
        new_rows = {
            ("SuiteA", "test1", "100"): TestTableRow(
                suite_name="SuiteA",
                test_name="test1",
                test_number="100",
                columns={"Lsl": "", "Usl": ""},
            ),
        }
        result = diff_testtable_suites("SuiteA", old_rows, new_rows)
        assert result is None

    def test_test_number_change_ignored(self) -> None:
        old_rows = {
            ("SuiteA", "test1", "100"): TestTableRow(
                suite_name="SuiteA",
                test_name="test1",
                test_number="100",
                columns={
                    "Suite name": "SuiteA",
                    "Test name": "test1",
                    "Test number": "100",
                    "Lsl": "10",
                },
            ),
        }
        new_rows = {
            ("SuiteA", "test1", "200"): TestTableRow(
                suite_name="SuiteA",
                test_name="test1",
                test_number="200",
                columns={
                    "Suite name": "SuiteA",
                    "Test name": "test1",
                    "Test number": "200",
                    "Lsl": "10",
                },
            ),
        }
        result = diff_testtable_suites("SuiteA", old_rows, new_rows)
        assert result is None


class TestDiffTestTables:
    def test_diff_multiple_suites(self) -> None:
        old_rows_by_suite = {
            "SuiteA": {
                ("SuiteA", "test1", "100"): TestTableRow(
                    suite_name="SuiteA", test_name="test1", test_number="100", columns={"Lsl": "10"}
                ),
            },
            "SuiteB": {
                ("SuiteB", "test1", "200"): TestTableRow(
                    suite_name="SuiteB", test_name="test1", test_number="200", columns={"Lsl": "5"}
                ),
            },
        }
        new_rows_by_suite = {
            "SuiteA": {
                ("SuiteA", "test1", "100"): TestTableRow(
                    suite_name="SuiteA", test_name="test1", test_number="100", columns={"Lsl": "15"}
                ),
            },
            "SuiteB": {
                ("SuiteB", "test1", "200"): TestTableRow(
                    suite_name="SuiteB", test_name="test1", test_number="200", columns={"Lsl": "5"}
                ),
            },
        }
        result = diff_testtables(["SuiteA", "SuiteB"], old_rows_by_suite, new_rows_by_suite)
        assert len(result) == 1
        assert result[0].suite_name == "SuiteA"
        assert len(result[0].rows_changed) == 1

    def test_empty_old_rows_ignored(self) -> None:
        old_rows_by_suite = {"SuiteA": {}}
        new_rows_by_suite = {
            "SuiteA": {
                ("SuiteA", "test1", "100"): TestTableRow(
                    suite_name="SuiteA", test_name="test1", test_number="100", columns={"Lsl": "10"}
                ),
            },
        }
        result = diff_testtables(["SuiteA"], old_rows_by_suite, new_rows_by_suite)
        assert result == []

    def test_empty_new_rows_ignored(self) -> None:
        old_rows_by_suite = {
            "SuiteA": {
                ("SuiteA", "test1", "100"): TestTableRow(
                    suite_name="SuiteA", test_name="test1", test_number="100", columns={"Lsl": "10"}
                ),
            },
        }
        new_rows_by_suite = {"SuiteA": {}}
        result = diff_testtables(["SuiteA"], old_rows_by_suite, new_rows_by_suite)
        assert result == []

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
