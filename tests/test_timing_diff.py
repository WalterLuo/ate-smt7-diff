#!/usr/bin/env python3
"""Tests for timing diff functionality."""

import unittest
from ate_smt7_diff.models import (
    TimingEqnSetBlock,
    TimingEqnSetDiff,
    TimingPinConfig,
    TimingSetConfig,
    TimingSpec,
    TimingSpecDiff,
)
from ate_smt7_diff.diff.timing_diff import (
    diff_timing_specs,
    diff_timing_eqnset_blocks,
    diff_timing_eqnset_blocks_full,
)


class TestDiffTimingSpecs(unittest.TestCase):
    """Tests for diff_timing_specs()."""

    def test_both_none(self):
        result = diff_timing_specs("SUITE1", "port", "SPEC1", None, None)
        self.assertIsNone(result)

    def test_old_none(self):
        new = {"TCLK": TimingSpec(value="10.0", units="ns")}
        result = diff_timing_specs("SUITE1", "port", "SPEC1", None, new)
        self.assertIsNotNone(result)
        self.assertTrue(result.has_changes)
        self.assertEqual(len(result.added), 1)
        self.assertEqual(len(result.removed), 0)
        self.assertEqual(len(result.changed), 0)

    def test_new_none(self):
        old = {"TCLK": TimingSpec(value="10.0", units="ns")}
        result = diff_timing_specs("SUITE1", "port", "SPEC1", old, None)
        self.assertIsNotNone(result)
        self.assertTrue(result.has_changes)
        self.assertEqual(len(result.added), 0)
        self.assertEqual(len(result.removed), 1)
        self.assertEqual(len(result.changed), 0)

    def test_no_changes(self):
        old = {"TCLK": TimingSpec(value="10.0", units="ns")}
        new = {"TCLK": TimingSpec(value="10.0", units="ns")}
        result = diff_timing_specs("SUITE1", "port", "SPEC1", old, new)
        self.assertIsNone(result)

    def test_added_spec(self):
        old = {"TCLK": TimingSpec(value="10.0", units="ns")}
        new = {
            "TCLK": TimingSpec(value="10.0", units="ns"),
            "TPER": TimingSpec(value="20.0", units="ns"),
        }
        result = diff_timing_specs("SUITE1", "port", "SPEC1", old, new)
        self.assertTrue(result.has_changes)
        self.assertIn("TPER", result.added)
        self.assertEqual(len(result.removed), 0)
        self.assertEqual(len(result.changed), 0)

    def test_removed_spec(self):
        old = {
            "TCLK": TimingSpec(value="10.0", units="ns"),
            "TPER": TimingSpec(value="20.0", units="ns"),
        }
        new = {"TCLK": TimingSpec(value="10.0", units="ns")}
        result = diff_timing_specs("SUITE1", "port", "SPEC1", old, new)
        self.assertTrue(result.has_changes)
        self.assertIn("TPER", result.removed)
        self.assertEqual(len(result.added), 0)
        self.assertEqual(len(result.changed), 0)

    def test_changed_value(self):
        old = {"TCLK": TimingSpec(value="10.0", units="ns")}
        new = {"TCLK": TimingSpec(value="12.0", units="ns")}
        result = diff_timing_specs("SUITE1", "port", "SPEC1", old, new)
        self.assertTrue(result.has_changes)
        self.assertEqual(len(result.added), 0)
        self.assertEqual(len(result.removed), 0)
        self.assertIn("TCLK", result.changed)
        old_spec, new_spec = result.changed["TCLK"]
        self.assertEqual(old_spec.value, "10.0")
        self.assertEqual(new_spec.value, "12.0")

    def test_changed_units(self):
        old = {"TCLK": TimingSpec(value="10.0", units="ns")}
        new = {"TCLK": TimingSpec(value="10.0", units="us")}
        result = diff_timing_specs("SUITE1", "port", "SPEC1", old, new)
        self.assertTrue(result.has_changes)
        self.assertIn("TCLK", result.changed)

    def test_multiple_changes(self):
        old = {
            "TCLK": TimingSpec(value="10.0", units="ns"),
            "TPER": TimingSpec(value="20.0", units="ns"),
        }
        new = {
            "TCLK": TimingSpec(value="12.0", units="ns"),
            "TSETUP": TimingSpec(value="1.0", units="ns"),
        }
        result = diff_timing_specs("SUITE1", "port", "SPEC1", old, new)
        self.assertTrue(result.has_changes)
        self.assertIn("TSETUP", result.added)
        self.assertIn("TPER", result.removed)
        self.assertIn("TCLK", result.changed)


class TestDiffTimingEqnsetBlocks(unittest.TestCase):
    """Tests for diff_timing_eqnset_blocks()."""

    def test_both_none(self):
        result = diff_timing_eqnset_blocks("SUITE1", None, None)
        self.assertIsNone(result)

    def test_old_none(self):
        new = TimingEqnSetBlock(
            eqnset_index=1,
            eqnset_name="TIM1",
            specset_index=1,
            specset_name="SPS1",
            specs={"TCLK": TimingSpec(value="10.0", units="ns")},
        )
        result = diff_timing_eqnset_blocks("SUITE1", None, new)
        self.assertIsNotNone(result)
        self.assertTrue(result.has_changes)
        self.assertEqual(result.spec_type, "regular")
        self.assertEqual(len(result.added), 1)

    def test_new_none(self):
        old = TimingEqnSetBlock(
            eqnset_index=1,
            eqnset_name="TIM1",
            specset_index=1,
            specset_name="SPS1",
            specs={"TCLK": TimingSpec(value="10.0", units="ns")},
        )
        result = diff_timing_eqnset_blocks("SUITE1", old, None)
        self.assertIsNotNone(result)
        self.assertTrue(result.has_changes)
        self.assertEqual(len(result.removed), 1)

    def test_no_changes(self):
        block = TimingEqnSetBlock(
            eqnset_index=1,
            eqnset_name="TIM1",
            specset_index=1,
            specset_name="SPS1",
            specs={"TCLK": TimingSpec(value="10.0", units="ns")},
        )
        result = diff_timing_eqnset_blocks("SUITE1", block, block)
        self.assertIsNone(result)

    def test_changed_specs(self):
        old = TimingEqnSetBlock(
            eqnset_index=1,
            eqnset_name="TIM1",
            specset_index=1,
            specset_name="SPS1",
            specs={"TCLK": TimingSpec(value="10.0", units="ns")},
        )
        new = TimingEqnSetBlock(
            eqnset_index=1,
            eqnset_name="TIM1",
            specset_index=1,
            specset_name="SPS1",
            specs={"TCLK": TimingSpec(value="12.0", units="ns")},
        )
        result = diff_timing_eqnset_blocks("SUITE1", old, new)
        self.assertIsNotNone(result)
        self.assertTrue(result.has_changes)
        self.assertIn("TCLK", result.changed)


class TestDiffTimingEqnsetBlocksFull(unittest.TestCase):
    """Tests for diff_timing_eqnset_blocks_full()."""

    def test_both_none(self):
        result = diff_timing_eqnset_blocks_full("SUITE1", None, None)
        self.assertIsNone(result)

    def test_old_none(self):
        new = TimingEqnSetBlock(
            eqnset_index=1,
            eqnset_name="TIM1",
            specset_index=1,
            specset_name="SPS1",
            specs={"TCLK": TimingSpec(value="10.0", units="ns")},
            pins_groups={"P1": TimingPinConfig(d1="0", r1="1")},
            timingsets={1: TimingSetConfig(index=1, name="TS1", period="per")},
        )
        result = diff_timing_eqnset_blocks_full("SUITE1", None, new)
        self.assertIsNotNone(result)
        self.assertTrue(result.has_changes)
        self.assertEqual(len(result.specs_added), 1)
        self.assertEqual(len(result.pins_added), 1)
        self.assertEqual(len(result.timingsets_added), 1)

    def test_new_none(self):
        old = TimingEqnSetBlock(
            eqnset_index=1,
            eqnset_name="TIM1",
            specset_index=1,
            specset_name="SPS1",
            specs={"TCLK": TimingSpec(value="10.0", units="ns")},
            pins_groups={"P1": TimingPinConfig(d1="0", r1="1")},
            timingsets={1: TimingSetConfig(index=1, name="TS1", period="per")},
        )
        result = diff_timing_eqnset_blocks_full("SUITE1", old, None)
        self.assertIsNotNone(result)
        self.assertTrue(result.has_changes)
        self.assertEqual(len(result.specs_removed), 1)
        self.assertEqual(len(result.pins_removed), 1)
        self.assertEqual(len(result.timingsets_removed), 1)

    def test_no_changes(self):
        block = TimingEqnSetBlock(
            eqnset_index=1,
            eqnset_name="TIM1",
            specset_index=1,
            specset_name="SPS1",
            specs={"TCLK": TimingSpec(value="10.0", units="ns")},
            pins_groups={"P1": TimingPinConfig(d1="0", r1="1")},
            timingsets={1: TimingSetConfig(index=1, name="TS1", period="per")},
        )
        result = diff_timing_eqnset_blocks_full("SUITE1", block, block)
        self.assertIsNone(result)

    def test_specs_changed(self):
        old = TimingEqnSetBlock(
            eqnset_index=1,
            eqnset_name="TIM1",
            specset_index=1,
            specset_name="SPS1",
            specs={"TCLK": TimingSpec(value="10.0", units="ns")},
        )
        new = TimingEqnSetBlock(
            eqnset_index=1,
            eqnset_name="TIM1",
            specset_index=1,
            specset_name="SPS1",
            specs={"TCLK": TimingSpec(value="12.0", units="ns")},
        )
        result = diff_timing_eqnset_blocks_full("SUITE1", old, new)
        self.assertIsNotNone(result)
        self.assertTrue(result.has_changes)
        self.assertIn("TCLK", result.specs_changed)

    def test_pins_added_removed(self):
        old = TimingEqnSetBlock(
            eqnset_index=1,
            eqnset_name="TIM1",
            specset_index=1,
            specset_name="SPS1",
            specs={},
            pins_groups={"P1": TimingPinConfig(d1="0")},
        )
        new = TimingEqnSetBlock(
            eqnset_index=1,
            eqnset_name="TIM1",
            specset_index=1,
            specset_name="SPS1",
            specs={},
            pins_groups={"P2": TimingPinConfig(d1="1")},
        )
        result = diff_timing_eqnset_blocks_full("SUITE1", old, new)
        self.assertIsNotNone(result)
        self.assertTrue(result.has_changes)
        self.assertIn("P2", result.pins_added)
        self.assertIn("P1", result.pins_removed)

    def test_pins_changed(self):
        old = TimingEqnSetBlock(
            eqnset_index=1,
            eqnset_name="TIM1",
            specset_index=1,
            specset_name="SPS1",
            specs={},
            pins_groups={"P1": TimingPinConfig(d1="0", r1="1")},
        )
        new = TimingEqnSetBlock(
            eqnset_index=1,
            eqnset_name="TIM1",
            specset_index=1,
            specset_name="SPS1",
            specs={},
            pins_groups={"P1": TimingPinConfig(d1="0", r1="2")},
        )
        result = diff_timing_eqnset_blocks_full("SUITE1", old, new)
        self.assertIsNotNone(result)
        self.assertTrue(result.has_changes)
        self.assertIn("P1", result.pins_changed)
        old_pin, new_pin = result.pins_changed["P1"]
        self.assertEqual(old_pin.r1, "1")
        self.assertEqual(new_pin.r1, "2")

    def test_timingset_changed(self):
        old = TimingEqnSetBlock(
            eqnset_index=1,
            eqnset_name="TIM1",
            specset_index=1,
            specset_name="SPS1",
            specs={},
            timingsets={1: TimingSetConfig(index=1, name="TS1", period="per")},
        )
        new = TimingEqnSetBlock(
            eqnset_index=1,
            eqnset_name="TIM1",
            specset_index=1,
            specset_name="SPS1",
            specs={},
            timingsets={1: TimingSetConfig(index=1, name="TS1", period="per2")},
        )
        result = diff_timing_eqnset_blocks_full("SUITE1", old, new)
        self.assertIsNotNone(result)
        self.assertTrue(result.has_changes)
        self.assertIn(1, result.timingsets_changed)


if __name__ == "__main__":
    unittest.main()
