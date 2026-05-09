#!/usr/bin/env python3
"""Tests for timing parser functionality."""

import unittest
from ate_smt7_diff.models import TimingPinConfig, TimingSetConfig, TimingSpec
from ate_smt7_diff.parsers.timing_parser import TimingLoader


class TestTimingLoaderIndexing(unittest.TestCase):
    """Tests for TimingLoader indexing capabilities."""

    def _make_loader(self, lines):
        loader = TimingLoader.__new__(TimingLoader)
        loader.path = "/dummy/timing.tim"
        loader.lines = lines
        loader.spec_sets = {}
        loader.wavetbls = {}
        loader.specifications = {}
        loader.eqsp_tim_eqnsets = {}
        loader.eqsp_tim_specsets = {}
        loader._load()
        return loader

    def test_index_spst(self):
        lines = [
            'SPST TIM,,"SPEC1",0',
            'WAVETBL "W1"',
        ]
        loader = self._make_loader(lines)
        self.assertIn("SPEC1", loader.spec_sets)

    def test_index_wavetbl(self):
        lines = [
            'WAVETBL "W1"',
        ]
        loader = self._make_loader(lines)
        self.assertIn("W1", loader.wavetbls)

    def test_index_specification(self):
        lines = [
            'SPECIFICATION "XSDS_SCAN"',
        ]
        loader = self._make_loader(lines)
        self.assertIn("XSDS_SCAN", loader.specifications)

    def test_index_eqsp_eqnset(self):
        lines = [
            "EQSP TIM,SPS",
            'EQNSET 1 "TIM1"',
            "@",
        ]
        loader = self._make_loader(lines)
        self.assertIn(1, loader.eqsp_tim_eqnsets)

    def test_index_eqsp_specset(self):
        lines = [
            "EQSP TIM,SPS",
            'EQNSET 1 "TIM1"',
            'SPECSET 1 "SPS1"',
            "@",
        ]
        loader = self._make_loader(lines)
        self.assertIn((1, 1), loader.eqsp_tim_specsets)


class TestParseSpecificationSpecs(unittest.TestCase):
    """Tests for TimingLoader.parse_specification_specs()."""

    def test_parse_basic_specs(self):
        lines = [
            'SPECIFICATION "TEST"',
            'TCLK  10.0  [ns]',
            'TPER  20.0  [ns]  # comment',
        ]
        loader = TimingLoader.__new__(TimingLoader)
        loader.lines = lines
        specs = loader.parse_specification_specs(0)
        self.assertEqual(len(specs), 2)
        self.assertEqual(specs["TCLK"].value, "10.0")
        self.assertEqual(specs["TCLK"].units, "ns")
        self.assertEqual(specs["TPER"].value, "20.0")
        self.assertEqual(specs["TPER"].comment, "# comment")

    def test_parse_stops_at_next_specification(self):
        lines = [
            'SPECIFICATION "TEST"',
            'TCLK  10.0  [ns]',
            'SPECIFICATION "NEXT"',
        ]
        loader = TimingLoader.__new__(TimingLoader)
        loader.lines = lines
        specs = loader.parse_specification_specs(0)
        self.assertEqual(len(specs), 1)
        self.assertIn("TCLK", specs)

    def test_parse_empty_block(self):
        lines = [
            'SPECIFICATION "TEST"',
            'SPECIFICATION "NEXT"',
        ]
        loader = TimingLoader.__new__(TimingLoader)
        loader.lines = lines
        specs = loader.parse_specification_specs(0)
        self.assertEqual(len(specs), 0)


class TestParseEqspEqnsetBlock(unittest.TestCase):
    """Tests for TimingLoader.parse_eqsp_eqnset_block()."""

    def test_parse_basic_eqnset(self):
        lines = [
            'EQNSET 1 "TIM1"',
            'SPECSET 1 "SPS1"',
            '# SPECNAME  VALUE  [UNITS]',
            'TCLK  10.0  [ns]',
            'TPER  20.0  [ns]',
        ]
        loader = TimingLoader.__new__(TimingLoader)
        loader.lines = lines
        block = loader.parse_eqsp_eqnset_block(0)
        self.assertIsNotNone(block)
        self.assertEqual(block.eqnset_index, 1)
        self.assertEqual(block.eqnset_name, "TIM1")
        self.assertEqual(block.specset_index, 1)
        self.assertEqual(block.specset_name, "SPS1")
        self.assertEqual(len(block.specs), 2)
        self.assertEqual(block.specs["TCLK"].value, "10.0")
        self.assertEqual(block.specs["TCLK"].units, "ns")

    def test_parse_stops_at_next_eqnset(self):
        lines = [
            'EQNSET 1 "TIM1"',
            'SPECSET 1 "SPS1"',
            '# SPECNAME  VALUE  [UNITS]',
            'TCLK  10.0  [ns]',
            'EQNSET 2 "TIM2"',
        ]
        loader = TimingLoader.__new__(TimingLoader)
        loader.lines = lines
        block = loader.parse_eqsp_eqnset_block(0)
        self.assertIsNotNone(block)
        self.assertEqual(len(block.specs), 1)
        self.assertIn("TCLK", block.specs)

    def test_parse_stops_at_at(self):
        lines = [
            'EQNSET 1 "TIM1"',
            'SPECSET 1 "SPS1"',
            '# SPECNAME  VALUE  [UNITS]',
            'TCLK  10.0  [ns]',
            '@',
        ]
        loader = TimingLoader.__new__(TimingLoader)
        loader.lines = lines
        block = loader.parse_eqsp_eqnset_block(0)
        self.assertIsNotNone(block)
        self.assertEqual(len(block.specs), 1)

    def test_parse_invalid_header(self):
        lines = [
            'SPECSET 1 "TEST"',
        ]
        loader = TimingLoader.__new__(TimingLoader)
        loader.lines = lines
        block = loader.parse_eqsp_eqnset_block(0)
        self.assertIsNone(block)


class TestExtractSnippet(unittest.TestCase):
    """Tests for snippet extraction."""

    def test_extract_snippet_boundary(self):
        lines = [
            'SPECIFICATION "TEST"',
            'TCLK  10.0  [ns]',
            'WAVETBL "W1"',
        ]
        loader = TimingLoader.__new__(TimingLoader)
        loader.lines = lines
        snippet = loader.extract_snippet(0)
        self.assertIn('SPECIFICATION "TEST"', snippet)
        self.assertIn("TCLK", snippet)
        self.assertNotIn("WAVETBL", snippet)

    def test_extract_braced_snippet(self):
        lines = [
            'SPECIFICATION "TEST"',
            '{',
            'CHECK all',
            'EQNSET 10 "E1"',
            'WAVETBL "W1"',
            'PORT P1',
            'SYNC',
            '{',
            '}',
            'TCLK  10.0  [ns]',
            '}',
            'EQNSET 3 "NEXT"',
        ]
        loader = TimingLoader.__new__(TimingLoader)
        loader.lines = lines
        snippet = loader.extract_snippet(0)
        self.assertIn('SPECIFICATION "TEST"', snippet)
        self.assertIn("TCLK", snippet)
        self.assertIn("WAVETBL", snippet)
        self.assertIn("PORT P1", snippet)
        self.assertNotIn('EQNSET 3', snippet)

    def test_extract_eqsp_snippet_boundary(self):
        lines = [
            'EQNSET 1 "TIM1"',
            'SPECSET 1 "SPS1"',
            'EQNSET 2 "TIM2"',
        ]
        loader = TimingLoader.__new__(TimingLoader)
        loader.lines = lines
        snippet = loader.extract_eqsp_snippet(0)
        self.assertIn('EQNSET 1', snippet)
        self.assertIn("SPECSET", snippet)
        self.assertNotIn('EQNSET 2', snippet)


class TestParseBracedSpecification(unittest.TestCase):
    """Tests for braced SPECIFICATION block parsing."""

    def test_parse_braced_specification(self):
        lines = [
            'SPECIFICATION "TEST"',
            '{',
            'CHECK all',
            'EQNSET 10 "E1"',
            'WAVETBL "W1"',
            'PORT P1',
            'SYNC',
            '{',
            '}',
            'TCLK  10.0  [ns]',
            '}',
            'EQNSET 3 "NEXT"',
        ]
        loader = TimingLoader.__new__(TimingLoader)
        loader.lines = lines
        specs = loader.parse_specification_specs(0)
        self.assertEqual(len(specs), 1)
        self.assertIn("P1/TCLK", specs)
        self.assertEqual(specs["P1/TCLK"].value, "10.0")
        self.assertEqual(specs["P1/TCLK"].units, "ns")

    def test_parse_duplicate_specs_with_context(self):
        lines = [
            'SPECIFICATION "TEST"',
            '{',
            'EQNSET 10 "E1"',
            'PORT P1',
            'TCLK  10.0  [ns]',
            'EQNSET 15 "E2"',
            'PORT P2',
            'TCLK  20.0  [ns]',
            '}',
        ]
        loader = TimingLoader.__new__(TimingLoader)
        loader.lines = lines
        specs = loader.parse_specification_specs(0)
        self.assertEqual(len(specs), 2)
        self.assertEqual(specs["P1/TCLK"].value, "10.0")
        self.assertEqual(specs["P2/TCLK"].value, "20.0")

    def test_parse_stops_at_closing_brace(self):
        lines = [
            'SPECIFICATION "TEST"',
            '{',
            'TCLK  10.0  [ns]',
            '}',
            'WAVETBL "W1"',
        ]
        loader = TimingLoader.__new__(TimingLoader)
        loader.lines = lines
        specs = loader.parse_specification_specs(0)
        self.assertEqual(len(specs), 1)
        self.assertIn("TCLK", specs)


class TestParsePinsGroup(unittest.TestCase):
    """Tests for TimingLoader.parse_pins_group()."""

    def test_parse_basic_pins(self):
        lines = [
            'PINS ALL_IO',
            'd1 = 0 * per',
            'r1 = 0.7 * per',
        ]
        loader = TimingLoader.__new__(TimingLoader)
        loader.lines = lines
        cfg = loader.parse_pins_group(0)
        self.assertEqual(cfg.d1, "0 * per")
        self.assertEqual(cfg.r1, "0.7 * per")

    def test_parse_multiple_edges(self):
        lines = [
            'PINS GPIOC_1',
            'd1 = 0.0*per_40',
            'd2 = 0.25*per_40',
            'd3 = 0.75*per_40',
            'r1 = 0.225*per_40',
        ]
        loader = TimingLoader.__new__(TimingLoader)
        loader.lines = lines
        cfg = loader.parse_pins_group(0)
        self.assertEqual(cfg.d1, "0.0*per_40")
        self.assertEqual(cfg.d2, "0.25*per_40")
        self.assertEqual(cfg.d3, "0.75*per_40")
        self.assertEqual(cfg.r1, "0.225*per_40")

    def test_parse_unknown_edges_in_extra(self):
        lines = [
            'PINS TEST',
            'd1 = 0',
            'x1 = 1',
        ]
        loader = TimingLoader.__new__(TimingLoader)
        loader.lines = lines
        cfg = loader.parse_pins_group(0)
        self.assertEqual(cfg.d1, "0")
        self.assertEqual(cfg.extra.get("x1"), "1")
        self.assertIn("x1", cfg.extra)

    def test_parse_stops_at_boundary(self):
        lines = [
            'PINS P1',
            'd1 = 0',
            'PINS P2',
            'd1 = 1',
        ]
        loader = TimingLoader.__new__(TimingLoader)
        loader.lines = lines
        cfg = loader.parse_pins_group(0)
        self.assertEqual(cfg.d1, "0")


class TestParseTimingSet(unittest.TestCase):
    """Tests for TimingLoader.parse_timingset()."""

    def test_parse_basic_timingset(self):
        lines = [
            'TIMINGSET 1 "OS"',
            'period = per',
        ]
        loader = TimingLoader.__new__(TimingLoader)
        loader.lines = lines
        cfg = loader.parse_timingset(0)
        self.assertIsNotNone(cfg)
        self.assertEqual(cfg.index, 1)
        self.assertEqual(cfg.name, "OS")
        self.assertEqual(cfg.period, "per")

    def test_parse_timingset_with_extra(self):
        lines = [
            'TIMINGSET 1 "T1"',
            'period = per',
            'extra_field = 123',
        ]
        loader = TimingLoader.__new__(TimingLoader)
        loader.lines = lines
        cfg = loader.parse_timingset(0)
        self.assertIsNotNone(cfg)
        self.assertEqual(cfg.period, "per")
        self.assertEqual(cfg.extra.get("extra_field"), "123")

    def test_parse_stops_at_boundary(self):
        lines = [
            'TIMINGSET 1 "T1"',
            'period = per',
            'PINS P1',
            'd1 = 0',
        ]
        loader = TimingLoader.__new__(TimingLoader)
        loader.lines = lines
        cfg = loader.parse_timingset(0)
        self.assertIsNotNone(cfg)
        self.assertEqual(cfg.period, "per")


class TestParseEqnsetBlockFull(unittest.TestCase):
    """Tests for TimingLoader.parse_eqsp_eqnset_block() with pins and timingsets."""

    def test_parse_eqnset_with_pins_and_timingset(self):
        lines = [
            'EQNSET 1 "OS_FUNC"',
            'SPECS',
            'per',
            'TIMINGSET 1 "OS"',
            'period = per',
            'PINS ALL_IO',
            'd1 = 0 * per',
            'r1 = 0.7 * per',
        ]
        loader = TimingLoader.__new__(TimingLoader)
        loader.lines = lines
        block = loader.parse_eqsp_eqnset_block(0)
        self.assertIsNotNone(block)
        self.assertEqual(block.eqnset_index, 1)
        self.assertEqual(len(block.specs), 1)
        self.assertIn("per", block.specs)
        self.assertEqual(len(block.timingsets), 1)
        self.assertIn(1, block.timingsets)
        self.assertEqual(block.timingsets[1].name, "OS")
        self.assertEqual(len(block.pins_groups), 1)
        self.assertIn("ALL_IO", block.pins_groups)
        self.assertEqual(block.pins_groups["ALL_IO"].d1, "0 * per")

    def test_parse_eqnset_multiple_pins(self):
        lines = [
            'EQNSET 2 "Temp"',
            'SPECS',
            'I2C_Per',
            'TIMINGSET 1 "Temp"',
            'period = I2C_Per',
            'PINS NO_Temp_Sensor',
            'd1 = 0 * I2C_Per',
            'PINS SCL_TEMP1 SCL_TEMP2',
            'd1 = 0   * 	I2C_Per',
            'd2 = 0.5 *  I2C_Per',
        ]
        loader = TimingLoader.__new__(TimingLoader)
        loader.lines = lines
        block = loader.parse_eqsp_eqnset_block(0)
        self.assertIsNotNone(block)
        self.assertEqual(len(block.pins_groups), 2)
        self.assertIn("NO_Temp_Sensor", block.pins_groups)
        self.assertIn("SCL_TEMP1 SCL_TEMP2", block.pins_groups)
        self.assertEqual(block.pins_groups["SCL_TEMP1 SCL_TEMP2"].d2, "0.5 *  I2C_Per")


class TestParseSpecificationEqnsetIndex(unittest.TestCase):
    """Tests for TimingLoader.parse_specification_eqnset_index()."""

    def test_parse_single_eqnset(self):
        lines = [
            'SPECIFICATION "BSCAN"',
            '{',
            'CHECK all',
            'EQNSET 4 "gen_tp1_BSCAN"',
            'WAVETBL "gen_tp1_BSCAN"',
            'PORT BSCAN',
            'SYNC',
            '{',
            '}',
            'per_40  50  [ ns]',
            '}',
        ]
        loader = TimingLoader.__new__(TimingLoader)
        loader.lines = lines
        idx = loader.parse_specification_eqnset_index(0)
        self.assertEqual(idx, 4)

    def test_parse_multiple_eqnsets(self):
        lines = [
            'SPECIFICATION "TEST"',
            '{',
            'EQNSET 4 "E1"',
            'EQNSET 14 "E2"',
            '}',
        ]
        loader = TimingLoader.__new__(TimingLoader)
        loader.lines = lines
        idx = loader.parse_specification_eqnset_index(0)
        self.assertEqual(idx, 4)
        all_eqn = loader.parse_specification_all_eqnsets(0)
        self.assertEqual(len(all_eqn), 2)
        self.assertEqual(all_eqn[0], (4, "E1"))
        self.assertEqual(all_eqn[1], (14, "E2"))

    def test_parse_no_eqnset(self):
        lines = [
            'SPECIFICATION "TEST"',
            '{',
            'TCLK  10.0  [ns]',
            '}',
        ]
        loader = TimingLoader.__new__(TimingLoader)
        loader.lines = lines
        idx = loader.parse_specification_eqnset_index(0)
        self.assertIsNone(idx)


if __name__ == "__main__":
    unittest.main()
