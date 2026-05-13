#!/usr/bin/env python3
"""
CLI entry point for the SMT7 diff engine.
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import logging
import sys
from pathlib import Path

from ate_smt7_diff.builder import diff_flow_files
from ate_smt7_diff.flow_matcher import FlowMatcher
from ate_smt7_diff.formatters.batch_console import format_batch_console
from ate_smt7_diff.formatters.batch_json import format_batch_json
from ate_smt7_diff.formatters.batch_markdown import format_batch_markdown
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


def _compute_dir_md5(directory: Path) -> str:
    """Compute a composite MD5 of all files under a directory.

    Files are sorted by relative path for stable hashing.
    ``history.md`` is excluded to avoid self-referential loops.
    """
    hasher = hashlib.md5()
    for file_path in sorted(directory.rglob("*")):
        if not file_path.is_file() or file_path.name == "history.md":
            continue
        try:
            rel_path = str(file_path.relative_to(directory))
            hasher.update(rel_path.encode())
            with file_path.open("rb") as f:
                while chunk := f.read(8192):
                    hasher.update(chunk)
        except (OSError, PermissionError):
            continue
    return hasher.hexdigest()


def _generate_identity_id(old_dir: Path, new_dir: Path) -> str:
    """Generate a short identity ID from the MD5 of two directories."""
    old_md5 = _compute_dir_md5(old_dir)
    new_md5 = _compute_dir_md5(new_dir)
    combined = f"{old_md5}:{new_md5}"
    return hashlib.md5(combined.encode()).hexdigest()[:12]


def _write_history(program_root: Path, content: str, identity_id: str) -> None:
    """Append diff report to history.md if identity_id is not already present."""
    history_file = program_root / "history.md"
    marker = f"<!-- DIFF_ID: {identity_id} -->"

    if history_file.exists():
        try:
            existing = history_file.read_text(encoding="utf-8")
            if marker in existing:
                logging.info("History entry %s already exists, skipping.", identity_id)
                return
        except (OSError, PermissionError):
            pass

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    section = f"\n---\n\n{marker}\n**Diff Time:** {timestamp}\n\n{content}\n"

    try:
        with history_file.open("a", encoding="utf-8") as f:
            f.write(section)
        logging.info("Appended diff report to %s", history_file)
    except (OSError, PermissionError) as e:
        logging.warning("Failed to write history file %s: %s", history_file, e)


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
                "markdown": format_batch_markdown,
                "json": format_batch_json,
                "console": format_batch_console,
            }
            output = formatters[args.format](batch)
            print(output)

            identity_id = _generate_identity_id(old_pkg, new_pkg)
            _write_history(new_pkg, format_batch_markdown(batch), identity_id)
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
            output = formatters[args.format](report)
            print(output)

            old_root = old_path.parent.parent
            new_root = new_path.parent.parent
            identity_id = _generate_identity_id(old_root, new_root)
            _write_history(new_root, format_markdown(report), identity_id)

    except (FileNotFoundError, PermissionError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
