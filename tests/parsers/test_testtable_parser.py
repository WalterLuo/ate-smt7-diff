#!/usr/bin/env python3
"""Tests for testtable_parser.py."""

import pytest
from pathlib import Path

from ate_smt7_diff.parsers.testtable_parser import TestTableLoader


class TestTestTableLoader:
    def test_parse_valid_csv(self, tmp_path: Path) -> None:
        csv_file = tmp_path / "test.csv"
        csv_file.write_text(
            '"Suite name","Test name","Test number","Lsl","Usl","Units"\n'
            '"SuiteA","test1","100","10","20","V"\n'
            '"SuiteA","test2","101","15","25","A"\n'
            '"SuiteB","test1","200","5","10","V"\n',
            encoding="utf-8",
        )
        loader = TestTableLoader(str(csv_file))
        assert "SuiteA" in loader.rows_by_suite
        assert "SuiteB" in loader.rows_by_suite
        assert len(loader.rows_by_suite["SuiteA"]) == 2
        assert len(loader.rows_by_suite["SuiteB"]) == 1

        row = loader.rows_by_suite["SuiteA"][("SuiteA", "test1", "100")]
        assert row.test_name == "test1"
        assert row.test_number == "100"
        assert row.columns["Lsl"] == "10"
        assert row.columns["Usl"] == "20"
        assert row.columns["Units"] == "V"

    def test_missing_required_columns(self, tmp_path: Path, caplog) -> None:
        csv_file = tmp_path / "test.csv"
        csv_file.write_text(
            '"Suite","Test","Num","Lsl"\n'
            '"SuiteA","test1","100","10"\n',
            encoding="utf-8",
        )
        loader = TestTableLoader(str(csv_file))
        assert loader.rows_by_suite == {}
        assert "missing required columns" in caplog.text

    def test_empty_file(self, tmp_path: Path) -> None:
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("", encoding="utf-8")
        loader = TestTableLoader(str(csv_file))
        assert loader.rows_by_suite == {}

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        csv_file = tmp_path / "nonexistent.csv"
        with pytest.raises(ValueError):
            TestTableLoader(str(csv_file))

    def test_duplicate_keys_keep_first(self, tmp_path: Path, caplog) -> None:
        csv_file = tmp_path / "test.csv"
        csv_file.write_text(
            '"Suite name","Test name","Test number","Lsl"\n'
            '"SuiteA","test1","100","10"\n'
            '"SuiteA","test1","100","20"\n',
            encoding="utf-8",
        )
        loader = TestTableLoader(str(csv_file))
        assert len(loader.rows_by_suite["SuiteA"]) == 1
        row = loader.rows_by_suite["SuiteA"][("SuiteA", "test1", "100")]
        assert row.columns["Lsl"] == "10"
        assert "Duplicate testtable row" in caplog.text

    def test_quoted_fields_with_commas(self, tmp_path: Path) -> None:
        csv_file = tmp_path / "test.csv"
        csv_file.write_text(
            '"Suite name","Test name","Test number","Test_remarks"\n'
            '"SuiteA","test1","100","some, remark"\n',
            encoding="utf-8",
        )
        loader = TestTableLoader(str(csv_file))
        row = loader.rows_by_suite["SuiteA"][("SuiteA", "test1", "100")]
        assert row.columns["Test_remarks"] == "some, remark"

    def test_repeating_limit_columns(self, tmp_path: Path) -> None:
        csv_file = tmp_path / "test.csv"
        csv_file.write_text(
            '"Suite name","Test name","Test number","Lsl","Lsl_typ","Usl_typ","Usl","Units","Lsl","Lsl_typ","Usl_typ","Usl","Units"\n'
            '"SuiteA","test1","100","10","GE","LE","20","V","5","GE","LE","15","A"\n',
            encoding="utf-8",
        )
        loader = TestTableLoader(str(csv_file))
        row = loader.rows_by_suite["SuiteA"][("SuiteA", "test1", "100")]
        # csv.DictReader keeps the last value for duplicate column names
        assert "Lsl" in row.columns
        assert row.columns["Lsl"] == "5"
        # All columns are stored including duplicates (DictReader behavior)
        lsl_keys = [k for k in row.columns.keys() if "Lsl" in k]
        assert len(lsl_keys) >= 1

    def test_whitespace_in_key_fields(self, tmp_path: Path) -> None:
        csv_file = tmp_path / "test.csv"
        csv_file.write_text(
            '"Suite name","Test name","Test number","Lsl"\n'
            '" SuiteA "," test1 "," 100 ","10"\n',
            encoding="utf-8",
        )
        loader = TestTableLoader(str(csv_file))
        # Key fields should be stripped
        row = loader.rows_by_suite["SuiteA"][("SuiteA", "test1", "100")]
        assert row.test_name == "test1"
        assert row.test_number == "100"
        assert row.columns["Lsl"] == "10"
