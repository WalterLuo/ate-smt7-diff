#!/usr/bin/env python3
"""Tests for vector_diff.py."""

import tempfile
from pathlib import Path

import pytest

from ate_smt7_diff.diff.vector_diff import diff_vectors
from ate_smt7_diff.models import (
    SuiteConfigView,
    VectorPatternMapping,
    VectorSuiteMapping,
)


@pytest.fixture
def old_view_with_mapping():
    return SuiteConfigView(
        suite_name="XSDS_DC_HV",
        flow_config={"override_seqlbl": '"DC_SCAN_XSDS"'},
        timing_spec_set=None,
        level_eqn_set=None,
        level_spec_set=None,
        level_levset=None,
        timing_snippet=None,
        level_snippet=None,
        level_specs=None,
        vector_mappings=VectorSuiteMapping(
            suite_name="XSDS_DC_HV",
            seqlbl="DC_SCAN_XSDS",
            path="/tmp/old_vectors/SCAN_XSDS",
            pattern_mappings=(
                VectorPatternMapping("DC_SCAN_XSDS", "NO_SCAN_XSDS", False),
                VectorPatternMapping("DC_SCAN_XSDS", "SCAN_XSDS", False),
            ),
        ),
    )


@pytest.fixture
def new_view_with_same_mapping():
    return SuiteConfigView(
        suite_name="XSDS_DC_HV",
        flow_config={"override_seqlbl": '"DC_SCAN_XSDS"'},
        timing_spec_set=None,
        level_eqn_set=None,
        level_spec_set=None,
        level_levset=None,
        timing_snippet=None,
        level_snippet=None,
        level_specs=None,
        vector_mappings=VectorSuiteMapping(
            suite_name="XSDS_DC_HV",
            seqlbl="DC_SCAN_XSDS",
            path="/tmp/new_vectors/SCAN_XSDS",
            pattern_mappings=(
                VectorPatternMapping("DC_SCAN_XSDS", "NO_SCAN_XSDS", False),
                VectorPatternMapping("DC_SCAN_XSDS", "SCAN_XSDS", False),
            ),
        ),
    )


@pytest.fixture
def new_view_with_mapping():
    return SuiteConfigView(
        suite_name="XSDS_DC_HV",
        flow_config={"override_seqlbl": '"DC_SCAN_XSDS"'},
        timing_spec_set=None,
        level_eqn_set=None,
        level_spec_set=None,
        level_levset=None,
        timing_snippet=None,
        level_snippet=None,
        level_specs=None,
        vector_mappings=VectorSuiteMapping(
            suite_name="XSDS_DC_HV",
            seqlbl="DC_SCAN_XSDS",
            path="/tmp/new_vectors/SCAN_XSDS",
            pattern_mappings=(
                VectorPatternMapping("DC_SCAN_XSDS", "NO_SCAN_XSDS", False),
                VectorPatternMapping("DC_SCAN_XSDS", "SCAN_XSDS", False),
            ),
        ),
    )


@pytest.fixture
def new_view_with_changed_mapping():
    return SuiteConfigView(
        suite_name="XSDS_DC_HV",
        flow_config={"override_seqlbl": '"DC_SCAN_XSDS"'},
        timing_spec_set=None,
        level_eqn_set=None,
        level_spec_set=None,
        level_levset=None,
        timing_snippet=None,
        level_snippet=None,
        level_specs=None,
        vector_mappings=VectorSuiteMapping(
            suite_name="XSDS_DC_HV",
            seqlbl="DC_SCAN_XSDS",
            path="/tmp/new_vectors/SCAN_XSDS",
            pattern_mappings=(
                VectorPatternMapping("DC_SCAN_XSDS", "NO_SCAN_XSDS", False),
                VectorPatternMapping("DC_SCAN_XSDS", "CHANGED_XSDS", False),
            ),
        ),
    )


@pytest.fixture
def old_view_no_mapping():
    return SuiteConfigView(
        suite_name="XSDS_DC_HV",
        flow_config={},
        timing_spec_set=None,
        level_eqn_set=None,
        level_spec_set=None,
        level_levset=None,
        timing_snippet=None,
        level_snippet=None,
        level_specs=None,
        vector_mappings=None,
    )


@pytest.fixture
def new_view_no_mapping():
    return SuiteConfigView(
        suite_name="XSDS_DC_HV",
        flow_config={},
        timing_spec_set=None,
        level_eqn_set=None,
        level_spec_set=None,
        level_levset=None,
        timing_snippet=None,
        level_snippet=None,
        level_specs=None,
        vector_mappings=None,
    )


def test_diff_vectors_no_changes(old_view_with_mapping, new_view_with_same_mapping):
    old_views = {"XSDS_DC_HV": old_view_with_mapping}
    new_views = {"XSDS_DC_HV": new_view_with_same_mapping}
    diffs = diff_vectors(["XSDS_DC_HV"], old_views, new_views)
    assert diffs == []


def test_diff_vectors_mapping_changed(old_view_with_mapping, new_view_with_changed_mapping):
    old_views = {"XSDS_DC_HV": old_view_with_mapping}
    new_views = {"XSDS_DC_HV": new_view_with_changed_mapping}
    diffs = diff_vectors(["XSDS_DC_HV"], old_views, new_views)
    assert len(diffs) == 1
    assert diffs[0].diff_type == "changed"
    assert diffs[0].suite_name == "XSDS_DC_HV"


def test_diff_vectors_added(old_view_no_mapping, new_view_with_mapping):
    old_views = {"XSDS_DC_HV": old_view_no_mapping}
    new_views = {"XSDS_DC_HV": new_view_with_mapping}
    diffs = diff_vectors(["XSDS_DC_HV"], old_views, new_views)
    assert len(diffs) == 1
    assert diffs[0].diff_type == "added"
    assert diffs[0].suite_name == "XSDS_DC_HV"


def test_diff_vectors_removed(old_view_with_mapping, new_view_no_mapping):
    old_views = {"XSDS_DC_HV": old_view_with_mapping}
    new_views = {"XSDS_DC_HV": new_view_no_mapping}
    diffs = diff_vectors(["XSDS_DC_HV"], old_views, new_views)
    assert len(diffs) == 1
    assert diffs[0].diff_type == "removed"
    assert diffs[0].suite_name == "XSDS_DC_HV"


def test_diff_vectors_no_mapping_both_sides(old_view_no_mapping, new_view_no_mapping):
    old_views = {"XSDS_DC_HV": old_view_no_mapping}
    new_views = {"XSDS_DC_HV": new_view_no_mapping}
    diffs = diff_vectors(["XSDS_DC_HV"], old_views, new_views)
    assert diffs == []


def test_diff_vectors_file_date_changed():
    with tempfile.TemporaryDirectory() as old_dir, tempfile.TemporaryDirectory() as new_dir:
        old_file = Path(old_dir) / "DC_SCAN_XSDS@NO_SCAN_XSDS"
        new_file = Path(new_dir) / "DC_SCAN_XSDS@NO_SCAN_XSDS"
        old_file.write_text("old content")
        new_file.write_text("new content")

        old_view = SuiteConfigView(
            suite_name="XSDS_DC_HV",
            flow_config={"override_seqlbl": '"DC_SCAN_XSDS"'},
            timing_spec_set=None,
            level_eqn_set=None,
            level_spec_set=None,
            level_levset=None,
            timing_snippet=None,
            level_snippet=None,
            level_specs=None,
            vector_mappings=VectorSuiteMapping(
                suite_name="XSDS_DC_HV",
                seqlbl="DC_SCAN_XSDS",
                path=old_dir,
                pattern_mappings=(VectorPatternMapping("DC_SCAN_XSDS", "NO_SCAN_XSDS", False),),
            ),
        )
        new_view = SuiteConfigView(
            suite_name="XSDS_DC_HV",
            flow_config={"override_seqlbl": '"DC_SCAN_XSDS"'},
            timing_spec_set=None,
            level_eqn_set=None,
            level_spec_set=None,
            level_levset=None,
            timing_snippet=None,
            level_snippet=None,
            level_specs=None,
            vector_mappings=VectorSuiteMapping(
                suite_name="XSDS_DC_HV",
                seqlbl="DC_SCAN_XSDS",
                path=new_dir,
                pattern_mappings=(VectorPatternMapping("DC_SCAN_XSDS", "NO_SCAN_XSDS", False),),
            ),
        )

        old_views = {"XSDS_DC_HV": old_view}
        new_views = {"XSDS_DC_HV": new_view}
        diffs = diff_vectors(["XSDS_DC_HV"], old_views, new_views)
        assert len(diffs) == 1
        assert diffs[0].diff_type == "file_date_changed"
        assert diffs[0].suite_name == "XSDS_DC_HV"
        assert len(diffs[0].file_date_changes) == 1
        assert diffs[0].file_date_changes[0].file_path == str(new_file)
