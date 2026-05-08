#!/usr/bin/env python3
"""
Test suite configuration diff engine.
Parses test_suites sections and computes configuration differences.
"""

import json
import re
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


# Module-level compiled regex patterns
# Suite names and keys may contain hyphens, dots, etc.
_SUITE_NAME_RE = re.compile(r'^([^:\s]+):$')
_CONFIG_KEY_RE = re.compile(r'^([^\s=]+)\s*=\s*(.+)$')


@dataclass
class SuiteConfigDiff:
    """Configuration differences for a single test suite."""
    suite_name: str
    changed: Dict[str, Tuple[str, str]] = field(default_factory=dict)
    added: Dict[str, str] = field(default_factory=dict)
    removed: Dict[str, str] = field(default_factory=dict)

    @property
    def has_changes(self) -> bool:
        return bool(self.changed or self.added or self.removed)


@dataclass
class SuiteConfigReport:
    """Complete suite configuration diff report."""
    old_file: str
    new_file: str
    diffs: List[SuiteConfigDiff]
    common_suites: List[str]
    skipped_suites: List[str]

    @cached_property
    def suites_with_changes(self) -> List[str]:
        return [d.suite_name for d in self.diffs if d.has_changes]


def extract_context_section(lines: List[str]) -> List[str]:
    """Extract lines between 'context' and its matching 'end'."""
    in_section = False
    section_lines = []

    for line in lines:
        stripped = line.strip()

        if stripped == "context":
            in_section = True
            continue

        if in_section:
            if stripped == "end":
                break
            section_lines.append(line)

    return section_lines


def parse_context(lines: List[str]) -> Dict[str, str]:
    """Parse context section into {key: value}.

    Example input:
        context_config_file = "YT9911CP_PIN";
        context_levels_file = "YT9911CP_LEV";

    Returns:
        {"context_config_file": "YT9911CP_PIN", "context_levels_file": "YT9911CP_LEV", ...}
    """
    result: Dict[str, str] = {}
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith('//'):
            continue

        # Strip inline comments
        comment_idx = stripped.find('//')
        if comment_idx != -1:
            stripped = stripped[:comment_idx].strip()
        if not stripped:
            continue

        # key = "value";
        match = _CONFIG_KEY_RE.match(stripped)
        if match:
            key = match.group(1)
            raw_value = match.group(2).strip()
            if raw_value.endswith(';'):
                raw_value = raw_value[:-1].strip()
            # Strip quotes if present
            if len(raw_value) >= 2 and raw_value[0] == '"' and raw_value[-1] == '"':
                raw_value = raw_value[1:-1]
            result[key] = raw_value

    return result


def extract_test_suites_section(lines: List[str]) -> List[str]:
    """Extract lines between 'test_suites' and its matching 'end'."""
    in_section = False
    section_lines = []

    for line in lines:
        stripped = line.strip()

        if stripped == "test_suites":
            in_section = True
            continue

        if in_section:
            if stripped == "end":
                break
            section_lines.append(line)

    return section_lines


def parse_suite_config(lines: List[str]) -> Dict[str, Dict[str, str]]:
    """
    Parse test_suites section into {suite_name: {key: value}}.

    Each suite starts with 'SuiteName:' and continues until the next
    'SuiteName:' or the end of the section.
    """
    result: Dict[str, Dict[str, str]] = {}
    current_suite: Optional[str] = None

    for line in lines:
        stripped = line.strip()

        # Skip empty lines and pure comments
        if not stripped or stripped.startswith('//'):
            continue

        # Strip inline comments before parsing
        comment_idx = stripped.find('//')
        if comment_idx != -1:
            stripped = stripped[:comment_idx].strip()
        if not stripped:
            continue

        # Suite name line: BSCAN_HV:
        match = _SUITE_NAME_RE.match(stripped)
        if match:
            current_suite = match.group(1)
            result[current_suite] = {}
            continue

        # Config line: key = value; (trailing semicolon is stripped)
        match = _CONFIG_KEY_RE.match(stripped)
        if match and current_suite is not None:
            key = match.group(1)
            raw_value = match.group(2).strip()
            # Strip trailing semicolon if present
            if raw_value.endswith(';'):
                raw_value = raw_value[:-1].strip()
            result[current_suite][key] = raw_value
            continue

        # Ignore unrecognized lines

    return result


def compute_suite_config_diff(
    suite_name: str,
    old_config: Dict[str, str],
    new_config: Dict[str, str]
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
    common_suites: Set[str],
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

    diffs: List[SuiteConfigDiff] = []
    missing_in_test_suites: List[str] = []

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
                lines.append(f"    {key}: {old_val} -> {new_val}")

        if diff.added:
            lines.append("  added:")
            for key, val in diff.added.items():
                lines.append(f"    {key}: {val}")

        if diff.removed:
            lines.append("  removed:")
            for key, val in diff.removed.items():
                lines.append(f"    {key}: {val}")

    return "\n".join(lines)


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
                lines.append(f"| `{key}` | `{old_val}` | `{new_val}` |")

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


def format_suite_json(report: SuiteConfigReport) -> dict:
    """Format suite config diff as a JSON-serializable dict."""
    diffs = []
    for diff in report.diffs:
        if not diff.has_changes:
            continue
        diffs.append({
            "suite_name": diff.suite_name,
            "changed": {
                k: {"old": ov, "new": nv}
                for k, (ov, nv) in diff.changed.items()
            },
            "added": diff.added,
            "removed": diff.removed,
        })

    return {
        "suite_config_diff": {
            "common_suites_count": len(report.common_suites),
            "suites_with_changes_count": len(report.suites_with_changes),
            "skipped_suites": report.skipped_suites,
            "diffs": diffs,
        }
    }
