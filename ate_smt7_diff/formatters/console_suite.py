#!/usr/bin/env python3
"""Console formatting for testtable, vector, and testmethod diffs."""

from ate_smt7_diff.formatters.shared import fmt_val
from ate_smt7_diff.models import TestMethodDiff, TestTableSuiteDiff, VectorSuiteDiff


def _format_testtable_console(diff: TestTableSuiteDiff) -> list[str]:
    """Format a single TestTableSuiteDiff as console lines."""
    lines = []
    lines.append(f"{diff.suite_name}:")
    if diff.rows_added:
        lines.append("  Rows Added:")
        for row in diff.rows_added:
            lines.append(f"    + {row.test_name} ({row.test_number})")
    if diff.rows_removed:
        lines.append("  Rows Removed:")
        for row in diff.rows_removed:
            lines.append(f"    - {row.test_name} ({row.test_number})")
    if diff.rows_changed:
        lines.append("  Rows Changed:")
        for rd in diff.rows_changed:
            changes = ", ".join(
                f"{k} {fmt_val(ov)} -> {fmt_val(nv)}"
                for k, (ov, nv) in sorted(rd.changed.items())
            )
            lines.append(f"    ~ {rd.test_name} ({rd.test_number}): {changes}")
    return lines


def _format_vector_console(diff: VectorSuiteDiff) -> list[str]:
    """Format a single VectorSuiteDiff as console lines."""
    lines = []
    if diff.diff_type == "added":
        lines.append(f"{diff.suite_name}: Pattern Added")
        if diff.new_mappings:
            for m in diff.new_mappings:
                if m.is_direct:
                    lines.append(f"    + {m.pattern_name}")
                else:
                    lines.append(f"    + {m.pattern_name} -> {m.mapped_file}")
    elif diff.diff_type == "removed":
        lines.append(f"{diff.suite_name}: Pattern Removed")
        if diff.old_mappings:
            for m in diff.old_mappings:
                if m.is_direct:
                    lines.append(f"    - {m.pattern_name}")
                else:
                    lines.append(f"    - {m.pattern_name} -> {m.mapped_file}")
    elif diff.diff_type == "changed":
        lines.append(f"{diff.suite_name}: Pattern Mapping Changed")
        if diff.old_mappings:
            lines.append("  Old:")
            for m in diff.old_mappings:
                if m.is_direct:
                    lines.append(f"    - {m.pattern_name}")
                else:
                    lines.append(f"    - {m.pattern_name} -> {m.mapped_file}")
        if diff.new_mappings:
            lines.append("  New:")
            for m in diff.new_mappings:
                if m.is_direct:
                    lines.append(f"    + {m.pattern_name}")
                else:
                    lines.append(f"    + {m.pattern_name} -> {m.mapped_file}")
    elif diff.diff_type == "file_date_changed":
        lines.append(f"{diff.suite_name}: Pattern File Date Changed")
        for fc in diff.file_date_changes:
            lines.append(f"    ~ {fc.file_path}: mtime changed")
    return lines


def _format_testmethod_console(diff: TestMethodDiff) -> list[str]:
    """Format a single TestMethodDiff as console lines."""
    lines = []
    if diff.diff_type == "tm_id_changed":
        lines.append(
            f"{diff.suite_name}: TestMethod ID changed: {diff.old_tm_id} -> {diff.new_tm_id}"
        )
    elif diff.diff_type == "class_changed":
        old_cls = diff.old_class or "(none)"
        new_cls = diff.new_class or "(none)"
        lines.append(
            f"{diff.suite_name}: TestMethod class changed: {old_cls} -> {new_cls}"
        )
    elif diff.diff_type == "both_changed":
        lines.append(
            f"{diff.suite_name}: TestMethod both changed: "
            f"ID {diff.old_tm_id} -> {diff.new_tm_id}, "
            f"class {diff.old_class} -> {diff.new_class}"
        )
    elif diff.diff_type == "file_not_found":
        lines.append(
            f"{diff.suite_name}: TestMethod source not found "
            f"({diff.new_class or diff.old_class})"
        )
    elif diff.diff_type == "file_changed":
        lines.append(
            f"{diff.suite_name}: TestMethod source changed "
            f"({diff.new_class or diff.old_class})"
        )
        for line in diff.file_diff:
            lines.append(f"  {line}")
    return lines
