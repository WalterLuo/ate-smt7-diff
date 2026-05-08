#!/usr/bin/env python3
"""Tests for EQNSET block parsing and diff functionality."""

import unittest
from program_loader import (
    DpsPinConfig,
    EqnSetBlock,
    EqnSetDiff,
    LevelLoader,
    LevelSetPinConfig,
    diff_eqnset_blocks,
)


class TestParseDpsPins(unittest.TestCase):
    """Tests for LevelLoader.parse_dpspins()."""

    def test_parse_single_dpspins(self):
        lines = [
            'DPSPINS V33',
            'vout = V33',
            'ilimit = 500',
            't_ms = 5',
            'vout_frc_rng = 5',
            'iout_clamp_rng = 500',
            'offcurr = act',
            'DPSPINS DVDD09',
        ]
        loader = LevelLoader.__new__(LevelLoader)
        loader.lines = lines
        config = loader.parse_dpspins(0)
        self.assertIsNotNone(config)
        self.assertEqual(config.vout, "V33")
        self.assertEqual(config.ilimit, "500")
        self.assertEqual(config.t_ms, "5")
        self.assertEqual(config.vout_frc_rng, "5")
        self.assertEqual(config.iout_clamp_rng, "500")
        self.assertEqual(config.offcurr, "act")

    def test_parse_dpspins_with_comments(self):
        lines = [
            'DPSPINS DVDD09',
            'vout = DVDD09\t\t # [V]',
            'ilimit = 2000\t\t # [mA]',
            't_ms = 5\t\t\t # [ms]',
            'vout_frc_rng = 2\t # [v]',
            'iout_clamp_rng = 2000 # [mA]',
            'offcurr = act',
            'LEVELSET 1 "MDIO"',
        ]
        loader = LevelLoader.__new__(LevelLoader)
        loader.lines = lines
        config = loader.parse_dpspins(0)
        self.assertEqual(config.vout, "DVDD09")
        self.assertEqual(config.ilimit, "2000")
        self.assertEqual(config.t_ms, "5")

    def test_parse_dpspins_stops_at_levelset(self):
        lines = [
            'DPSPINS V33',
            'vout = V33',
            'LEVELSET 1 "TEST"',
        ]
        loader = LevelLoader.__new__(LevelLoader)
        loader.lines = lines
        config = loader.parse_dpspins(0)
        self.assertEqual(config.vout, "V33")
        self.assertEqual(config.ilimit, "")

    def test_parse_dpspins_stops_at_eqnset(self):
        lines = [
            'DPSPINS V33',
            'vout = V33',
            'EQNSET 8 "NEXT"',
        ]
        loader = LevelLoader.__new__(LevelLoader)
        loader.lines = lines
        config = loader.parse_dpspins(0)
        self.assertEqual(config.vout, "V33")

    def test_parse_dpspins_stops_at_at(self):
        lines = [
            'DPSPINS V33',
            'vout = V33',
            '@',
        ]
        loader = LevelLoader.__new__(LevelLoader)
        loader.lines = lines
        config = loader.parse_dpspins(0)
        self.assertEqual(config.vout, "V33")

    def test_parse_dpspins_unknown_fields(self):
        lines = [
            'DPSPINS V33',
            'vout = V33',
            'ilimit = 500',
            'slew = fast',
            'edge = rise',
            'DPSPINS DVDD09',
        ]
        loader = LevelLoader.__new__(LevelLoader)
        loader.lines = lines
        config = loader.parse_dpspins(0)
        self.assertEqual(config.vout, "V33")
        self.assertEqual(config.ilimit, "500")
        self.assertEqual(config.extra.get("slew"), "fast")
        self.assertEqual(config.extra.get("edge"), "rise")
        self.assertIn("slew", config.all_fields())
        self.assertIn("edge", config.all_fields())


class TestParseLevelSet(unittest.TestCase):
    """Tests for LevelLoader.parse_levelset()."""

    def test_parse_single_pins_group(self):
        lines = [
            'LEVELSET 1 "MDIO"',
            'PINS NO_MDIO',
            'vih = VIH',
            'vil = VIL',
            'voh = VOH',
            'vol = VOL',
            'LEVELSET 2 "NEXT"',
        ]
        loader = LevelLoader.__new__(LevelLoader)
        loader.lines = lines
        result = loader.parse_levelset(0)
        self.assertIn("NO_MDIO", result)
        config = result["NO_MDIO"]
        self.assertEqual(config.vih, "VIH")
        self.assertEqual(config.vil, "VIL")
        self.assertEqual(config.voh, "VOH")
        self.assertEqual(config.vol, "VOL")

    def test_parse_multiple_pins_groups(self):
        lines = [
            'LEVELSET 1 "MDIO"',
            'PINS NO_MDIO',
            'vih = VIH',
            'vil = VIL',
            'voh = VOH',
            'vol = VOL',
            '',
            'PINS GPIOA_1 GPIOA_2 # MDC MDIO',
            'vih = VIH',
            'vil = VIL',
            'voh = VOH',
            'vol = VOL',
            'EQNSET 8 "SCAN_FUNC"',
        ]
        loader = LevelLoader.__new__(LevelLoader)
        loader.lines = lines
        result = loader.parse_levelset(0)
        self.assertEqual(len(result), 2)
        self.assertIn("NO_MDIO", result)
        self.assertIn("GPIOA_1 GPIOA_2", result)
        self.assertEqual(result["GPIOA_1 GPIOA_2"].vih, "VIH")

    def test_parse_levelset_stops_at_eqnset(self):
        lines = [
            'LEVELSET 1 "MDIO"',
            'PINS NO_MDIO',
            'vih = VIH',
            'EQNSET 8 "NEXT"',
        ]
        loader = LevelLoader.__new__(LevelLoader)
        loader.lines = lines
        result = loader.parse_levelset(0)
        self.assertEqual(len(result), 1)

    def test_parse_levelset_stops_at_at(self):
        lines = [
            'LEVELSET 1 "MDIO"',
            'PINS NO_MDIO',
            'vih = VIH',
            '@',
        ]
        loader = LevelLoader.__new__(LevelLoader)
        loader.lines = lines
        result = loader.parse_levelset(0)
        self.assertEqual(len(result), 1)

    def test_parse_levelset_empty(self):
        lines = [
            'LEVELSET 1 "MDIO"',
            'EQNSET 8 "NEXT"',
        ]
        loader = LevelLoader.__new__(LevelLoader)
        loader.lines = lines
        result = loader.parse_levelset(0)
        self.assertEqual(len(result), 0)

    def test_parse_levelset_unknown_fields(self):
        lines = [
            'LEVELSET 1 "MDIO"',
            'PINS NO_MDIO',
            'vih = VIH',
            'vil = VIL',
            'voh = VOH',
            'vol = VOL',
            'slew = fast',
            'edge = rise',
            'EQNSET 8 "NEXT"',
        ]
        loader = LevelLoader.__new__(LevelLoader)
        loader.lines = lines
        result = loader.parse_levelset(0)
        config = result["NO_MDIO"]
        self.assertEqual(config.vih, "VIH")
        self.assertEqual(config.extra.get("slew"), "fast")
        self.assertEqual(config.extra.get("edge"), "rise")


class TestParseEqnSetBlock(unittest.TestCase):
    """Tests for LevelLoader.parse_eqnset_block()."""

    def test_parse_full_eqnset(self):
        lines = [
            'EQNSET 7 "MDIO"',
            '',
            'SPECS ',
            'V33\t\t[V]',
            'DVDD09\t\t[V]',
            '',
            'DPSPINS V33',
            'vout = V33',
            'ilimit = 500',
            'offcurr = act',
            '',
            'DPSPINS DVDD09',
            'vout = DVDD09',
            'ilimit = 2000',
            'offcurr = act',
            '',
            'LEVELSET 1 "MDIO"',
            'PINS NO_MDIO',
            'vih = VIH',
            'vil = VIL',
            'voh = VOH',
            'vol = VOL',
            '',
            'PINS GPIOA_1 GPIOA_2',
            'vih = VIH',
            'vil = VIL',
            'voh = VOH',
            'vol = VOL',
            'EQNSET 8 "SCAN_FUNC"',
        ]
        loader = LevelLoader.__new__(LevelLoader)
        loader.lines = lines
        block = loader.parse_eqnset_block(0)
        self.assertIsNotNone(block)
        self.assertEqual(block.eqnset_index, 7)
        self.assertEqual(block.eqnset_name, "MDIO")
        self.assertEqual(len(block.specs), 2)
        self.assertEqual(len(block.dpspins), 2)
        self.assertEqual(len(block.levelsets), 1)
        self.assertIn(1, block.levelsets)
        self.assertEqual(len(block.levelsets[1]), 2)
        self.assertEqual(block.dpspins["V33"].ilimit, "500")
        self.assertEqual(block.dpspins["DVDD09"].ilimit, "2000")

    def test_parse_eqnset_no_dpspins_no_levelset(self):
        lines = [
            'EQNSET 1 "TEST"',
            'SPECS ',
            'V33\t\t[V]',
            'EQNSET 2 "NEXT"',
        ]
        loader = LevelLoader.__new__(LevelLoader)
        loader.lines = lines
        block = loader.parse_eqnset_block(0)
        self.assertIsNotNone(block)
        self.assertEqual(len(block.dpspins), 0)
        self.assertEqual(len(block.levelsets), 0)

    def test_parse_eqnset_stops_at_at(self):
        lines = [
            'EQNSET 1 "TEST"',
            'SPECS ',
            'V33\t\t[V]',
            '@',
        ]
        loader = LevelLoader.__new__(LevelLoader)
        loader.lines = lines
        block = loader.parse_eqnset_block(0)
        self.assertEqual(block.eqnset_index, 1)


class TestDiffEqnSetBlocks(unittest.TestCase):
    """Tests for diff_eqnset_blocks()."""

    def test_both_none(self):
        result = diff_eqnset_blocks("SUITE1", None, None)
        self.assertIsNone(result)

    def test_old_none(self):
        block = EqnSetBlock(eqnset_index=7, eqnset_name="MDIO", dpspins={"V33": DpsPinConfig(vout="3.3")})
        result = diff_eqnset_blocks("SUITE1", None, block)
        self.assertIsNotNone(result)
        self.assertTrue(result.has_changes)
        self.assertEqual(len(result.dpspins_added), 1)

    def test_new_none(self):
        block = EqnSetBlock(eqnset_index=7, eqnset_name="MDIO", dpspins={"V33": DpsPinConfig(vout="3.3")})
        result = diff_eqnset_blocks("SUITE1", block, None)
        self.assertIsNotNone(result)
        self.assertTrue(result.has_changes)
        self.assertEqual(len(result.dpspins_removed), 1)

    def test_no_changes(self):
        block = EqnSetBlock(
            eqnset_index=7, eqnset_name="MDIO",
            dpspins={"V33": DpsPinConfig(vout="3.3", ilimit="500")},
        )
        result = diff_eqnset_blocks("SUITE1", block, block)
        self.assertFalse(result.has_changes)

    def test_dpspins_added(self):
        old = EqnSetBlock(eqnset_index=7, eqnset_name="MDIO", dpspins={"V33": DpsPinConfig(vout="3.3")})
        new = EqnSetBlock(
            eqnset_index=7, eqnset_name="MDIO",
            dpspins={"V33": DpsPinConfig(vout="3.3"), "DVDD09": DpsPinConfig(vout="0.9")},
        )
        result = diff_eqnset_blocks("SUITE1", old, new)
        self.assertTrue(result.has_changes)
        self.assertIn("DVDD09", result.dpspins_added)

    def test_dpspins_removed(self):
        old = EqnSetBlock(
            eqnset_index=7, eqnset_name="MDIO",
            dpspins={"V33": DpsPinConfig(vout="3.3"), "DVDD09": DpsPinConfig(vout="0.9")},
        )
        new = EqnSetBlock(eqnset_index=7, eqnset_name="MDIO", dpspins={"V33": DpsPinConfig(vout="3.3")})
        result = diff_eqnset_blocks("SUITE1", old, new)
        self.assertIn("DVDD09", result.dpspins_removed)

    def test_dpspins_changed(self):
        old = EqnSetBlock(eqnset_index=7, eqnset_name="MDIO", dpspins={"V33": DpsPinConfig(vout="3.3", ilimit="500")})
        new = EqnSetBlock(eqnset_index=7, eqnset_name="MDIO", dpspins={"V33": DpsPinConfig(vout="3.3", ilimit="600")})
        result = diff_eqnset_blocks("SUITE1", old, new)
        self.assertIn("V33", result.dpspins_changed)
        old_cfg, new_cfg = result.dpspins_changed["V33"]
        self.assertEqual(old_cfg.ilimit, "500")
        self.assertEqual(new_cfg.ilimit, "600")

    def test_levelset_added(self):
        old = EqnSetBlock(eqnset_index=7, eqnset_name="MDIO", levelsets={})
        new = EqnSetBlock(
            eqnset_index=7, eqnset_name="MDIO",
            levelsets={1: {"NO_MDIO": LevelSetPinConfig(vih="VIH")}},
        )
        result = diff_eqnset_blocks("SUITE1", old, new)
        self.assertIn(1, result.levelsets_added)

    def test_levelset_removed(self):
        old = EqnSetBlock(
            eqnset_index=7, eqnset_name="MDIO",
            levelsets={1: {"NO_MDIO": LevelSetPinConfig(vih="VIH")}},
        )
        new = EqnSetBlock(eqnset_index=7, eqnset_name="MDIO", levelsets={})
        result = diff_eqnset_blocks("SUITE1", old, new)
        self.assertIn(1, result.levelsets_removed)

    def test_levelset_pins_changed(self):
        old = EqnSetBlock(
            eqnset_index=7, eqnset_name="MDIO",
            levelsets={1: {"NO_MDIO": LevelSetPinConfig(vih="3.3", vil="0")}},
        )
        new = EqnSetBlock(
            eqnset_index=7, eqnset_name="MDIO",
            levelsets={1: {"NO_MDIO": LevelSetPinConfig(vih="2.5", vil="0")}},
        )
        result = diff_eqnset_blocks("SUITE1", old, new)
        self.assertIn(1, result.levelsets_changed)
        self.assertIn("NO_MDIO", result.levelsets_changed[1])
        old_cfg, new_cfg = result.levelsets_changed[1]["NO_MDIO"]
        self.assertEqual(old_cfg.vih, "3.3")
        self.assertEqual(new_cfg.vih, "2.5")

    def test_levelset_pins_added_removed(self):
        old = EqnSetBlock(
            eqnset_index=7, eqnset_name="MDIO",
            levelsets={1: {"NO_MDIO": LevelSetPinConfig(vih="3.3")}},
        )
        new = EqnSetBlock(
            eqnset_index=7, eqnset_name="MDIO",
            levelsets={1: {"GPIOA_1": LevelSetPinConfig(vih="2.5")}},
        )
        result = diff_eqnset_blocks("SUITE1", old, new)
        self.assertIn(1, result.levelsets_changed)
        self.assertIn("GPIOA_1", result.levelsets_changed[1])
        self.assertIn("NO_MDIO", result.levelsets_changed[1])

    def test_dpspins_extra_field_changed(self):
        old = EqnSetBlock(
            eqnset_index=7, eqnset_name="MDIO",
            dpspins={"V33": DpsPinConfig(vout="3.3", extra={"slew": "fast"})},
        )
        new = EqnSetBlock(
            eqnset_index=7, eqnset_name="MDIO",
            dpspins={"V33": DpsPinConfig(vout="3.3", extra={"slew": "slow"})},
        )
        result = diff_eqnset_blocks("SUITE1", old, new)
        self.assertIn("V33", result.dpspins_changed)
        old_cfg, new_cfg = result.dpspins_changed["V33"]
        self.assertEqual(old_cfg.extra["slew"], "fast")
        self.assertEqual(new_cfg.extra["slew"], "slow")

    def test_levelset_extra_field_changed(self):
        old = EqnSetBlock(
            eqnset_index=7, eqnset_name="MDIO",
            levelsets={1: {"NO_MDIO": LevelSetPinConfig(vih="3.3", extra={"slew": "fast"})}},
        )
        new = EqnSetBlock(
            eqnset_index=7, eqnset_name="MDIO",
            levelsets={1: {"NO_MDIO": LevelSetPinConfig(vih="3.3", extra={"slew": "slow"})}},
        )
        result = diff_eqnset_blocks("SUITE1", old, new)
        self.assertIn(1, result.levelsets_changed)
        self.assertIn("NO_MDIO", result.levelsets_changed[1])
        old_cfg, new_cfg = result.levelsets_changed[1]["NO_MDIO"]
        self.assertEqual(old_cfg.extra["slew"], "fast")
        self.assertEqual(new_cfg.extra["slew"], "slow")


if __name__ == "__main__":
    unittest.main()
