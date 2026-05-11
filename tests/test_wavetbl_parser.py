#!/usr/bin/env python3
"""Tests for WAVETBL parsing in timing_parser.py."""

import pytest

from ate_smt7_diff.models import WaveTblBlock, WaveTblPinsGroup, WaveTblRow
from ate_smt7_diff.parsers.timing_parser import TimingLoader


SAMPLE_TIMING = """\
EQSP TIM,WVT,#9000068300WAVETBL "OS_FUNC"
PINS ALL_IO
0 "d1:0"		0
1 "d1:Z r1:M"	M
2 "d1:Z r1:X"	X

brk ""
f ""

WAVETBL "Leakage"
PINS ALL_IO
0 "d1:Z"		Z


WAVETBL "Temp_Sensor"

PINS NO_Temp_Sensor
0 	"d1:0"		0
1 	"d1:1"		1
f   "d1:1"
brk "d1:1"

PINS SCL_TEMP1 SCL_TEMP2
0 	"d1:1"		0
1 	"d1:0 d2:1"	1
f 	"d1:1"
brk "d1:1"

@

EQSP TIM,SPS,#9000009188

EQNSET 2 "Temp_Sensor"
WAVETBL "Temp_Sensor"
CHECK all
SPECSET 1 "Temp_Sensor"

SPECIFICATION "BSCAN"
{
CHECK all

EQNSET 4 "gen_tp1_BSCAN"
WAVETBL "gen_tp1_BSCAN"
PORT BSCAN
SYNC
{
}

per_40           50                                                 [ ns]

EQNSET 14 "NO_BSCAN"
WAVETBL "NO_BSCAN"
PORT NO_BSCAN
SYNC
{
}

per_40           100                                                [ ns]
}
"""


@pytest.fixture
def loader(tmp_path):
    path = tmp_path / "timing.tim"
    path.write_text(SAMPLE_TIMING, encoding="utf-8")
    return TimingLoader(str(path))


class TestParseWavetbl:
    def test_parse_wavetbl_os_func(self, loader):
        idx = loader.lookup_wavetbl("OS_FUNC")
        assert idx is not None
        block = loader.parse_wavetbl(idx)
        assert block is not None
        assert block.name == "OS_FUNC"
        assert set(block.pins_groups.keys()) == {"ALL_IO"}

        group = block.pins_groups["ALL_IO"]
        assert len(group.rows) == 3
        assert group.rows[0] == WaveTblRow("0", "d1:0", "0")
        assert group.rows[1] == WaveTblRow("1", "d1:Z r1:M", "M")
        assert group.rows[2] == WaveTblRow("2", "d1:Z r1:X", "X")
        assert group.brk == ""
        assert group.f == ""

    def test_parse_wavetbl_leakage(self, loader):
        idx = loader.lookup_wavetbl("Leakage")
        assert idx is not None
        block = loader.parse_wavetbl(idx)
        assert block is not None
        assert block.name == "Leakage"
        assert set(block.pins_groups.keys()) == {"ALL_IO"}

        group = block.pins_groups["ALL_IO"]
        assert len(group.rows) == 1
        assert group.rows[0] == WaveTblRow("0", "d1:Z", "Z")

    def test_parse_wavetbl_temp_sensor(self, loader):
        idx = loader.lookup_wavetbl("Temp_Sensor")
        assert idx is not None
        block = loader.parse_wavetbl(idx)
        assert block is not None
        assert block.name == "Temp_Sensor"
        assert set(block.pins_groups.keys()) == {"NO_Temp_Sensor", "SCL_TEMP1 SCL_TEMP2"}

        group1 = block.pins_groups["NO_Temp_Sensor"]
        assert len(group1.rows) == 2
        assert group1.rows[0] == WaveTblRow("0", "d1:0", "0")
        assert group1.rows[1] == WaveTblRow("1", "d1:1", "1")
        assert group1.f == "d1:1"
        assert group1.brk == "d1:1"

        group2 = block.pins_groups["SCL_TEMP1 SCL_TEMP2"]
        assert len(group2.rows) == 2
        assert group2.rows[0] == WaveTblRow("0", "d1:1", "0")
        assert group2.rows[1] == WaveTblRow("1", "d1:0 d2:1", "1")
        assert group2.f == "d1:1"
        assert group2.brk == "d1:1"

    def test_parse_wavetbl_strips_comments(self, loader, tmp_path):
        sample = """\
WAVETBL "TestComment"
PINS A
0 "d1:0"	0	# this is a comment
1 "d1:1"	1
brk "d1:1" # comment after brk
f "d1:0"
"""
        path = tmp_path / "comment.tim"
        path.write_text(sample, encoding="utf-8")
        l = TimingLoader(str(path))
        idx = l.lookup_wavetbl("TestComment")
        assert idx is not None
        block = l.parse_wavetbl(idx)
        assert block is not None
        group = block.pins_groups["A"]
        assert group.rows[0] == WaveTblRow("0", "d1:0", "0")
        assert group.rows[1] == WaveTblRow("1", "d1:1", "1")
        assert group.brk == "d1:1"
        assert group.f == "d1:0"

    def test_parse_wavetbl_not_found(self, loader):
        assert loader.parse_wavetbl(99999) is None

    def test_parse_wavetbl_invalid_line(self, loader):
        # line 0 is EQSP TIM,WVT header with embedded WAVETBL, so pick a non-wavetbl line
        assert loader.parse_wavetbl(2) is None


class TestExtractWavetblNameFromEqnset:
    def test_from_eqnset(self, loader):
        eqn_idx = loader.lookup_eqsp_eqnset(2)
        assert eqn_idx is not None
        name = loader.extract_wavetbl_name_from_eqnset(eqn_idx)
        assert name == "Temp_Sensor"

    def test_not_found(self, loader):
        assert loader.extract_wavetbl_name_from_eqnset(99999) is None


class TestExtractWavetblNamesFromSpecification:
    def test_from_specification(self, loader):
        spec_idx = loader.lookup_specification("BSCAN")
        assert spec_idx is not None
        names = loader.extract_wavetbl_names_from_specification(spec_idx)
        assert names == ["gen_tp1_BSCAN", "NO_BSCAN"]

    def test_not_found(self, loader):
        assert loader.extract_wavetbl_names_from_specification(99999) == []


class TestWavetblBlockEquality:
    def test_equality(self, loader):
        idx = loader.lookup_wavetbl("OS_FUNC")
        block1 = loader.parse_wavetbl(idx)
        block2 = loader.parse_wavetbl(idx)
        assert block1 == block2

    def test_inequality(self, loader):
        idx1 = loader.lookup_wavetbl("OS_FUNC")
        idx2 = loader.lookup_wavetbl("Leakage")
        block1 = loader.parse_wavetbl(idx1)
        block2 = loader.parse_wavetbl(idx2)
        assert block1 != block2
