#!/usr/bin/env python3
"""Markdown formatter for diff reports."""

from pathlib import Path

from ate_smt7_diff.formatters.markdown_level import (
    _aggregate_eqnset_diffs,
    _eqnset_change_key,
    _format_eqnset_markdown,
    _format_eqnset_pattern_markdown,
    _format_level_spec_markdown,
)
from ate_smt7_diff.formatters.markdown_suite import (
    _format_testmethod_table,
    _format_testtable_markdown,
    _format_vector_markdown,
)
from ate_smt7_diff.formatters.markdown_timing import (
    _aggregate_timing_eqnset_replacements,
    _aggregate_wavetbl_replacements,
    _format_eqnset_block_markdown,
    _format_timing_eqnset_markdown,
    _format_timing_spec_markdown,
    _format_wavetbl_block_markdown,
    _format_wavetbl_markdown,
)
from ate_smt7_diff.formatters.shared import fmt_val
from ate_smt7_diff.models import DiffReport, DiffType, SuiteConfigReport


def _program_name(file_path: str) -> str:
    """Extract program directory name from flow file path.

    e.g. ``Test1/example1/testflow/example1.flow`` -> ``Test1/example1``
    """
    p = Path(file_path)
    root = p.parent.parent
    parts = root.parts
    if len(parts) >= 2:
        return str(Path(*parts[-2:]))
    return str(root)


# ---------------------------------------------------------------------------
# Suite config
# ---------------------------------------------------------------------------


def format_suite_markdown(report: SuiteConfigReport) -> str:
    """Format suite config diff as Markdown."""
    lines = []
    lines.append("## Suite Configuration Diff")
    lines.append("")
    lines.append(
        f"- **Common suites**: {len(report.common_suites)} "
        f"({len(report.suites_with_changes)} with changes)"
    )

    if report.skipped_suites:
        lines.append("")
        lines.append(f"- **Skipped** (not in test_suites): {len(report.skipped_suites)}")
        for name in report.skipped_suites:
            lines.append(f"  - `{name}`")

    for diff in report.diffs:
        if not diff.has_changes:
            continue

        lines.append("")
        lines.append(f"### {diff.suite_name}")

        if diff.changed:
            lines.append("")
            lines.append("| Key | Old Value | New Value |")
            lines.append("|-----|-----------|-----------|")
            for key, (old_val, new_val) in diff.changed.items():
                lines.append(f"| `{key}` | `{old_val}` | `{fmt_val(new_val)}` |")

        if diff.added:
            lines.append("")
            lines.append("**Added:**")
            for key, val in diff.added.items():
                lines.append(f"- `{key}` = `{val}`")

        if diff.removed:
            lines.append("")
            lines.append("**Removed:**")
            for key, val in diff.removed.items():
                lines.append(f"- ~~`{key}` = `{val}`~~")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main formatter
# ---------------------------------------------------------------------------


def format_markdown(report: DiffReport) -> str:
    """Format diff report as Markdown."""
    lines = []
    lines.append("# SMT7 Flow Diff Report")
    lines.append("")

    old_prog = _program_name(report.old_file)
    new_prog = _program_name(report.new_file)
    lines.append("## Diff Summary")
    lines.append("")
    lines.append("| Item | Old | New |")
    lines.append("|------|-----|-----|")
    lines.append(f"| Flow File | {Path(report.old_file).name} | {Path(report.new_file).name} |")
    lines.append(f"| Total Tests | {len(report.old_tests)} | {len(report.new_tests)} |")
    lines.append(f"| Added | - | {len(report.added)} |")
    lines.append(f"| Removed | - | {len(report.removed)} |")
    lines.append(f"| Unchanged | - | {len(report.unchanged)} |")
    if report.suite_config_report:
        lines.append(
            f"| Suites with Config Changes | - | {len(report.suite_config_report.suites_with_changes)} |"
        )

    lines.append("")
    lines.append("---")

    if report.added or report.removed or report.moved:
        lines.append("")
        lines.append("## Flow Sequence Changes")

    if report.added:
        lines.append("")
        lines.append(f"### Added Tests ({len(report.added)})")
        added_entries = [d for d in report.diffs if d.diff_type == DiffType.ADDED]
        if added_entries:
            lines.append("")
            lines.append("| Test Name | New Position |")
            lines.append("|-----------|-------------|")
            for d in sorted(added_entries, key=lambda x: x.new_index or 0):
                pos = d.new_index + 1 if d.new_index is not None else "?"
                lines.append(f"| `{d.suite_name}` | {pos} |")
        else:
            for name in report.added:
                lines.append(f"- `{name}`")

    if report.removed:
        lines.append("")
        lines.append(f"### Removed Tests ({len(report.removed)})")
        removed_entries = [d for d in report.diffs if d.diff_type == DiffType.REMOVED]
        if removed_entries:
            lines.append("")
            lines.append("| Test Name | Old Position |")
            lines.append("|-----------|-------------|")
            for d in sorted(removed_entries, key=lambda x: x.old_index or 0):
                pos = d.old_index + 1 if d.old_index is not None else "?"
                lines.append(f"| `{d.suite_name}` | {pos} |")
        else:
            for name in report.removed:
                lines.append(f"- ~~`{name}`~~")

    if report.moved:
        lines.append("")
        lines.append(f"### Moved Tests ({len(report.moved)})")
        lines.append("")
        lines.append("| Test Name | Old Position | New Position |")
        lines.append("|-----------|-------------|-------------|")
        for name in report.moved:
            entries = [
                d for d in report.diffs if d.suite_name == name and d.diff_type == DiffType.MOVED
            ]
            for d in entries:
                old_pos = d.old_index + 1 if d.old_index is not None else "?"
                new_pos = d.new_index + 1 if d.new_index is not None else "?"
                lines.append(f"| `{name}` | {old_pos} | {new_pos} |")

    if report.order_changed:
        lines.append("")
        lines.append(f"### Order Changed Tests ({len(report.order_changed)})")
        for name in report.order_changed:
            lines.append(f"- `{name}`")

    if report.added or report.removed or report.moved or report.order_changed:
        lines.append("")
        lines.append("---")

    if report.suite_config_report is not None:
        lines.append("")
        lines.append(format_suite_markdown(report.suite_config_report))

    if report.level_spec_diffs:
        lines.append("")
        lines.append("## Level Spec Diff")
        lines.append("")
        for diff in report.level_spec_diffs:
            lines.extend(_format_level_spec_markdown(diff))

    if report.eqnset_diffs:
        lines.append("")
        lines.append("## Level EQNSET Diff")
        lines.append("")
        unique_diffs, pattern_groups = _aggregate_eqnset_diffs(report.eqnset_diffs)
        for key, suites in pattern_groups.items():
            rep_diff = next(d for d in report.eqnset_diffs if _eqnset_change_key(d) == key)
            lines.extend(_format_eqnset_pattern_markdown(rep_diff, suites))
            lines.append("")
            lines.append("---")
            lines.append("")
        for diff in unique_diffs:
            lines.extend(_format_eqnset_markdown(diff))
            lines.append("")

    if report.timing_spec_diffs:
        lines.append("")
        lines.append("## Timing Spec Diff")
        lines.append("")
        for diff in report.timing_spec_diffs:
            lines.extend(_format_timing_spec_markdown(diff))

    if report.timing_eqnset_diffs:
        lines.append("")
        lines.append("## Timing EQNSET Diff")
        lines.append("")
        replacement_groups = _aggregate_timing_eqnset_replacements(report.timing_eqnset_diffs)
        for key, group_diffs in replacement_groups.items():
            old_idx, old_name, new_idx, new_name = key
            lines.append(
                f"### Timing EQNSET Replacement: "
                f'{old_idx} "{old_name}" -> {new_idx} "{new_name}" ({len(group_diffs)} suites)'
            )
            lines.append("")
            lines.append("| Suite | Replacement |")
            lines.append("|-------|-------------|")
            for diff in group_diffs:
                lines.append(
                    f"| `{diff.suite_name}` | {diff.replaced_from_index} \"{diff.replaced_from_name}\" -> "
                    f'{diff.eqnset_index} "{diff.eqnset_name}" |'
                )
            rep = group_diffs[0]
            if rep.new_block:
                lines.append("")
                lines.append("**New EQNSET content:**")
                lines.extend(_format_eqnset_block_markdown(rep.new_block))
            lines.append("")
            lines.append("---")
            lines.append("")
        for diff in report.timing_eqnset_diffs:
            if not diff.replaced_from_name:
                lines.extend(_format_timing_eqnset_markdown(diff))
                lines.append("")

    if report.timing_wavetbl_diffs:
        lines.append("")
        lines.append("## Timing Wavetable Diff")
        lines.append("")
        wavetbl_groups = _aggregate_wavetbl_replacements(report.timing_wavetbl_diffs)
        for key, group_diffs in wavetbl_groups.items():
            old_name, new_name = key
            lines.append(
                f"### WAVETBL Replacement: {old_name} -> {new_name} ({len(group_diffs)} suites)"
            )
            lines.append("")
            lines.append("| Suite | Old | New |")
            lines.append("|-------|-----|-----|")
            for diff in group_diffs:
                lines.append(f"| `{diff.suite_name}` | {diff.replaced_from} | {diff.wavetbl_name} |")
            rep = group_diffs[0]
            if rep.new_block:
                lines.append("")
                lines.append(f"**New WAVETBL `{new_name}` content:**")
                lines.extend(_format_wavetbl_block_markdown(rep.new_block, "+"))
            lines.append("")
            lines.append("---")
            lines.append("")
        for diff in report.timing_wavetbl_diffs:
            if not diff.replaced_from:
                lines.extend(_format_wavetbl_markdown(diff))
                lines.append("")

    if report.testtable_diffs:
        lines.append("")
        lines.append("## Testtable Diff")
        lines.append("")
        for diff in report.testtable_diffs:
            lines.extend(_format_testtable_markdown(diff))
            lines.append("")

    if report.vector_diffs:
        lines.append("")
        lines.append("## Vector / Pattern Diff")
        lines.append("")
        for diff in report.vector_diffs:
            lines.extend(_format_vector_markdown(diff))
            lines.append("")

    if report.testmethod_diffs:
        lines.append("")
        lines.append("## TestMethod Diff")
        lines.append("")
        changed = [d for d in report.testmethod_diffs if d.diff_type != "unchanged"]
        if changed:
            lines.extend(_format_testmethod_table(changed))
        lines.append("")

    lines.append("")
    lines.append("## Change Statistics")
    lines.append("")
    lines.append("| Category | Count |")
    lines.append("|----------|-------|")
    lines.append(f"| Flow Sequence Changes | +{len(report.added)} / -{len(report.removed)} tests |")
    if report.suite_config_report:
        lines.append(
            f"| Suite Config Changes | {len(report.suite_config_report.suites_with_changes)} suites |"
        )
    if report.level_spec_diffs:
        lines.append(f"| Level SPEC Changes | {len(report.level_spec_diffs)} suites |")
    if report.eqnset_diffs:
        unique_count = len(_aggregate_eqnset_diffs(report.eqnset_diffs)[0])
        pattern_count = sum(
            len(suites)
            for suites in _aggregate_eqnset_diffs(report.eqnset_diffs)[1].values()
        )
        if pattern_count:
            lines.append(
                f"| Level EQNSET Changes | {unique_count} unique + {pattern_count} (common pattern) suites |"
            )
        else:
            lines.append(f"| Level EQNSET Changes | {len(report.eqnset_diffs)} suites |")
    if report.timing_spec_diffs:
        lines.append(f"| Timing Spec Changes | {len(report.timing_spec_diffs)} suites |")
    if report.timing_eqnset_diffs:
        lines.append(f"| Timing EQNSET Changes | {len(report.timing_eqnset_diffs)} suites |")
    if report.timing_wavetbl_diffs:
        lines.append(f"| Wavetable Changes | {len(report.timing_wavetbl_diffs)} suites |")
    if report.vector_diffs:
        lines.append(f"| Vector Mapping Changes | {len(report.vector_diffs)} suites |")
    if report.testmethod_diffs:
        changed_tm = len([d for d in report.testmethod_diffs if d.diff_type != "unchanged"])
        lines.append(f"| TestMethod Changes | {changed_tm} suites |")
    if report.testtable_diffs:
        lines.append(f"| Testtable Changes | {len(report.testtable_diffs)} suites |")

    return "\n".join(lines)
