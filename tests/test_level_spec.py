#!/usr/bin/env python3
"""Tests for level spec parsing and diff functionality."""

import unittest
from ate_smt7_diff.models import LevelSpec, LevelSpecDiff
from ate_smt7_diff.parsers.level_parser import LevelLoader
from ate_smt7_diff.diff.level_diff import diff_level_specs


class TestParseSpecs(unittest.TestCase):
    """Tests for LevelLoader.parse_specs()."""

    def test_parse_basic_specs(self):
        lines = [
            'SPECSET 1 "TEST"',
            '',
            '# SPECNAME       *****ACTUAL***** *****MINIMUM**** *****MAXIMUM**** UNITS COMMENT',
            'V33              0                                                  [  V] ',
            'VOH              -0.2                                               [  V] ',
            'IOH              0.2                                                [ mA] ',
            '',
            'SPECSET 2 "NEXT"',
        ]
        loader = LevelLoader.__new__(LevelLoader)
        loader.lines = lines
        specs = loader.parse_specs(0)
        self.assertEqual(len(specs), 3)
        self.assertEqual(specs["V33"].actual, "0")
        self.assertEqual(specs["V33"].units, "V")
        self.assertEqual(specs["VOH"].actual, "-0.2")
        self.assertEqual(specs["IOH"].actual, "0.2")
        self.assertEqual(specs["IOH"].units, "mA")

    def test_parse_specs_with_min_max(self):
        lines = [
            'SPECSET 1 "TEST"',
            '# SPECNAME       *****ACTUAL***** *****MINIMUM**** *****MAXIMUM**** UNITS COMMENT',
            'VT               -1.5             0                0                [  V] ',
            'DVDD09           0.9              0                0                [  V] ',
        ]
        loader = LevelLoader.__new__(LevelLoader)
        loader.lines = lines
        specs = loader.parse_specs(0)
        self.assertEqual(specs["VT"].actual, "-1.5")
        self.assertEqual(specs["VT"].min, "0")
        self.assertEqual(specs["VT"].max, "0")
        self.assertEqual(specs["DVDD09"].actual, "0.9")
        self.assertEqual(specs["DVDD09"].min, "0")
        self.assertEqual(specs["DVDD09"].max, "0")

    def test_parse_specs_stops_at_eqnset(self):
        lines = [
            'SPECSET 1 "TEST"',
            '# SPECNAME       *****ACTUAL***** *****MINIMUM**** *****MAXIMUM**** UNITS COMMENT',
            'V33              0                                                  [  V] ',
            'EQNSET 2 "NEXT"',
        ]
        loader = LevelLoader.__new__(LevelLoader)
        loader.lines = lines
        specs = loader.parse_specs(0)
        self.assertEqual(len(specs), 1)
        self.assertIn("V33", specs)

    def test_parse_specs_stops_at_at(self):
        lines = [
            'SPECSET 1 "TEST"',
            '# SPECNAME       *****ACTUAL***** *****MINIMUM**** *****MAXIMUM**** UNITS COMMENT',
            'V33              0                                                  [  V] ',
            '@',
        ]
        loader = LevelLoader.__new__(LevelLoader)
        loader.lines = lines
        specs = loader.parse_specs(0)
        self.assertEqual(len(specs), 1)

    def test_parse_specs_empty_block(self):
        lines = [
            'SPECSET 1 "TEST"',
            '',
            'SPECSET 2 "NEXT"',
        ]
        loader = LevelLoader.__new__(LevelLoader)
        loader.lines = lines
        specs = loader.parse_specs(0)
        self.assertEqual(len(specs), 0)


class TestDiffLevelSpecs(unittest.TestCase):
    """Tests for diff_level_specs()."""

    def test_both_none(self):
        result = diff_level_specs("SUITE1", None, None)
        self.assertIsNone(result)

    def test_old_none(self):
        new = {"V33": LevelSpec(actual="1.0", units="V")}
        result = diff_level_specs("SUITE1", None, new)
        self.assertIsNotNone(result)
        self.assertTrue(result.has_changes)
        self.assertEqual(len(result.added), 1)
        self.assertEqual(len(result.removed), 0)
        self.assertEqual(len(result.changed), 0)

    def test_new_none(self):
        old = {"V33": LevelSpec(actual="1.0", units="V")}
        result = diff_level_specs("SUITE1", old, None)
        self.assertIsNotNone(result)
        self.assertTrue(result.has_changes)
        self.assertEqual(len(result.added), 0)
        self.assertEqual(len(result.removed), 1)
        self.assertEqual(len(result.changed), 0)

    def test_no_changes(self):
        old = {"V33": LevelSpec(actual="1.0", units="V")}
        new = {"V33": LevelSpec(actual="1.0", units="V")}
        result = diff_level_specs("SUITE1", old, new)
        self.assertIsNotNone(result)
        self.assertFalse(result.has_changes)

    def test_added_spec(self):
        old = {"V33": LevelSpec(actual="1.0", units="V")}
        new = {
            "V33": LevelSpec(actual="1.0", units="V"),
            "VDD": LevelSpec(actual="3.3", units="V"),
        }
        result = diff_level_specs("SUITE1", old, new)
        self.assertTrue(result.has_changes)
        self.assertIn("VDD", result.added)
        self.assertEqual(len(result.removed), 0)
        self.assertEqual(len(result.changed), 0)

    def test_removed_spec(self):
        old = {
            "V33": LevelSpec(actual="1.0", units="V"),
            "VDD": LevelSpec(actual="3.3", units="V"),
        }
        new = {"V33": LevelSpec(actual="1.0", units="V")}
        result = diff_level_specs("SUITE1", old, new)
        self.assertTrue(result.has_changes)
        self.assertIn("VDD", result.removed)
        self.assertEqual(len(result.added), 0)
        self.assertEqual(len(result.changed), 0)

    def test_changed_actual(self):
        old = {"V33": LevelSpec(actual="1.0", units="V")}
        new = {"V33": LevelSpec(actual="1.2", units="V")}
        result = diff_level_specs("SUITE1", old, new)
        self.assertTrue(result.has_changes)
        self.assertEqual(len(result.added), 0)
        self.assertEqual(len(result.removed), 0)
        self.assertIn("V33", result.changed)
        old_spec, new_spec = result.changed["V33"]
        self.assertEqual(old_spec.actual, "1.0")
        self.assertEqual(new_spec.actual, "1.2")

    def test_changed_units(self):
        old = {"IOH": LevelSpec(actual="0.2", units="mA")}
        new = {"IOH": LevelSpec(actual="0.2", units="uA")}
        result = diff_level_specs("SUITE1", old, new)
        self.assertTrue(result.has_changes)
        self.assertIn("IOH", result.changed)

    def test_multiple_changes(self):
        old = {
            "V33": LevelSpec(actual="1.0", units="V"),
            "VDD": LevelSpec(actual="3.3", units="V"),
        }
        new = {
            "V33": LevelSpec(actual="1.2", units="V"),
            "VIO": LevelSpec(actual="1.8", units="V"),
        }
        result = diff_level_specs("SUITE1", old, new)
        self.assertTrue(result.has_changes)
        self.assertIn("VIO", result.added)
        self.assertIn("VDD", result.removed)
        self.assertIn("V33", result.changed)


if __name__ == "__main__":
    unittest.main()
