#!/usr/bin/env python3
"""Batch diff report console formatter."""

from __future__ import annotations

from pathlib import Path

from ate_smt7_diff.formatters.console import format_console
from ate_smt7_diff.models import BatchDiffReport


def format_batch_console(batch: BatchDiffReport) -> str:
    """Format a batch diff report for console."""
    lines: list[str] = []
    lines.append("=" * 60)
    lines.append("SMT7 Batch Flow Diff Report")
    lines.append("=" * 60)
    lines.append(f"Old Package: {batch.old_package}")
    lines.append(f"New Package: {batch.new_package}")
    lines.append(f"Total Flows: {batch.total_pairs}")
    lines.append(f"Flows with Changes: {len(batch.pairs_with_changes)}")
    lines.append("")

    for old_f, new_f, report in batch.pairs:
        lines.append("-" * 60)
        lines.append(f"{Path(old_f).name} vs {Path(new_f).name}")
        lines.append("-" * 60)
        lines.append(format_console(report))
        lines.append("")

    return "\n".join(lines)
