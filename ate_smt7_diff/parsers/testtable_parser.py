#!/usr/bin/env python3
"""
Testtable CSV parser.
Loads testtable files and groups rows by suite name.
"""

import csv
import logging
from pathlib import Path

from ate_smt7_diff.models import TestTableRow


class TestTableLoader:
    """Load and parse a testtable CSV file.

    Rows are indexed by (suite_name, test_name, test_number) within
    each suite group.
    """

    REQUIRED_COLUMNS = {"Suite name", "Test name", "Test number"}

    def __init__(self, path: str) -> None:
        self.path = path
        self.rows_by_suite: dict[str, dict[tuple[str, str, str], TestTableRow]] = {}
        self._load()

    def _load(self) -> None:
        try:
            text = Path(self.path).read_text(encoding="utf-8")
        except UnicodeDecodeError:
            try:
                text = Path(self.path).read_text(encoding="latin-1")
            except UnicodeDecodeError as e:
                raise ValueError(f"Failed to decode testtable {self.path}: {e}") from e
        except (FileNotFoundError, PermissionError) as e:
            raise ValueError(f"Failed to read testtable {self.path}: {e}") from e

        try:
            reader = csv.DictReader(text.splitlines())
        except csv.Error as e:
            raise ValueError(f"Failed to parse CSV from {self.path}: {e}") from e

        if not reader.fieldnames:
            return

        missing = self.REQUIRED_COLUMNS - set(reader.fieldnames)
        if missing:
            logging.warning(
                "Testtable missing required columns %s in %s",
                missing,
                self.path,
            )
            return

        for raw_row in reader:
            suite = raw_row.get("Suite name", "").strip()
            test = raw_row.get("Test name", "").strip()
            num = raw_row.get("Test number", "").strip()
            if not suite or not test or not num:
                continue

            key = (suite, test, num)
            columns = {k: v.strip() for k, v in raw_row.items() if v is not None}
            row = TestTableRow(
                suite_name=suite,
                test_name=test,
                test_number=num,
                columns=columns,
            )
            suite_rows = self.rows_by_suite.setdefault(suite, {})
            if key in suite_rows:
                logging.warning(
                    "Duplicate testtable row %s in %s, keeping first",
                    key,
                    self.path,
                )
                continue
            suite_rows[key] = row
