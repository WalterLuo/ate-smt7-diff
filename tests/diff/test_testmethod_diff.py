#!/usr/bin/env python3
"""Tests for testmethod_diff.py."""

from pathlib import Path

from ate_smt7_diff.diff.testmethod_diff import diff_testmethods
from ate_smt7_diff.models import SuiteConfigView, TestMethodDiff, TestMethodInfo


def _make_view(tm_id: str | None, cls: str | None, path: Path | None = None, content: str | None = None) -> SuiteConfigView:
    """Helper to build a SuiteConfigView with optional TestMethodInfo."""
    tm = None
    if tm_id is not None or cls is not None:
        tm = TestMethodInfo(
            tm_id=tm_id or "",
            testmethod_class=cls or "",
            file_path=path,
            content=content,
        )
    return SuiteConfigView(
        suite_name="SuiteA",
        flow_config={},
        timing_spec_set=None,
        level_eqn_set=None,
        level_spec_set=None,
        timing_snippet=None,
        level_snippet=None,
        level_specs=None,
        testmethod=tm,
    )


class TestDiffTestmethods:
    def test_both_none_skipped(self) -> None:
        old_views = {"SuiteA": _make_view(None, None)}
        new_views = {"SuiteA": _make_view(None, None)}
        result = diff_testmethods(["SuiteA"], old_views, new_views)
        assert result == []

    def test_old_none_new_added(self) -> None:
        old_views = {"SuiteA": _make_view(None, None)}
        new_views = {"SuiteA": _make_view("tm_100", "YT9911CP_TML.TML.pcie_gen2")}
        result = diff_testmethods(["SuiteA"], old_views, new_views)
        assert len(result) == 1
        assert result[0].diff_type == "class_changed"
        assert result[0].new_tm_id == "tm_100"
        assert result[0].new_class == "YT9911CP_TML.TML.pcie_gen2"

    def test_new_none_old_removed(self) -> None:
        old_views = {"SuiteA": _make_view("tm_100", "YT9911CP_TML.TML.pcie_gen2")}
        new_views = {"SuiteA": _make_view(None, None)}
        result = diff_testmethods(["SuiteA"], old_views, new_views)
        assert len(result) == 1
        assert result[0].diff_type == "class_changed"
        assert result[0].old_tm_id == "tm_100"
        assert result[0].old_class == "YT9911CP_TML.TML.pcie_gen2"

    def test_tm_id_changed(self) -> None:
        old_views = {"SuiteA": _make_view("tm_100", "YT9911CP_TML.TML.pcie_gen2")}
        new_views = {"SuiteA": _make_view("tm_200", "YT9911CP_TML.TML.pcie_gen2")}
        result = diff_testmethods(["SuiteA"], old_views, new_views)
        assert len(result) == 1
        assert result[0].diff_type == "tm_id_changed"
        assert result[0].old_tm_id == "tm_100"
        assert result[0].new_tm_id == "tm_200"

    def test_class_changed(self) -> None:
        old_views = {"SuiteA": _make_view("tm_100", "YT9911CP_TML.TML.pcie_gen2")}
        new_views = {"SuiteA": _make_view("tm_100", "YT9911CP_TML.TML.sram")}
        result = diff_testmethods(["SuiteA"], old_views, new_views)
        assert len(result) == 1
        assert result[0].diff_type == "class_changed"
        assert result[0].old_class == "YT9911CP_TML.TML.pcie_gen2"
        assert result[0].new_class == "YT9911CP_TML.TML.sram"

    def test_both_changed(self) -> None:
        old_views = {"SuiteA": _make_view("tm_100", "YT9911CP_TML.TML.pcie_gen2")}
        new_views = {"SuiteA": _make_view("tm_200", "YT9911CP_TML.TML.sram")}
        result = diff_testmethods(["SuiteA"], old_views, new_views)
        assert len(result) == 1
        assert result[0].diff_type == "both_changed"
        assert result[0].old_tm_id == "tm_100"
        assert result[0].new_tm_id == "tm_200"
        assert result[0].old_class == "YT9911CP_TML.TML.pcie_gen2"
        assert result[0].new_class == "YT9911CP_TML.TML.sram"

    def test_both_missing_skipped(self) -> None:
        """Built-in testmethods missing on both sides are silently skipped."""
        old_views = {"SuiteA": _make_view("tm_100", "YT9911CP_TML.TML.pcie_gen2", None, None)}
        new_views = {"SuiteA": _make_view("tm_100", "YT9911CP_TML.TML.pcie_gen2", None, None)}
        result = diff_testmethods(["SuiteA"], old_views, new_views)
        assert result == []

    def test_one_missing_file_not_found(self) -> None:
        """If only one side has the source file, report file_not_found."""
        old_views = {"SuiteA": _make_view("tm_100", "YT9911CP_TML.TML.pcie_gen2", Path("x.cpp"), "content")}
        new_views = {"SuiteA": _make_view("tm_100", "YT9911CP_TML.TML.pcie_gen2", None, None)}
        result = diff_testmethods(["SuiteA"], old_views, new_views)
        assert len(result) == 1
        assert result[0].diff_type == "file_not_found"

    def test_unchanged_no_diff(self) -> None:
        old_views = {"SuiteA": _make_view("tm_100", "YT9911CP_TML.TML.pcie_gen2", Path("x"), "abc")}
        new_views = {"SuiteA": _make_view("tm_100", "YT9911CP_TML.TML.pcie_gen2", Path("y"), "abc")}
        result = diff_testmethods(["SuiteA"], old_views, new_views)
        assert result == []

    def test_file_changed(self) -> None:
        old_views = {"SuiteA": _make_view("tm_100", "YT9911CP_TML.TML.pcie_gen2", Path("x"), "old line\n")}
        new_views = {"SuiteA": _make_view("tm_100", "YT9911CP_TML.TML.pcie_gen2", Path("y"), "new line\n")}
        result = diff_testmethods(["SuiteA"], old_views, new_views)
        assert len(result) == 1
        assert result[0].diff_type == "file_changed"
        assert result[0].file_diff
        assert any("new line" in line for line in result[0].file_diff)

    def test_metadata_change_skips_file_diff(self) -> None:
        old_views = {"SuiteA": _make_view("tm_100", "YT9911CP_TML.TML.pcie_gen2", Path("x"), "old line\n")}
        new_views = {"SuiteA": _make_view("tm_200", "YT9911CP_TML.TML.pcie_gen2", Path("y"), "new line\n")}
        result = diff_testmethods(["SuiteA"], old_views, new_views)
        assert len(result) == 1
        assert result[0].diff_type == "tm_id_changed"
        assert result[0].file_diff == ()

    def test_multiple_suites(self) -> None:
        old_views = {
            "SuiteA": _make_view("tm_100", "YT9911CP_TML.TML.pcie_gen2", Path("a.cpp"), "content"),
            "SuiteB": _make_view("tm_200", "YT9911CP_TML.TML.sram"),
        }
        new_views = {
            "SuiteA": _make_view("tm_100", "YT9911CP_TML.TML.pcie_gen2", Path("a.cpp"), "content"),
            "SuiteB": _make_view("tm_200", "YT9911CP_TML.TML.sram_changed"),
        }
        result = diff_testmethods(["SuiteA", "SuiteB"], old_views, new_views)
        assert len(result) == 1
        assert result[0].suite_name == "SuiteB"
        assert result[0].diff_type == "class_changed"

    def test_suite_missing_from_views(self) -> None:
        old_views: dict[str, SuiteConfigView] = {}
        new_views: dict[str, SuiteConfigView] = {}
        result = diff_testmethods(["SuiteA"], old_views, new_views)
        assert result == []
