#!/usr/bin/env python3
"""Console formatter for diff reports."""

from ate_smt7_diff.formatters.console_level import (
    _format_eqnset_console,
    _format_level_spec_console,
)
from ate_smt7_diff.formatters.console_suite import (
    _format_testmethod_console,
    _format_testtable_console,
    _format_vector_console,
)
from ate_smt7_diff.formatters.console_timing import (
    _format_timing_eqnset_console,
    _format_timing_spec_console,
    _format_wavetbl_console,
)
from ate_smt7_diff.formatters.shared import fmt_val
from ate_smt7_diff.models import DiffReport, DiffType, LevelSpecDiff, SuiteConfigReport


def format_suite_console(report: SuiteConfigReport) -> str:
    """Format suite config diff as colored console output."""
    lines = []
    lines.append("=" * 60)
    lines.append("Suite Configuration Diff Report")
    lines.append("=" * 60)
    lines.append(
        f"Common suites: {len(report.common_suites)} "
        f"({len(report.suites_with_changes)} with changes)"
    )

    if report.skipped_suites:
        lines.append("")
        lines.append(f"Missing from both test_suites: {len(report.skipped_suites)}")
        for name in report.skipped_suites:
            lines.append(f"  ? {name}")

    for diff in report.diffs:
        if not diff.has_changes:
            continue

        lines.append("")
        lines.append(f"{diff.suite_name}:")

        if diff.changed:
            lines.append("  changed:")
            for key, (old_val, new_val) in diff.changed.items():
                lines.append(f"    {key}: {old_val} -> {fmt_val(new_val)}")

        if diff.added:
            lines.append("  added:")
            for key, val in diff.added.items():
                lines.append(f"    {key}: {val}")

        if diff.removed:
            lines.append("  removed:")
            for key, val in diff.removed.items():
                lines.append(f"    {key}: {val}")

    return "\n".join(lines)


def format_console(report: DiffReport) -> str:
    """Format diff report as colored console output."""
    lines = []
    lines.append("=" * 60)
    lines.append("SMT7 Flow Diff Report")
    lines.append("=" * 60)
    lines.append(f"Old: {report.old_file} ({len(report.old_tests)} tests)")
    lines.append(f"New: {report.new_file} ({len(report.new_tests)} tests)")
    lines.append("")

    if report.added:
        lines.append(f"Added Tests ({len(report.added)}):")
        for name in report.added:
            lines.append(f"  + {name}")
        lines.append("")

    if report.removed:
        lines.append(f"Removed Tests ({len(report.removed)}):")
        for name in report.removed:
            lines.append(f"  - {name}")
        lines.append("")

    if report.moved:
        lines.append(f"Moved Tests ({len(report.moved)}):")
        for name in report.moved:
            # Find the diff entries for this move
            entries = [
                d for d in report.diffs if d.suite_name == name and d.diff_type == DiffType.MOVED
            ]
            for d in entries:
                old_pos = d.old_index + 1 if d.old_index is not None else "?"
                new_pos = d.new_index + 1 if d.new_index is not None else "?"
                old_grp = " / ".join(d.old_group_path) if d.old_group_path else "(root)"
                new_grp = " / ".join(d.new_group_path) if d.new_group_path else "(root)"
                move_info = f"    pos {old_pos} -> {new_pos}"
                if old_grp != new_grp:
                    move_info += f", group [{old_grp}] -> [{new_grp}]"
                lines.append(f"  ~ {name}{move_info}")
        lines.append("")

    if report.order_changed:
        lines.append(f"Order Changed Tests ({len(report.order_changed)}):")
        for name in report.order_changed:
            lines.append(f"  * {name}")
        lines.append("")

    unchanged_count = len(report.unchanged)
    lines.append(f"Unchanged Tests: {unchanged_count}")
    lines.append("")

    # Sequence diff detail
    lines.append("Sequence Diff Detail:")
    lines.append("-" * 60)
    for d in report.diffs:
        if d.diff_type == DiffType.UNCHANGED:
            continue
        symbol = {DiffType.ADDED: "+", DiffType.REMOVED: "-", DiffType.MOVED: "~"}.get(
            d.diff_type, "?"
        )
        pos_info = ""
        if d.old_index is not None:
            pos_info += f" [old:{d.old_index + 1}]"
        if d.new_index is not None:
            pos_info += f" [new:{d.new_index + 1}]"
        grp = ""
        if d.new_group_path:
            grp = f" (in: {' / '.join(d.new_group_path)})"
        elif d.old_group_path:
            grp = f" (was in: {' / '.join(d.old_group_path)})"
        lines.append(f"  {symbol} {d.suite_name}{pos_info}{grp}")

    if report.suite_config_report is not None:
        lines.append("")
        lines.append(format_suite_console(report.suite_config_report))

    if report.old_suite_views is not None and report.new_suite_views is not None:
        common = sorted(set(report.old_suite_views.keys()) & set(report.new_suite_views.keys()))
        # Build lookup for level spec diffs
        spec_diff_by_suite: dict[str, LevelSpecDiff] = {}
        if report.level_spec_diffs:
            for diff in report.level_spec_diffs:
                spec_diff_by_suite[diff.suite_name] = diff

        changed_suite_lines: list[str] = []
        for suite_name in common:
            old_v = report.old_suite_views[suite_name]
            new_v = report.new_suite_views[suite_name]
            suite_lines: list[str] = []

            if old_v.timing_spec_set or new_v.timing_spec_set:
                old_t = old_v.timing_spec_set or "-"
                new_t = new_v.timing_spec_set or "-"
                if old_t != new_t:
                    suite_lines.append(f"    timing spec: {old_t} -> {new_t}")
            if old_v.level_eqn_set is not None or new_v.level_eqn_set is not None:
                old_e = old_v.level_eqn_set if old_v.level_eqn_set is not None else "-"
                new_e = new_v.level_eqn_set if new_v.level_eqn_set is not None else "-"
                if old_e != new_e:
                    suite_lines.append(f"    level EQNSET: {old_e} -> {new_e}")
            if old_v.level_spec_set is not None or new_v.level_spec_set is not None:
                old_s = old_v.level_spec_set if old_v.level_spec_set is not None else "-"
                new_s = new_v.level_spec_set if new_v.level_spec_set is not None else "-"
                if old_s != new_s:
                    suite_lines.append(f"    level SPECSET: {old_s} -> {new_s}")
            if suite_name in spec_diff_by_suite:
                suite_lines.extend(_format_level_spec_console(spec_diff_by_suite[suite_name]))

            if suite_lines:
                changed_suite_lines.append(f"{suite_name}:")
                changed_suite_lines.extend(suite_lines)

        if changed_suite_lines:
            lines.append("")
            lines.append("=" * 60)
            lines.append("Level SPEC Diff")
            lines.append("=" * 60)
            lines.extend(changed_suite_lines)

    if report.eqnset_diffs:
        lines.append("")
        lines.append("=" * 60)
        lines.append("Level EQNSET Diff")
        lines.append("=" * 60)
        for diff in report.eqnset_diffs:
            lines.extend(_format_eqnset_console(diff))

    if report.timing_spec_diffs:
        lines.append("")
        lines.append("=" * 60)
        lines.append("Timing Spec Diff")
        lines.append("=" * 60)
        for diff in report.timing_spec_diffs:
            lines.extend(_format_timing_spec_console(diff))

    if report.timing_eqnset_diffs:
        lines.append("")
        lines.append("=" * 60)
        lines.append("Timing EQNSET Diff")
        lines.append("=" * 60)
        for diff in report.timing_eqnset_diffs:
            lines.extend(_format_timing_eqnset_console(diff))

    if report.timing_wavetbl_diffs:
        lines.append("")
        lines.append("=" * 60)
        lines.append("Timing Wavetable Diff")
        lines.append("=" * 60)
        for diff in report.timing_wavetbl_diffs:
            lines.extend(_format_wavetbl_console(diff))

    if report.testtable_diffs:
        lines.append("")
        lines.append("=" * 60)
        lines.append("Testtable Diff")
        lines.append("=" * 60)
        for diff in report.testtable_diffs:
            lines.extend(_format_testtable_console(diff))

    if report.vector_diffs:
        lines.append("")
        lines.append("=" * 60)
        lines.append("Vector / Pattern Diff")
        lines.append("=" * 60)
        for diff in report.vector_diffs:
            lines.extend(_format_vector_console(diff))

    if report.testmethod_diffs:
        lines.append("")
        lines.append("=" * 60)
        lines.append("TestMethod Diff")
        lines.append("=" * 60)
        for diff in report.testmethod_diffs:
            lines.extend(_format_testmethod_console(diff))

    return "\n".join(lines)
