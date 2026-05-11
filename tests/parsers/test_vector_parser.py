#!/usr/bin/env python3
"""Tests for vector_parser.py."""

import tempfile
from pathlib import Path

import pytest

from ate_smt7_diff.parsers.vector_parser import VectorLoader
from ate_smt7_diff.models import VectorPatternMapping


@pytest.fixture
def sample_vector_file():
    content = """path:
  ../vectors/SCAN_XSDS

files:
DC_SCAN_XSDS@NO_SCAN_XSDS
DC_SCAN_XSDS@SCAN_XSDS
AC_SCAN_XSDS@SCAN_XSDS
AC_SCAN_XSDS@NO_SCAN_XSDS
NO_SCAN_XSDS
zhurong_top_retargeting3_mode_saf_shift_25M_burst.burst

-- commented line
path:
  ../vectors/OTHER

files:
OTHER_PATTERN@OTHER_FILE
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(content)
        f.flush()
        yield f.name
    Path(f.name).unlink(missing_ok=True)


def test_vector_loader_parses_path_and_files(sample_vector_file):
    loader = VectorLoader(sample_vector_file)
    assert len(loader.pattern_lookup) > 0

    # Check pattern mappings
    result = loader.lookup("DC_SCAN_XSDS")
    assert result is not None
    path_dir, mappings = result
    assert path_dir == "../vectors/SCAN_XSDS"
    assert len(mappings) == 2
    assert mappings[0] == VectorPatternMapping(
        pattern_name="DC_SCAN_XSDS",
        mapped_file="NO_SCAN_XSDS",
        is_direct=False,
    )
    assert mappings[1] == VectorPatternMapping(
        pattern_name="DC_SCAN_XSDS",
        mapped_file="SCAN_XSDS",
        is_direct=False,
    )


def test_vector_loader_direct_file(sample_vector_file):
    loader = VectorLoader(sample_vector_file)

    result = loader.lookup("NO_SCAN_XSDS")
    assert result is not None
    path_dir, mappings = result
    assert len(mappings) == 1
    assert mappings[0] == VectorPatternMapping(
        pattern_name="NO_SCAN_XSDS",
        mapped_file=None,
        is_direct=True,
    )


def test_vector_loader_bursty_file(sample_vector_file):
    loader = VectorLoader(sample_vector_file)

    result = loader.lookup("zhurong_top_retargeting3_mode_saf_shift_25M_burst.burst")
    assert result is not None
    path_dir, mappings = result
    assert len(mappings) == 1
    assert mappings[0].is_direct is True
    assert mappings[0].pattern_name == "zhurong_top_retargeting3_mode_saf_shift_25M_burst.burst"


def test_vector_loader_second_path_section(sample_vector_file):
    loader = VectorLoader(sample_vector_file)

    result = loader.lookup("OTHER_PATTERN")
    assert result is not None
    path_dir, mappings = result
    assert path_dir == "../vectors/OTHER"
    assert len(mappings) == 1
    assert mappings[0] == VectorPatternMapping(
        pattern_name="OTHER_PATTERN",
        mapped_file="OTHER_FILE",
        is_direct=False,
    )


def test_vector_loader_missing_file():
    loader = VectorLoader("/nonexistent/path/to/file.txt")
    assert loader.pattern_lookup == {}


def test_vector_loader_unknown_pattern(sample_vector_file):
    loader = VectorLoader(sample_vector_file)
    assert loader.lookup("UNKNOWN_PATTERN") is None
