#!/usr/bin/env python3
"""
Suite configuration diff algorithms.
"""

from pathlib import Path

from ate_smt7_diff.models import SuiteConfigDiff, SuiteConfigReport
from ate_smt7_diff.parsers.suite_parser import (
    extract_test_suites_section,
    parse_suite_config,
)


def compute_suite_config_diff(
    suite_name: str, old_config: dict[str, str], new_config: dict[str, str]
) -> SuiteConfigDiff:
    """Compute configuration differences for a single suite."""
    old_keys = set(old_config.keys())
    new_keys = set(new_config.keys())

    changed = {}
    for key in old_keys & new_keys:
        if old_config[key] != new_config[key]:
            changed[key] = (old_config[key], new_config[key])

    added = {key: new_config[key] for key in new_keys - old_keys}
    removed = {key: old_config[key] for key in old_keys - new_keys}

    return SuiteConfigDiff(
        suite_name=suite_name,
        changed=changed,
        added=added,
        removed=removed,
    )


def diff_suite_configs(
    old_path: str,
    new_path: str,
    common_suites: set[str],
) -> SuiteConfigReport:
    """
    Main entry: parse two flow files' test_suites and compute config diff.

    Only suites present in `common_suites` (i.e., run in both test_flows)
    are compared.

    Raises:
        FileNotFoundError: If either flow file does not exist.
        PermissionError: If either flow file is not readable.
        ValueError: If file encoding is not UTF-8.
    """
    try:
        old_lines = Path(old_path).read_text(encoding="utf-8").splitlines()
        new_lines = Path(new_path).read_text(encoding="utf-8").splitlines()
    except FileNotFoundError as e:
        raise FileNotFoundError(f"Flow file not found: {e.filename}") from e
    except PermissionError as e:
        raise PermissionError(f"Permission denied reading flow file: {e.filename}") from e
    except UnicodeDecodeError as e:
        raise ValueError(f"File encoding error (expected UTF-8): {e}") from e

    old_section = extract_test_suites_section(old_lines)
    new_section = extract_test_suites_section(new_lines)

    old_configs = parse_suite_config(old_section)
    new_configs = parse_suite_config(new_section)

    diffs: list[SuiteConfigDiff] = []
    missing_in_test_suites: list[str] = []

    for suite_name in sorted(common_suites):
        in_old = suite_name in old_configs
        in_new = suite_name in new_configs

        if not in_old and not in_new:
            missing_in_test_suites.append(suite_name)
            continue

        old_cfg = old_configs.get(suite_name, {})
        new_cfg = new_configs.get(suite_name, {})

        diff = compute_suite_config_diff(suite_name, old_cfg, new_cfg)
        diffs.append(diff)

    return SuiteConfigReport(
        old_file=old_path,
        new_file=new_path,
        diffs=diffs,
        common_suites=sorted(common_suites),
        skipped_suites=missing_in_test_suites,
    )
