#!/usr/bin/env python3
"""Batch diff report Markdown formatter."""

from __future__ import annotations

from pathlib import Path

from ate_smt7_diff.formatters.markdown import format_markdown
from ate_smt7_diff.models import BatchDiffReport


def format_batch_markdown(batch: BatchDiffReport) -> str:
    """Format a batch diff report as Markdown."""
    lines: list[str] = []
    lines.append("# SMT7 Flow Diff Report")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append("| Item | Value |")
    lines.append("|------|-------|")
    lines.append(f"| Old Package | {batch.old_package} |")
    lines.append(f"| New Package | {batch.new_package} |")
    lines.append(f"| Total Flows | {batch.total_pairs} |")
    lines.append(f"| Flows with Changes | {len(batch.pairs_with_changes)} |")
    lines.append("")

    for old_f, new_f, report in batch.pairs:
        lines.append("---")
        lines.append("")
        lines.append(f"## {Path(old_f).name} vs {Path(new_f).name}")
        lines.append("")
        lines.append(format_markdown(report))
        lines.append("")

    return "\n".join(lines)
