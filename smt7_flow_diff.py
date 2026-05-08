#!/usr/bin/env python3
"""
MVP: SMT7 Flow Diff Engine
Parses test_flow sections and computes test sequence differences.
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from enum import Enum, auto
from functools import cached_property
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from program_loader import (
    LevelSpecDiff,
    SuiteConfigView,
    build_suite_views,
    diff_level_specs,
)
from suite_config import (
    SuiteConfigReport,
    diff_suite_configs,
    format_suite_console,
    format_suite_markdown,
    format_suite_json,
)


class DiffType(Enum):
    ADDED = auto()
    REMOVED = auto()
    MOVED = auto()
    UNCHANGED = auto()


@dataclass(frozen=True)
class TestItem:
    """A single test execution in the flow."""
    suite_name: str
    group_path: Tuple[str, ...]
    line_number: int
    is_branch: bool


@dataclass(frozen=True)
class FlowDiff:
    """Difference result for a single test occurrence."""
    suite_name: str
    diff_type: DiffType
    old_index: Optional[int]
    new_index: Optional[int]
    old_group_path: Tuple[str, ...]
    new_group_path: Tuple[str, ...]


@dataclass
class DiffReport:
    """Complete diff report between two flows."""
    old_file: str
    new_file: str
    old_tests: List[TestItem]
    new_tests: List[TestItem]
    diffs: List[FlowDiff]
    suite_config_report: Optional[SuiteConfigReport] = None
    old_suite_views: Optional[Dict[str, SuiteConfigView]] = None
    new_suite_views: Optional[Dict[str, SuiteConfigView]] = None
    level_spec_diffs: Optional[List[LevelSpecDiff]] = None

    @cached_property
    def added(self) -> List[str]:
        return sorted({d.suite_name for d in self.diffs if d.diff_type == DiffType.ADDED})

    @cached_property
    def removed(self) -> List[str]:
        return sorted({d.suite_name for d in self.diffs if d.diff_type == DiffType.REMOVED})

    @cached_property
    def moved(self) -> List[str]:
        return sorted({d.suite_name for d in self.diffs if d.diff_type == DiffType.MOVED})

    @cached_property
    def unchanged(self) -> List[str]:
        return sorted({d.suite_name for d in self.diffs if d.diff_type == DiffType.UNCHANGED})

    @cached_property
    def order_changed(self) -> List[str]:
        """Tests whose relative order to other common tests actually changed."""
        return compute_order_changes(self.old_tests, self.new_tests)


def extract_test_flow_section(lines: List[str]) -> List[str]:
    """Extract lines between 'test_flow' and its matching 'end'."""
    in_test_flow = False
    test_flow_lines = []

    for line in lines:
        stripped = line.strip()

        if stripped == "test_flow":
            in_test_flow = True
            continue

        if in_test_flow:
            if stripped == "end":
                break
            test_flow_lines.append(line)

    return test_flow_lines


# Module-level compiled regex patterns for parsing test_flow
_RUN_RE = re.compile(r'^\s*run\(\s*([^)]+?)\s*\)\s*;\s*$')
_RUN_BRANCH_RE = re.compile(r'^\s*run_and_branch\(\s*([^)]+?)\s*\)\s*$')
_GROUP_END_RE = re.compile(
    r'^\s*}\s*,\s*(open|close|groupbypass)\s*,\s*"((?:[^"\\]|\\.)*)"\s*$'
)


def parse_test_flow(lines: List[str]) -> List[TestItem]:
    """
    Parse test_flow lines into a flat list of TestItems.

    Handles:
      - run(SuiteName);
      - run_and_branch(SuiteName)
      - { ... }, open,"GroupName", ""
      - { ... }, close,"GroupName", ""
    """
    result: List[TestItem] = []
    group_stack: List[str] = []
    i = 0

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Skip empty lines and comments
        if not stripped or stripped.startswith('//'):
            i += 1
            continue

        # run(SuiteName);
        match = _RUN_RE.match(line)
        if match:
            suite_name = match.group(1).strip()
            result.append(TestItem(
                suite_name=suite_name,
                group_path=tuple(group_stack),
                line_number=i + 1,
                is_branch=False
            ))
            i += 1
            continue

        # run_and_branch(SuiteName)
        match = _RUN_BRANCH_RE.match(line)
        if match:
            suite_name = match.group(1).strip()
            result.append(TestItem(
                suite_name=suite_name,
                group_path=tuple(group_stack),
                line_number=i + 1,
                is_branch=True
            ))
            i += 1
            continue

        # Group end: }, open,"Name", "" or }, close,"Name", ""
        match = _GROUP_END_RE.match(line)
        if match:
            group_type = match.group(1)
            group_name = match.group(2)
            if group_type == "open":
                group_stack.append(group_name)
            elif group_type == "close":
                if group_stack and group_stack[-1] == group_name:
                    group_stack.pop()
                elif group_name in group_stack:
                    while group_stack and group_stack[-1] != group_name:
                        group_stack.pop()
                    if group_stack:
                        group_stack.pop()
            elif group_type == "groupbypass":
                pass  # groupbypass does not affect group stack
            i += 1
            continue

        # Group start: {
        if stripped == '{':
            i += 1
            continue

        # Ignore other statements (multi_bin, stop_bin, etc.)
        i += 1

    return result


def compute_diff(old_tests: List[TestItem], new_tests: List[TestItem]) -> List[FlowDiff]:
    """Compute LCS-based diff between two test sequences."""
    old_names = [t.suite_name for t in old_tests]
    new_names = [t.suite_name for t in new_tests]

    matcher = SequenceMatcher(None, old_names, new_names)
    diffs: List[FlowDiff] = []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'equal':
            for offset in range(j2 - j1):
                idx_old = i1 + offset
                idx_new = j1 + offset
                diffs.append(FlowDiff(
                    suite_name=new_names[idx_new],
                    diff_type=DiffType.UNCHANGED,
                    old_index=idx_old,
                    new_index=idx_new,
                    old_group_path=old_tests[idx_old].group_path,
                    new_group_path=new_tests[idx_new].group_path,
                ))
        elif tag == 'replace':
            for offset in range(i2 - i1):
                diffs.append(FlowDiff(
                    suite_name=old_names[i1 + offset],
                    diff_type=DiffType.REMOVED,
                    old_index=i1 + offset,
                    new_index=None,
                    old_group_path=old_tests[i1 + offset].group_path,
                    new_group_path=(),
                ))
            for offset in range(j2 - j1):
                diffs.append(FlowDiff(
                    suite_name=new_names[j1 + offset],
                    diff_type=DiffType.ADDED,
                    old_index=None,
                    new_index=j1 + offset,
                    old_group_path=(),
                    new_group_path=new_tests[j1 + offset].group_path,
                ))
        elif tag == 'delete':
            for offset in range(i2 - i1):
                diffs.append(FlowDiff(
                    suite_name=old_names[i1 + offset],
                    diff_type=DiffType.REMOVED,
                    old_index=i1 + offset,
                    new_index=None,
                    old_group_path=old_tests[i1 + offset].group_path,
                    new_group_path=(),
                ))
        elif tag == 'insert':
            for offset in range(j2 - j1):
                diffs.append(FlowDiff(
                    suite_name=new_names[j1 + offset],
                    diff_type=DiffType.ADDED,
                    old_index=None,
                    new_index=j1 + offset,
                    old_group_path=(),
                    new_group_path=new_tests[j1 + offset].group_path,
                ))

    return diffs


def detect_moves(diffs: List[FlowDiff]) -> List[FlowDiff]:
    """Post-process: reclassify ADDED+REMOVED pairs as MOVED."""
    removed = [(i, d) for i, d in enumerate(diffs) if d.diff_type == DiffType.REMOVED]
    added = [(i, d) for i, d in enumerate(diffs) if d.diff_type == DiffType.ADDED]

    removed_by_name: Dict[str, List[Tuple[int, FlowDiff]]] = {}
    for idx, d in removed:
        removed_by_name.setdefault(d.suite_name, []).append((idx, d))

    added_by_name: Dict[str, List[Tuple[int, FlowDiff]]] = {}
    for idx, d in added:
        added_by_name.setdefault(d.suite_name, []).append((idx, d))

    consumed_removed: Set[int] = set()
    consumed_added: Set[int] = set()
    move_diffs: List[FlowDiff] = []

    for name in set(removed_by_name.keys()) & set(added_by_name.keys()):
        old_entries = removed_by_name[name]
        new_entries = added_by_name[name]

        # Greedy pairing
        count = min(len(old_entries), len(new_entries))
        for k in range(count):
            old_idx, old_d = old_entries[k]
            new_idx, new_d = new_entries[k]
            consumed_removed.add(old_idx)
            consumed_added.add(new_idx)

            move_diffs.append(FlowDiff(
                suite_name=name,
                diff_type=DiffType.MOVED,
                old_index=old_d.old_index,
                new_index=new_d.new_index,
                old_group_path=old_d.old_group_path,
                new_group_path=new_d.new_group_path,
            ))

    # Add remaining unconsumed diffs
    final_diffs = move_diffs[:]
    for idx, d in enumerate(diffs):
        if d.diff_type == DiffType.REMOVED and idx in consumed_removed:
            continue
        if d.diff_type == DiffType.ADDED and idx in consumed_added:
            continue
        final_diffs.append(d)

    # Sort by new_index (None at end), then by old_index
    final_diffs.sort(key=lambda d: (
        (0, d.new_index) if d.new_index is not None else (1, 0),
        (0, d.old_index) if d.old_index is not None else (1, 0),
    ))

    return final_diffs


def detect_swaps(diffs: List[FlowDiff]) -> List[FlowDiff]:
    """
    Detect adjacent swaps: two tests adjacent in old but reversed in new.
    Reclassify any UNCHANGED tests involved in a swap as MOVED.
    """
    # Map old_index -> (diff_index, diff) for tests present in both files
    aligned_by_old: Dict[int, Tuple[int, FlowDiff]] = {}
    for idx, d in enumerate(diffs):
        if d.old_index is not None and d.new_index is not None:
            aligned_by_old[d.old_index] = (idx, d)

    old_indices = sorted(aligned_by_old.keys())

    # Find adjacent pairs that are reversed in new
    to_reclassify: Set[int] = set()
    for i in range(len(old_indices) - 1):
        idx_a = old_indices[i]
        idx_b = old_indices[i + 1]
        # Must be adjacent in old
        if idx_b != idx_a + 1:
            continue

        diff_idx_a, diff_a = aligned_by_old[idx_a]
        diff_idx_b, diff_b = aligned_by_old[idx_b]

        # Check if reversed in new (adjacent and swapped)
        if (diff_a.new_index == diff_b.new_index + 1 and
                diff_b.new_index == diff_a.new_index - 1):
            if diff_a.diff_type == DiffType.UNCHANGED:
                to_reclassify.add(diff_idx_a)
            if diff_b.diff_type == DiffType.UNCHANGED:
                to_reclassify.add(diff_idx_b)

    if not to_reclassify:
        return diffs

    new_diffs: List[FlowDiff] = []
    for idx, d in enumerate(diffs):
        if idx in to_reclassify:
            new_diffs.append(FlowDiff(
                suite_name=d.suite_name,
                diff_type=DiffType.MOVED,
                old_index=d.old_index,
                new_index=d.new_index,
                old_group_path=d.old_group_path,
                new_group_path=d.new_group_path,
            ))
        else:
            new_diffs.append(d)

    return new_diffs


def compute_order_changes(old_tests: List[TestItem], new_tests: List[TestItem]) -> List[str]:
    """
    Detect tests whose relative order to other common tests actually changed.

    Uses pairwise inversion detection on first occurrences:
    - For each pair of common tests (t1, t2):
      - If t1 < t2 in old but t1 > t2 in new (or vice versa), both changed relative order.
    - Tests that only shift due to insertions/deletions of other tests are NOT flagged.

    Complexity: O(m^2) where m = number of unique common tests.
    For flows with thousands of unique common tests, this may become slow.
    Consider a Fenwick-tree-based O(m log m) approach if profiling shows a bottleneck.
    """
    # Build first-occurrence position maps
    old_first_pos: Dict[str, int] = {}
    for i, t in enumerate(old_tests):
        if t.suite_name not in old_first_pos:
            old_first_pos[t.suite_name] = i

    new_first_pos: Dict[str, int] = {}
    for i, t in enumerate(new_tests):
        if t.suite_name not in new_first_pos:
            new_first_pos[t.suite_name] = i

    # Get common tests sorted by old position for consistent ordering
    common = sorted(
        set(old_first_pos.keys()) & set(new_first_pos.keys()),
        key=lambda n: old_first_pos[n]
    )

    order_changed: Set[str] = set()
    for i in range(len(common)):
        for j in range(i + 1, len(common)):
            name_a, name_b = common[i], common[j]
            old_a, old_b = old_first_pos[name_a], old_first_pos[name_b]
            new_a, new_b = new_first_pos[name_a], new_first_pos[name_b]
            if (old_a < old_b) != (new_a < new_b):
                order_changed.add(name_a)
                order_changed.add(name_b)

    return sorted(order_changed)


def diff_flow_files(
    old_path: str,
    new_path: str,
    include_suite_diff: bool = False,
    include_config_views: bool = False,
) -> DiffReport:
    """Main entry: parse two flow files and compute diff."""
    try:
        old_lines = Path(old_path).read_text(encoding="utf-8").splitlines()
        new_lines = Path(new_path).read_text(encoding="utf-8").splitlines()
    except FileNotFoundError as e:
        raise FileNotFoundError(f"Flow file not found: {e.filename}") from e
    except PermissionError as e:
        raise PermissionError(f"Permission denied reading flow file: {e.filename}") from e
    except UnicodeDecodeError as e:
        raise ValueError(f"File encoding error (expected UTF-8): {e}") from e

    old_tf = extract_test_flow_section(old_lines)
    new_tf = extract_test_flow_section(new_lines)

    old_tests = parse_test_flow(old_tf)
    new_tests = parse_test_flow(new_tf)

    diffs = compute_diff(old_tests, new_tests)
    diffs = detect_moves(diffs)
    diffs = detect_swaps(diffs)

    suite_report: Optional[SuiteConfigReport] = None
    if include_suite_diff:
        old_names = {t.suite_name for t in old_tests}
        new_names = {t.suite_name for t in new_tests}
        common_suites = old_names & new_names
        suite_report = diff_suite_configs(old_path, new_path, common_suites)

    old_views: Optional[Dict[str, SuiteConfigView]] = None
    new_views: Optional[Dict[str, SuiteConfigView]] = None
    level_spec_diffs: Optional[List[LevelSpecDiff]] = None
    if include_config_views:
        old_names = {t.suite_name for t in old_tests}
        new_names = {t.suite_name for t in new_tests}
        common_suites = old_names & new_names
        old_views = build_suite_views(old_path, common_suites)
        new_views = build_suite_views(new_path, common_suites)

        level_spec_diffs = []
        for suite_name in sorted(common_suites):
            old_v = old_views.get(suite_name)
            new_v = new_views.get(suite_name)
            if old_v and new_v:
                diff = diff_level_specs(suite_name, old_v.level_specs, new_v.level_specs)
                if diff and diff.has_changes:
                    level_spec_diffs.append(diff)
        if not level_spec_diffs:
            level_spec_diffs = None

    return DiffReport(
        old_file=old_path,
        new_file=new_path,
        old_tests=old_tests,
        new_tests=new_tests,
        diffs=diffs,
        suite_config_report=suite_report,
        old_suite_views=old_views,
        new_suite_views=new_views,
        level_spec_diffs=level_spec_diffs,
    )


def format_console(report: DiffReport) -> str:
    """Format diff report as colored console output."""
    lines = []
    lines.append("=" * 60)
    lines.append("SMT7 Flow Diff Report")
    lines.append("=" * 60)
    lines.append(f"Old: {report.old_file} ({len(report.old_tests)} tests)")
    lines.append(f"New: {report.new_file} ({len(report.new_tests)} tests)")
    lines.append("")

    if report.added:
        lines.append(f"Added Tests ({len(report.added)}):")
        for name in report.added:
            lines.append(f"  + {name}")
        lines.append("")

    if report.removed:
        lines.append(f"Removed Tests ({len(report.removed)}):")
        for name in report.removed:
            lines.append(f"  - {name}")
        lines.append("")

    if report.moved:
        lines.append(f"Moved Tests ({len(report.moved)}):")
        for name in report.moved:
            # Find the diff entries for this move
            entries = [d for d in report.diffs if d.suite_name == name and d.diff_type == DiffType.MOVED]
            for d in entries:
                old_pos = d.old_index + 1 if d.old_index is not None else '?'
                new_pos = d.new_index + 1 if d.new_index is not None else '?'
                old_grp = ' / '.join(d.old_group_path) if d.old_group_path else '(root)'
                new_grp = ' / '.join(d.new_group_path) if d.new_group_path else '(root)'
                move_info = f"    pos {old_pos} -> {new_pos}"
                if old_grp != new_grp:
                    move_info += f", group [{old_grp}] -> [{new_grp}]"
                lines.append(f"  ~ {name}{move_info}")
        lines.append("")

    if report.order_changed:
        lines.append(f"Order Changed Tests ({len(report.order_changed)}):")
        for name in report.order_changed:
            lines.append(f"  * {name}")
        lines.append("")

    unchanged_count = len(report.unchanged)
    lines.append(f"Unchanged Tests: {unchanged_count}")
    lines.append("")

    # Sequence diff detail
    lines.append("Sequence Diff Detail:")
    lines.append("-" * 60)
    for d in report.diffs:
        if d.diff_type == DiffType.UNCHANGED:
            continue
        symbol = {DiffType.ADDED: "+", DiffType.REMOVED: "-", DiffType.MOVED: "~"}.get(d.diff_type, "?")
        pos_info = ""
        if d.old_index is not None:
            pos_info += f" [old:{d.old_index + 1}]"
        if d.new_index is not None:
            pos_info += f" [new:{d.new_index + 1}]"
        grp = ""
        if d.new_group_path:
            grp = f" (in: {' / '.join(d.new_group_path)})"
        elif d.old_group_path:
            grp = f" (was in: {' / '.join(d.old_group_path)})"
        lines.append(f"  {symbol} {d.suite_name}{pos_info}{grp}")

    if report.suite_config_report is not None:
        lines.append("")
        lines.append(format_suite_console(report.suite_config_report))

    if report.old_suite_views is not None and report.new_suite_views is not None:
        lines.append("")
        lines.append("=" * 60)
        lines.append("Associated Config Views")
        lines.append("=" * 60)
        common = sorted(
            set(report.old_suite_views.keys()) & set(report.new_suite_views.keys())
        )
        # Build lookup for level spec diffs
        spec_diff_by_suite: Dict[str, LevelSpecDiff] = {}
        if report.level_spec_diffs:
            for diff in report.level_spec_diffs:
                spec_diff_by_suite[diff.suite_name] = diff
        for suite_name in common:
            old_v = report.old_suite_views[suite_name]
            new_v = report.new_suite_views[suite_name]
            lines.append(f"{suite_name}:")
            if old_v.timing_spec_set or new_v.timing_spec_set:
                old_t = old_v.timing_spec_set or "-"
                new_t = new_v.timing_spec_set or "-"
                marker = "  " if old_t == new_t else "* "
                lines.append(f"  {marker}timing spec: {old_t} -> {new_t}")
            if old_v.level_eqn_set is not None or new_v.level_eqn_set is not None:
                old_e = old_v.level_eqn_set if old_v.level_eqn_set is not None else "-"
                new_e = new_v.level_eqn_set if new_v.level_eqn_set is not None else "-"
                marker = "  " if old_e == new_e else "* "
                lines.append(f"  {marker}level EQNSET: {old_e} -> {new_e}")
            if old_v.level_spec_set is not None or new_v.level_spec_set is not None:
                old_s = old_v.level_spec_set if old_v.level_spec_set is not None else "-"
                new_s = new_v.level_spec_set if new_v.level_spec_set is not None else "-"
                marker = "  " if old_s == new_s else "* "
                lines.append(f"  {marker}level SPECSET: {old_s} -> {new_s}")
            if suite_name in spec_diff_by_suite:
                diff = spec_diff_by_suite[suite_name]
                lines.append("  * level spec changes:")
                for name, spec in diff.added.items():
                    lines.append(f"    + {name}: actual={spec.actual}, units={spec.units}")
                for name, spec in diff.removed.items():
                    lines.append(f"    - {name}: actual={spec.actual}, units={spec.units}")
                for name, (old_s, new_s) in diff.changed.items():
                    changes = []
                    if old_s.actual != new_s.actual:
                        changes.append(f"actual {old_s.actual} -> {new_s.actual}")
                    if old_s.min != new_s.min:
                        changes.append(f"min {old_s.min} -> {new_s.min}")
                    if old_s.max != new_s.max:
                        changes.append(f"max {old_s.max} -> {new_s.max}")
                    if old_s.units != new_s.units:
                        changes.append(f"units {old_s.units} -> {new_s.units}")
                    if old_s.comment != new_s.comment:
                        changes.append(f"comment {old_s.comment} -> {new_s.comment}")
                    lines.append(f"    ~ {name}: {', '.join(changes)}")

    return "\n".join(lines)


def format_markdown(report: DiffReport) -> str:
    """Format diff report as Markdown."""
    lines = []
    lines.append("# SMT7 Flow Diff Report")
    lines.append("")
    lines.append(f"- **Old**: `{report.old_file}` ({len(report.old_tests)} tests)")
    lines.append(f"- **New**: `{report.new_file}` ({len(report.new_tests)} tests)")
    lines.append("")

    if report.added:
        lines.append(f"## Added Tests ({len(report.added)})")
        for name in report.added:
            lines.append(f"- **{name}**")
        lines.append("")

    if report.removed:
        lines.append(f"## Removed Tests ({len(report.removed)})")
        for name in report.removed:
            lines.append(f"- ~~{name}~~")
        lines.append("")

    if report.moved:
        lines.append(f"## Moved Tests ({len(report.moved)})")
        for name in report.moved:
            entries = [d for d in report.diffs if d.suite_name == name and d.diff_type == DiffType.MOVED]
            for d in entries:
                old_pos = d.old_index + 1 if d.old_index is not None else '?'
                new_pos = d.new_index + 1 if d.new_index is not None else '?'
                lines.append(f"- **{name}**: position {old_pos} → {new_pos}")
        lines.append("")

    if report.order_changed:
        lines.append(f"## Order Changed Tests ({len(report.order_changed)})")
        for name in report.order_changed:
            lines.append(f"- **{name}**")
        lines.append("")

    unchanged_count = len(report.unchanged)
    lines.append(f"## Unchanged Tests: {unchanged_count}")
    lines.append("")

    # Summary table
    lines.append("## Summary")
    lines.append("| Metric | Count |")
    lines.append("|--------|-------|")
    lines.append(f"| Total Old Tests | {len(report.old_tests)} |")
    lines.append(f"| Total New Tests | {len(report.new_tests)} |")
    lines.append(f"| Added | {len(report.added)} |")
    lines.append(f"| Removed | {len(report.removed)} |")
    lines.append(f"| Moved | {len(report.moved)} |")
    lines.append(f"| Order Changed | {len(report.order_changed)} |")
    lines.append(f"| Unchanged | {unchanged_count} |")

    if report.suite_config_report is not None:
        lines.append("")
        lines.append(format_suite_markdown(report.suite_config_report))

    if report.level_spec_diffs:
        lines.append("")
        lines.append("## Level Spec Diff")
        lines.append("")
        for diff in report.level_spec_diffs:
            lines.append(f"### {diff.suite_name}")
            if diff.added:
                lines.append("")
                lines.append("**Added:**")
                for name, spec in diff.added.items():
                    lines.append(f"- `{name}`: actual={spec.actual}, units={spec.units}")
            if diff.removed:
                lines.append("")
                lines.append("**Removed:**")
                for name, spec in diff.removed.items():
                    lines.append(f"- ~~`{name}`: actual={spec.actual}, units={spec.units}~~")
            if diff.changed:
                lines.append("")
                lines.append("**Changed:**")
                lines.append("| Spec | Field | Old | New |")
                lines.append("|------|-------|-----|-----|")
                for name, (old_s, new_s) in diff.changed.items():
                    if old_s.actual != new_s.actual:
                        lines.append(f"| `{name}` | actual | `{old_s.actual}` | `{new_s.actual}` |")
                    if old_s.min != new_s.min:
                        lines.append(f"| `{name}` | min | `{old_s.min}` | `{new_s.min}` |")
                    if old_s.max != new_s.max:
                        lines.append(f"| `{name}` | max | `{old_s.max}` | `{new_s.max}` |")
                    if old_s.units != new_s.units:
                        lines.append(f"| `{name}` | units | `{old_s.units}` | `{new_s.units}` |")
                    if old_s.comment != new_s.comment:
                        lines.append(f"| `{name}` | comment | `{old_s.comment}` | `{new_s.comment}` |")

    return "\n".join(lines)


def format_json(report: DiffReport) -> str:
    """Format diff report as strict JSON per user specification."""
    # Build order_changed entries with first matched occurrence positions
    order_changed_entries = []

    old_pos_map: Dict[str, List[int]] = {}
    for i, t in enumerate(report.old_tests):
        old_pos_map.setdefault(t.suite_name, []).append(i)

    new_pos_map: Dict[str, List[int]] = {}
    for i, t in enumerate(report.new_tests):
        new_pos_map.setdefault(t.suite_name, []).append(i)

    for name in report.order_changed:
        old_order = old_pos_map.get(name, [None])[0]
        new_order = new_pos_map.get(name, [None])[0]
        order_changed_entries.append({
            "test_name": name,
            "old_order": (old_order + 1) if old_order is not None else None,
            "new_order": (new_order + 1) if new_order is not None else None,
        })

    result = {
        "added_tests": report.added,
        "removed_tests": report.removed,
        "order_changed": order_changed_entries,
        "summary": {
            "added_count": len(report.added),
            "removed_count": len(report.removed),
            "order_changed_count": len(report.order_changed),
        }
    }

    if report.suite_config_report is not None:
        suite_json = format_suite_json(report.suite_config_report)
        result["suite_config_diff"] = suite_json["suite_config_diff"]

    if report.level_spec_diffs:
        result["level_spec_diff"] = [
            {
                "suite_name": diff.suite_name,
                "added": {
                    name: {
                        "actual": spec.actual,
                        "min": spec.min,
                        "max": spec.max,
                        "units": spec.units,
                        "comment": spec.comment,
                    }
                    for name, spec in diff.added.items()
                },
                "removed": {
                    name: {
                        "actual": spec.actual,
                        "min": spec.min,
                        "max": spec.max,
                        "units": spec.units,
                        "comment": spec.comment,
                    }
                    for name, spec in diff.removed.items()
                },
                "changed": {
                    name: {
                        "old": {
                            "actual": old_s.actual,
                            "min": old_s.min,
                            "max": old_s.max,
                            "units": old_s.units,
                            "comment": old_s.comment,
                        },
                        "new": {
                            "actual": new_s.actual,
                            "min": new_s.min,
                            "max": new_s.max,
                            "units": new_s.units,
                            "comment": new_s.comment,
                        },
                    }
                    for name, (old_s, new_s) in diff.changed.items()
                },
            }
            for diff in report.level_spec_diffs
        ]

    return json.dumps(result, indent=2, ensure_ascii=False)


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
