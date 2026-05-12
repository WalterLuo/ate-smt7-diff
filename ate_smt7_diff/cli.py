#!/usr/bin/env python3
"""
CLI entry point for the SMT7 diff engine.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from ate_smt7_diff.builder import diff_flow_files
from ate_smt7_diff.flow_matcher import FlowMatcher
from ate_smt7_diff.formatters.console import format_console
from ate_smt7_diff.formatters.json import format_json
from ate_smt7_diff.formatters.markdown import format_markdown
from ate_smt7_diff.models import BatchDiffReport, DiffReport


def _run_single_diff(
    old_path: Path,
    new_path: Path,
    args: argparse.Namespace,
) -> DiffReport:
    """Run diff for a single pair of flow files."""
    return diff_flow_files(
        str(old_path),
        str(new_path),
        include_suite_diff=args.suite_diff or args.load_configs,
        include_config_views=args.load_configs or args.testtable_diff or args.testmethod_diff,
        include_testtable_diff=args.load_configs or args.testtable_diff,
        include_testmethod_diff=args.load_configs or args.testmethod_diff,
    )


def _run_batch_diff(
    old_pkg: Path,
    new_pkg: Path,
    matcher: FlowMatcher,
    args: argparse.Namespace,
) -> BatchDiffReport:
    """Run diff for all matched flow file pairs in two packages."""
    old_flow_dir = old_pkg / "testflow"
    new_flow_dir = new_pkg / "testflow"

    if not old_flow_dir.exists():
        print(f"Error: testflow directory not found: {old_flow_dir}", file=sys.stderr)
        sys.exit(1)
    if not new_flow_dir.exists():
        print(f"Error: testflow directory not found: {new_flow_dir}", file=sys.stderr)
        sys.exit(1)

    pairs = matcher.match_directories(old_flow_dir, new_flow_dir)
    if not pairs:
        print("Error: No flow files matched between packages.", file=sys.stderr)
        sys.exit(1)

    batch = BatchDiffReport(
        old_package=str(old_pkg),
        new_package=str(new_pkg),
    )

    for old_flow, new_flow in pairs:
        report = _run_single_diff(old_flow, new_flow, args)
        batch.pairs.append((str(old_flow), str(new_flow), report))

    return batch


def _format_batch_markdown(batch: BatchDiffReport) -> str:
    """Format a batch diff report as Markdown."""
    lines: list[str] = []
    lines.append("# SMT7 Batch Flow Diff Report")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append("| Item | Value |")
    lines.append("|------|-------|")
    lines.append(f"| Old Package | {batch.old_package} |")
    lines.append(f"| New Package | {batch.new_package} |")
    lines.append(f"| Total Pairs | {batch.total_pairs} |")
    lines.append(f"| Pairs with Changes | {len(batch.pairs_with_changes)} |")
    lines.append("")

    for old_f, new_f, report in batch.pairs:
        lines.append("---")
        lines.append("")
        lines.append(f"## {Path(old_f).name} vs {Path(new_f).name}")
        lines.append("")
        lines.append(format_markdown(report))
        lines.append("")

    return "\n".join(lines)


def _format_batch_json(batch: BatchDiffReport) -> str:
    """Format a batch diff report as JSON."""
    return json.dumps(
        {
            "old_package": batch.old_package,
            "new_package": batch.new_package,
            "total_pairs": batch.total_pairs,
            "pairs": [
                {
                    "old_file": old_f,
                    "new_file": new_f,
                    "report": json.loads(format_json(report)),
                }
                for old_f, new_f, report in batch.pairs
            ],
        },
        indent=2,
    )


def _format_batch_console(batch: BatchDiffReport) -> str:
    """Format a batch diff report for console."""
    lines: list[str] = []
    lines.append("=" * 60)
    lines.append("SMT7 Batch Flow Diff Report")
    lines.append("=" * 60)
    lines.append(f"Old Package: {batch.old_package}")
    lines.append(f"New Package: {batch.new_package}")
    lines.append(f"Total Pairs: {batch.total_pairs}")
    lines.append(f"Pairs with Changes: {len(batch.pairs_with_changes)}")
    lines.append("")

    for old_f, new_f, report in batch.pairs:
        lines.append("-" * 60)
        lines.append(f"{Path(old_f).name} vs {Path(new_f).name}")
        lines.append("-" * 60)
        lines.append(format_console(report))
        lines.append("")

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="SMT7 Flow Diff Engine")
    parser.add_argument("old_file", nargs="?", help="Path to old .flow file")
    parser.add_argument("new_file", nargs="?", help="Path to new .flow file")
    parser.add_argument(
        "--packages",
        nargs=2,
        metavar=("OLD_PKG", "NEW_PKG"),
        help="Compare two program packages by scanning testflow/ dirs",
    )
    parser.add_argument(
        "--match-config",
        help="Path to flow matching config file (JSON)",
    )
    parser.add_argument(
        "--format",
        "-f",
        choices=["console", "markdown", "json"],
        default="console",
        help="Output format",
    )
    parser.add_argument(
        "--suite-diff",
        action="store_true",
        help="Also diff test suite configurations for common tests",
    )
    parser.add_argument(
        "--load-configs",
        action="store_true",
        help="Load associated timing/level/vector/testtable config files",
    )
    parser.add_argument(
        "--testtable-diff",
        action="store_true",
        help="Also diff testtable CSV files for common test suites",
    )
    parser.add_argument(
        "--testmethod-diff",
        action="store_true",
        help="Also diff testmethod source files for common test suites",
    )
    args = parser.parse_args()

    if args.packages:
        if args.old_file or args.new_file:
            parser.error("Cannot mix --packages with positional file arguments")
    elif not args.old_file or not args.new_file:
        parser.error("Requires either --packages OLD_PKG NEW_PKG or two .flow files")

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    try:
        if args.packages:
            old_pkg = Path(args.packages[0]).resolve()
            new_pkg = Path(args.packages[1]).resolve()

            matcher = FlowMatcher.from_config(args.match_config)
            batch = _run_batch_diff(old_pkg, new_pkg, matcher, args)

            formatters = {
                "markdown": _format_batch_markdown,
                "json": _format_batch_json,
                "console": _format_batch_console,
            }
            print(formatters[args.format](batch))
        else:
            old_path = Path(args.old_file).resolve()
            new_path = Path(args.new_file).resolve()

            if old_path.suffix.lower() != ".flow":
                print(f"Error: Expected .flow file: {args.old_file}", file=sys.stderr)
                sys.exit(1)
            if new_path.suffix.lower() != ".flow":
                print(f"Error: Expected .flow file: {args.new_file}", file=sys.stderr)
                sys.exit(1)

            report = _run_single_diff(old_path, new_path, args)

            formatters = {
                "markdown": format_markdown,
                "json": format_json,
                "console": format_console,
            }
            print(formatters[args.format](report))

    except (FileNotFoundError, PermissionError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
