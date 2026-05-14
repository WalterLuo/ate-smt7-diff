#!/usr/bin/env python3
"""Markdown formatting for testtable, vector, and testmethod diffs."""

from ate_smt7_diff.formatters.shared import fmt_val
from ate_smt7_diff.models import (
    TestMethodDiff,
    TestTableSuiteDiff,
    VectorSuiteDiff,
)


# ---------------------------------------------------------------------------
# TestMethod
# ---------------------------------------------------------------------------


def _format_testmethod_markdown(diff: TestMethodDiff) -> list[str]:
    """Format a single TestMethodDiff as Markdown lines."""
    lines = []
    lines.append(f"### {diff.suite_name}")
    if diff.diff_type == "tm_id_changed":
        lines.append(f"- **TestMethod ID changed**: `{diff.old_tm_id}` -> `{diff.new_tm_id}`")
    elif diff.diff_type == "class_changed":
        old_cls = diff.old_class or "(none)"
        new_cls = diff.new_class or "(none)"
        lines.append(f"- **TestMethod class changed**: `{old_cls}` -> `{new_cls}`")
    elif diff.diff_type == "both_changed":
        lines.append(
            f"- **TestMethod ID changed**: `{diff.old_tm_id}` -> `{diff.new_tm_id}`"
        )
        lines.append(
            f"- **TestMethod class changed**: `{diff.old_class}` -> `{diff.new_class}`"
        )
    elif diff.diff_type == "file_not_found":
        lines.append(
            f"- **TestMethod source not found**: `{diff.new_class or diff.old_class}`"
        )
    elif diff.diff_type == "file_changed":
        lines.append(
            f"- **TestMethod source changed**: `{diff.new_class or diff.old_class}`"
        )
        if diff.file_diff:
            lines.append("")
            lines.append("```diff")
            for line in diff.file_diff:
                lines.append(line)
            lines.append("```")
    return lines


def _format_testmethod_table(diffs: list[TestMethodDiff]) -> list[str]:
    """Format all TestMethod diffs as a single Markdown table."""
    lines = []
    lines.append("| Suite | Old TestMethod | New TestMethod |")
    lines.append("|-------|----------------|----------------|")
    for diff in diffs:
        if diff.diff_type == "unchanged":
            continue
        old_str = "-"
        new_str = "-"
        if diff.diff_type in ("tm_id_changed", "both_changed"):
            old_cls = diff.old_class or ""
            new_cls = diff.new_class or ""
            old_str = f"{diff.old_tm_id}: `{old_cls}`" if diff.old_tm_id else old_cls
            new_str = f"{diff.new_tm_id}: `{new_cls}`" if diff.new_tm_id else new_cls
        elif diff.diff_type == "class_changed":
            old_str = f"`{diff.old_class or '(none)'}`"
            new_str = f"`{diff.new_class or '(none)'}`"
        elif diff.diff_type == "file_changed":
            cls = diff.new_class or diff.old_class or "(none)"
            old_str = f"`{cls}`"
            new_str = f"`{cls}` (source changed)"
        elif diff.diff_type == "file_not_found":
            cls = diff.new_class or diff.old_class or "(none)"
            old_str = f"`{cls}`"
            new_str = "not found"
        lines.append(f"| `{diff.suite_name}` | {old_str} | {new_str} |")
    return lines


# ---------------------------------------------------------------------------
# Testtable
# ---------------------------------------------------------------------------


def _format_testtable_markdown(diff: TestTableSuiteDiff) -> list[str]:
    """Format a single TestTableSuiteDiff as Markdown lines."""
    lines = []
    lines.append(f"### {diff.suite_name}")
    if diff.rows_added:
        lines.append("")
        lines.append("**Rows Added:**")
        for row in diff.rows_added:
            lines.append(f"- `{row.test_name}` ({row.test_number})")
    if diff.rows_removed:
        lines.append("")
        lines.append("**Rows Removed:**")
        for row in diff.rows_removed:
            lines.append(f"- ~~`{row.test_name}` ({row.test_number})~~")
    if diff.rows_changed:
        lines.append("")
        lines.append("**Rows Changed:**")
        lines.append("")
        lines.append("| Test | Number | Column | Old | New |")
        lines.append("|------|--------|--------|-----|-----|")
        for rd in diff.rows_changed:
            for col, (old_val, new_val) in sorted(rd.changed.items()):
                lines.append(
                    f"| `{rd.test_name}` | `{rd.test_number}` | `{col}` | `{old_val}` | `{fmt_val(new_val)}` |"
                )
    return lines


# ---------------------------------------------------------------------------
# Vector
# ---------------------------------------------------------------------------


def _format_vector_markdown(diff: VectorSuiteDiff) -> list[str]:
    """Format a single VectorSuiteDiff as Markdown lines."""
    lines = []
    if diff.diff_type == "added":
        lines.append(f"### {diff.suite_name}: Pattern Added")
        if diff.new_mappings:
            lines.append("")
            lines.append("**Mappings:**")
            for m in diff.new_mappings:
                if m.is_direct:
                    lines.append(f"- `{m.pattern_name}`")
                else:
                    lines.append(f"- `{m.pattern_name}` -> `{m.mapped_file}`")
    elif diff.diff_type == "removed":
        lines.append(f"### {diff.suite_name}: Pattern Removed")
        if diff.old_mappings:
            lines.append("")
            lines.append("**Mappings:**")
            for m in diff.old_mappings:
                if m.is_direct:
                    lines.append(f"- ~~`{m.pattern_name}`~~")
                else:
                    lines.append(f"- ~~`{m.pattern_name}` -> `{m.mapped_file}`~~")
    elif diff.diff_type == "changed":
        lines.append(f"### {diff.suite_name}: Pattern Mapping Changed")
        if diff.old_mappings:
            lines.append("")
            lines.append("**Old Mappings:**")
            for m in diff.old_mappings:
                if m.is_direct:
                    lines.append(f"- ~~`{m.pattern_name}`~~")
                else:
                    lines.append(f"- ~~`{m.pattern_name}` -> `{m.mapped_file}`~~")
        if diff.new_mappings:
            lines.append("")
            lines.append("**New Mappings:**")
            for m in diff.new_mappings:
                if m.is_direct:
                    lines.append(f"- `{m.pattern_name}`")
                else:
                    lines.append(f"- `{m.pattern_name}` -> `{m.mapped_file}`")
    elif diff.diff_type == "file_date_changed":
        lines.append(f"### {diff.suite_name}: Pattern File Date Changed")
        if diff.file_date_changes:
            lines.append("")
            lines.append("| File | Old mtime | New mtime |")
            lines.append("|------|-----------|-----------|")
            for fc in diff.file_date_changes:
                lines.append(f"| `{fc.file_path}` | `{fc.old_mtime}` | `{fc.new_mtime}` |")
    return lines
