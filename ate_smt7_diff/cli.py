#!/usr/bin/env python3
"""
CLI entry point for the SMT7 diff engine.
"""

import argparse
import sys
from pathlib import Path

from ate_smt7_diff.builder import diff_flow_files
from ate_smt7_diff.formatters.console import format_console
from ate_smt7_diff.formatters.markdown import format_markdown
from ate_smt7_diff.formatters.json import format_json


def main() -> None:
    parser = argparse.ArgumentParser(description="SMT7 Flow Diff Engine")
    parser.add_argument("old_file", help="Path to old .flow file")
    parser.add_argument("new_file", help="Path to new .flow file")
    parser.add_argument(
        "--format", "-f",
        choices=["console", "markdown", "json"],
        default="console",
        help="Output format"
    )
    parser.add_argument(
        "--suite-diff",
        action="store_true",
        help="Also diff test suite configurations for common tests"
    )
    parser.add_argument(
        "--load-configs",
        action="store_true",
        help="Load associated timing/level/pattern/testtable config files"
    )
    args = parser.parse_args()

    old_path = Path(args.old_file).resolve()
    new_path = Path(args.new_file).resolve()

    if old_path.suffix.lower() != ".flow":
        print(f"Error: Expected .flow file: {args.old_file}", file=sys.stderr)
        sys.exit(1)
    if new_path.suffix.lower() != ".flow":
        print(f"Error: Expected .flow file: {args.new_file}", file=sys.stderr)
        sys.exit(1)

    try:
        report = diff_flow_files(
            str(old_path), str(new_path),
            include_suite_diff=args.suite_diff,
            include_config_views=args.load_configs,
        )
    except (FileNotFoundError, PermissionError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    formatters = {
        "markdown": format_markdown,
        "json": format_json,
        "console": format_console,
    }
    print(formatters[args.format](report))


if __name__ == "__main__":
    main()
