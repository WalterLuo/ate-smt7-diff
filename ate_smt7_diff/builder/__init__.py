#!/usr/bin/env python3
"""
Builder package: orchestrates parsing, diff computation, and config view building.
"""

from ate_smt7_diff.builder.suite_views import build_suite_views
from ate_smt7_diff.diff.flow_diff import compute_diff, detect_moves, detect_swaps
from ate_smt7_diff.filesystem import FileSystem, RealFileSystem
from ate_smt7_diff.models import DiffReport, SuiteConfigView
from ate_smt7_diff.parsers.flow_parser import extract_test_flow_section, parse_test_flow

# Import builtin plugins to trigger auto-registration
from ate_smt7_diff.plugins import builtin  # noqa: F401
from ate_smt7_diff.plugins.registry import get


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

    old_names = {t.suite_name for t in old_tests}
    new_names = {t.suite_name for t in new_tests}
    common_suites = old_names & new_names

    # Determine enabled plugins from legacy boolean flags
    enabled: list[str] = []
    if include_suite_diff:
        enabled.append("suite_config")
    if include_config_views:
        enabled.extend(["level_spec", "eqnset", "timing", "timing_wavetbl", "vector"])
    if include_testmethod_diff:
        enabled.append("testmethod")
    if include_testtable_diff:
        enabled.append("testtable")

    # Load config views if any enabled plugin requires them
    needs_views = any(
        plugin.requires_views
        for name in enabled
        if (plugin := get(name)) is not None
    )

    old_views: dict[str, SuiteConfigView] | None = None
    new_views: dict[str, SuiteConfigView] | None = None
    if needs_views:
        old_views = build_suite_views(old_path, common_suites, fs)
        new_views = build_suite_views(new_path, common_suites, fs)

    # Run enabled plugins and collect their contributions
    report_kwargs: dict[str, object] = {}
    for name in enabled:
        plugin = get(name)
        if plugin is None:
            continue
        result = plugin.run(old_path, new_path, common_suites, old_views, new_views, fs)
        report_kwargs.update(result)

    return DiffReport(
        old_file=old_path,
        new_file=new_path,
        old_tests=old_tests,
        new_tests=new_tests,
        diffs=diffs,
        old_suite_views=old_views,
        new_suite_views=new_views,
        **report_kwargs,
    )
