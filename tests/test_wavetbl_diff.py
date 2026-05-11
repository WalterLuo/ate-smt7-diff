#!/usr/bin/env python3
"""Tests for WAVETBL diff algorithms in timing_diff.py."""

import pytest

from ate_smt7_diff.models import (
    WaveTblBlock,
    WaveTblDiff,
    WaveTblPinsGroup,
    WaveTblPinsGroupDiff,
    WaveTblRow,
)
from ate_smt7_diff.diff.timing_diff import (
    diff_wavetbl_blocks,
    diff_wavetbl_pins_group,
    diff_wavetbls,
)


def make_group(name, rows, brk="", f=""):
    return WaveTblPinsGroup(
        pins_name=name,
        rows=tuple(rows),
        brk=brk,
        f=f,
    )


def make_block(name, groups):
    return WaveTblBlock(name=name, pins_groups={g.pins_name: g for g in groups})


class TestDiffWavetblPinsGroup:
    def test_no_changes(self):
        old = make_group("A", [WaveTblRow("0", "d1:0", "0")])
        new = make_group("A", [WaveTblRow("0", "d1:0", "0")])
        assert diff_wavetbl_pins_group(old, new) is None

    def test_row_added(self):
        old = make_group("A", [WaveTblRow("0", "d1:0", "0")])
        new = make_group("A", [
            WaveTblRow("0", "d1:0", "0"),
            WaveTblRow("1", "d1:1", "1"),
        ])
        result = diff_wavetbl_pins_group(old, new)
        assert result is not None
        assert result.rows_added == (WaveTblRow("1", "d1:1", "1"),)
        assert result.rows_removed == ()
        assert result.rows_changed == ()

    def test_row_removed(self):
        old = make_group("A", [
            WaveTblRow("0", "d1:0", "0"),
            WaveTblRow("1", "d1:1", "1"),
        ])
        new = make_group("A", [WaveTblRow("0", "d1:0", "0")])
        result = diff_wavetbl_pins_group(old, new)
        assert result is not None
        assert result.rows_added == ()
        assert result.rows_removed == (WaveTblRow("1", "d1:1", "1"),)
        assert result.rows_changed == ()

    def test_row_changed(self):
        old = make_group("A", [WaveTblRow("0", "d1:0", "0")])
        new = make_group("A", [WaveTblRow("0", "d1:1", "1")])
        result = diff_wavetbl_pins_group(old, new)
        assert result is not None
        assert result.rows_added == ()
        assert result.rows_removed == ()
        assert result.rows_changed == ((
            WaveTblRow("0", "d1:0", "0"),
            WaveTblRow("0", "d1:1", "1"),
        ),)

    def test_brk_changed(self):
        old = make_group("A", [WaveTblRow("0", "d1:0", "0")], brk="d1:0")
        new = make_group("A", [WaveTblRow("0", "d1:0", "0")], brk="d1:1")
        result = diff_wavetbl_pins_group(old, new)
        assert result is not None
        assert result.brk_old == "d1:0"
        assert result.brk_new == "d1:1"

    def test_f_changed(self):
        old = make_group("A", [WaveTblRow("0", "d1:0", "0")], f="d1:0")
        new = make_group("A", [WaveTblRow("0", "d1:0", "0")], f="d1:1")
        result = diff_wavetbl_pins_group(old, new)
        assert result is not None
        assert result.f_old == "d1:0"
        assert result.f_new == "d1:1"


class TestDiffWavetblBlocks:
    def test_both_none(self):
        assert diff_wavetbl_blocks("suite", "wt", None, None) is None

    def test_old_none(self):
        new = make_block("wt", [make_group("A", [WaveTblRow("0", "d1:0", "0")])])
        result = diff_wavetbl_blocks("suite", "wt", None, new)
        assert result is not None
        assert result.suite_name == "suite"
        assert result.wavetbl_name == "wt"
        assert result.new_block is not None
        assert "A" in result.new_block.pins_groups
        assert result.old_block is None
        assert not result.pins_groups_added
        assert not result.pins_groups_removed
        assert not result.pins_groups_changed

    def test_new_none(self):
        old = make_block("wt", [make_group("A", [WaveTblRow("0", "d1:0", "0")])])
        result = diff_wavetbl_blocks("suite", "wt", old, None)
        assert result is not None
        assert result.old_block is not None
        assert "A" in result.old_block.pins_groups
        assert result.new_block is None
        assert not result.pins_groups_added
        assert not result.pins_groups_removed
        assert not result.pins_groups_changed

    def test_pins_group_added(self):
        old = make_block("wt", [make_group("A", [WaveTblRow("0", "d1:0", "0")])])
        new = make_block("wt", [
            make_group("A", [WaveTblRow("0", "d1:0", "0")]),
            make_group("B", [WaveTblRow("0", "d1:1", "1")]),
        ])
        result = diff_wavetbl_blocks("suite", "wt", old, new)
        assert result is not None
        assert "B" in result.pins_groups_added
        assert not result.pins_groups_removed
        assert not result.pins_groups_changed

    def test_pins_group_removed(self):
        old = make_block("wt", [
            make_group("A", [WaveTblRow("0", "d1:0", "0")]),
            make_group("B", [WaveTblRow("0", "d1:1", "1")]),
        ])
        new = make_block("wt", [make_group("A", [WaveTblRow("0", "d1:0", "0")])])
        result = diff_wavetbl_blocks("suite", "wt", old, new)
        assert result is not None
        assert "B" in result.pins_groups_removed
        assert not result.pins_groups_added
        assert not result.pins_groups_changed

    def test_pins_group_changed(self):
        old = make_block("wt", [make_group("A", [WaveTblRow("0", "d1:0", "0")])])
        new = make_block("wt", [make_group("A", [WaveTblRow("0", "d1:1", "1")])])
        result = diff_wavetbl_blocks("suite", "wt", old, new)
        assert result is not None
        assert not result.pins_groups_added
        assert not result.pins_groups_removed
        assert "A" in result.pins_groups_changed

    def test_no_changes(self):
        old = make_block("wt", [make_group("A", [WaveTblRow("0", "d1:0", "0")])])
        new = make_block("wt", [make_group("A", [WaveTblRow("0", "d1:0", "0")])])
        assert diff_wavetbl_blocks("suite", "wt", old, new) is None


class TestDiffWavetbls:
    def test_multiple_wavetbls(self):
        old_blocks = {
            "wt1": make_block("wt1", [make_group("A", [WaveTblRow("0", "d1:0", "0")])]),
            "wt2": make_block("wt2", [make_group("B", [WaveTblRow("0", "d1:1", "1")])]),
        }
        new_blocks = {
            "wt1": make_block("wt1", [make_group("A", [WaveTblRow("0", "d1:0", "0")])]),
            "wt2": make_block("wt2", [make_group("B", [WaveTblRow("0", "d1:2", "2")])]),
            "wt3": make_block("wt3", [make_group("C", [WaveTblRow("0", "d1:3", "3")])]),
        }
        result = diff_wavetbls("suite", old_blocks, new_blocks)
        assert len(result) == 2
        names = {d.wavetbl_name for d in result}
        assert names == {"wt2", "wt3"}

    def test_no_changes(self):
        old_blocks = {
            "wt1": make_block("wt1", [make_group("A", [WaveTblRow("0", "d1:0", "0")])]),
        }
        new_blocks = {
            "wt1": make_block("wt1", [make_group("A", [WaveTblRow("0", "d1:0", "0")])]),
        }
        result = diff_wavetbls("suite", old_blocks, new_blocks)
        assert result == []

    def test_replacement_detected(self):
        old_blocks = {
            "old_wt": make_block("old_wt", [make_group("A", [WaveTblRow("0", "d1:0", "0")])]),
        }
        new_blocks = {
            "new_wt": make_block("new_wt", [make_group("A", [WaveTblRow("0", "d1:0", "0")])]),
        }
        result = diff_wavetbls("suite", old_blocks, new_blocks)
        assert len(result) == 1
        diff = result[0]
        assert diff.wavetbl_name == "new_wt"
        assert diff.replaced_from == "old_wt"
        assert diff.new_block is not None

    def test_replacement_with_content_diff(self):
        old_blocks = {
            "old_wt": make_block("old_wt", [
                make_group("A", [WaveTblRow("0", "d1:0", "0")]),
                make_group("B", [WaveTblRow("0", "d1:1", "1")]),
            ]),
        }
        new_blocks = {
            "new_wt": make_block("new_wt", [
                make_group("A", [WaveTblRow("0", "d1:0", "0")]),
                make_group("B", [WaveTblRow("0", "d1:2", "2")]),
            ]),
        }
        result = diff_wavetbls("suite", old_blocks, new_blocks)
        assert len(result) == 1
        diff = result[0]
        assert diff.wavetbl_name == "new_wt"
        assert diff.replaced_from == "old_wt"
        assert diff.new_block is not None
        assert "B" in diff.new_block.pins_groups
        assert not diff.pins_groups_added
        assert not diff.pins_groups_removed
        assert not diff.pins_groups_changed

    def test_no_replacement_when_keys_differ(self):
        old_blocks = {
            "old_wt": make_block("old_wt", [make_group("A", [WaveTblRow("0", "d1:0", "0")])]),
        }
        new_blocks = {
            "new_wt": make_block("new_wt", [make_group("B", [WaveTblRow("0", "d1:1", "1")])]),
        }
        result = diff_wavetbls("suite", old_blocks, new_blocks)
        assert len(result) == 2
        names = {d.wavetbl_name for d in result}
        assert names == {"old_wt", "new_wt"}
        for d in result:
            assert d.replaced_from is None
