#!/usr/bin/env python3
"""
Builder package: orchestrates parsing, diff computation, and config view building.
"""

from ate_smt7_diff.builder.context import load_program_context
from ate_smt7_diff.builder.suite_views import build_suite_views
from ate_smt7_diff.builder.timing_diff_dispatch import _diff_port_timing, _diff_regular_timing
from ate_smt7_diff.diff.flow_diff import compute_diff, detect_moves, detect_swaps
from ate_smt7_diff.diff.level_diff import diff_eqnset_blocks, diff_level_specs
from ate_smt7_diff.diff.suite_diff import diff_suite_configs
from ate_smt7_diff.diff.testmethod_diff import diff_testmethods
from ate_smt7_diff.diff.testtable_diff import diff_testtables
from ate_smt7_diff.diff.timing_diff import diff_wavetbls
from ate_smt7_diff.diff.vector_diff import diff_vectors
from ate_smt7_diff.filesystem import FileSystem, RealFileSystem
from ate_smt7_diff.models import (
    DiffReport,
    EqnSetDiff,
    LevelSpecDiff,
    SuiteConfigReport,
    SuiteConfigView,
    TestMethodDiff,
    TimingEqnSetDiff,
    TimingSpecDiff,
    VectorSuiteDiff,
    WaveTblDiff,
)
from ate_smt7_diff.parsers.flow_parser import extract_test_flow_section, parse_test_flow
from ate_smt7_diff.parsers.testtable_parser import TestTableLoader


def diff_flow_files(
    old_path: str,
    new_path: str,
    include_suite_diff: bool = False,
    include_config_views: bool = False,
    include_testtable_diff: bool = False,
    include_testmethod_diff: bool = False,
    fs: FileSystem | None = None,
) -> DiffReport:
    """Main entry: parse two flow files and compute diff."""
    fs = fs or RealFileSystem()
    try:
        old_lines = fs.read_text(old_path, encoding="utf-8").splitlines()
        new_lines = fs.read_text(new_path, encoding="utf-8").splitlines()
    except FileNotFoundError as e:
        raise FileNotFoundError(f"Flow file not found: {e.filename}") from e
    except PermissionError as e:
        raise PermissionError(f"Permission denied reading flow file: {e.filename}") from e
    except UnicodeDecodeError as e:
        raise ValueError(f"File encoding error (expected UTF-8): {e}") from e

    old_tf = extract_test_flow_section(old_lines)
    new_tf = extract_test_flow_section(new_lines)

    old_tests = parse_test_flow(old_tf)
    new_tests = parse_test_flow(new_tf)

    diffs = compute_diff(old_tests, new_tests)
    diffs = detect_moves(diffs)
    diffs = detect_swaps(diffs)

    suite_report: SuiteConfigReport | None = None
    if include_suite_diff:
        old_names = {t.suite_name for t in old_tests}
        new_names = {t.suite_name for t in new_tests}
        common_suites = old_names & new_names
        suite_report = diff_suite_configs(old_path, new_path, common_suites, fs)

    old_views: dict[str, SuiteConfigView] | None = None
    new_views: dict[str, SuiteConfigView] | None = None
    level_spec_diffs: list[LevelSpecDiff] | None = None
    eqnset_diffs: list[EqnSetDiff] | None = None
    timing_spec_diffs: list[TimingSpecDiff] | None = None
    timing_eqnset_diffs: list[TimingEqnSetDiff] | None = None
    timing_wavetbl_diffs: list[WaveTblDiff] | None = None
    vector_diffs: list[VectorSuiteDiff] | None = None
    testmethod_diffs: list[TestMethodDiff] | None = None
    if include_config_views:
        old_names = {t.suite_name for t in old_tests}
        new_names = {t.suite_name for t in new_tests}
        common_suites = old_names & new_names
        old_views = build_suite_views(old_path, common_suites, fs)
        new_views = build_suite_views(new_path, common_suites, fs)

        level_spec_diffs = []
        eqnset_diffs = []
        timing_spec_diffs = []
        timing_eqnset_diffs = []
        timing_wavetbl_diffs = []
        for suite_name in sorted(common_suites):
            old_v = old_views.get(suite_name)
            new_v = new_views.get(suite_name)
            if old_v and new_v:
                diff = diff_level_specs(suite_name, old_v.level_specs, new_v.level_specs)
                if diff and diff.has_changes:
                    level_spec_diffs.append(diff)
                eq_diff = diff_eqnset_blocks(suite_name, old_v.eqnset_block, new_v.eqnset_block)
                if eq_diff and eq_diff.has_changes:
                    eqnset_diffs.append(eq_diff)

                if old_v.timing_eqn_set is None and new_v.timing_eqn_set is None:
                    _diff_port_timing(
                        suite_name, old_v, new_v, timing_spec_diffs, timing_eqnset_diffs
                    )
                else:
                    _diff_regular_timing(
                        suite_name, old_v, new_v, timing_spec_diffs, timing_eqnset_diffs
                    )

                # WAVETBL diff
                wt_diffs = diff_wavetbls(
                    suite_name,
                    old_v.timing_wavetbl_blocks,
                    new_v.timing_wavetbl_blocks,
                )
                timing_wavetbl_diffs.extend(wt_diffs)
        if not level_spec_diffs:
            level_spec_diffs = None
        if not eqnset_diffs:
            eqnset_diffs = None
        if not timing_spec_diffs:
            timing_spec_diffs = None
        if not timing_eqnset_diffs:
            timing_eqnset_diffs = None
        if not timing_wavetbl_diffs:
            timing_wavetbl_diffs = None

        # Vector diff
        vector_diffs = diff_vectors(
            sorted(common_suites),
            old_views or {},
            new_views or {},
        )
        if not vector_diffs:
            vector_diffs = None

        # Testmethod diff
        if include_testmethod_diff:
            testmethod_diffs = diff_testmethods(
                sorted(common_suites),
                old_views or {},
                new_views or {},
            )
            if not testmethod_diffs:
                testmethod_diffs = None

    testtable_diffs = None
    if include_testtable_diff:
        old_names = {t.suite_name for t in old_tests}
        new_names = {t.suite_name for t in new_tests}
        common_suites = old_names & new_names

        if old_views is not None and new_views is not None:
            # Reuse already-loaded testtable data from config views
            old_rows_by_suite = {
                suite_name: view.testtable_rows
                for suite_name, view in old_views.items()
                if view.testtable_rows is not None
            }
            new_rows_by_suite = {
                suite_name: view.testtable_rows
                for suite_name, view in new_views.items()
                if view.testtable_rows is not None
            }
        else:
            old_ctx = load_program_context(old_path, fs)
            new_ctx = load_program_context(new_path, fs)
            old_testtable = (
                TestTableLoader(str(old_ctx.testtable_path), fs)
                if old_ctx.testtable_path
                else None
            )
            new_testtable = (
                TestTableLoader(str(new_ctx.testtable_path), fs)
                if new_ctx.testtable_path
                else None
            )
            old_rows_by_suite = old_testtable.rows_by_suite if old_testtable else {}
            new_rows_by_suite = new_testtable.rows_by_suite if new_testtable else {}

        testtable_diffs = diff_testtables(
            sorted(common_suites),
            old_rows_by_suite,
            new_rows_by_suite,
        )
        if not testtable_diffs:
            testtable_diffs = None

    return DiffReport(
        old_file=old_path,
        new_file=new_path,
        old_tests=old_tests,
        new_tests=new_tests,
        diffs=diffs,
        suite_config_report=suite_report,
        old_suite_views=old_views,
        new_suite_views=new_views,
        level_spec_diffs=level_spec_diffs,
        eqnset_diffs=eqnset_diffs,
        timing_spec_diffs=timing_spec_diffs,
        timing_eqnset_diffs=timing_eqnset_diffs,
        timing_wavetbl_diffs=timing_wavetbl_diffs,
        testtable_diffs=testtable_diffs,
        vector_diffs=vector_diffs,
        testmethod_diffs=testmethod_diffs,
    )
