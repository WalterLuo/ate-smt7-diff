#!/usr/bin/env python3
"""
Flow diff algorithms: LCS-based sequence comparison,
move detection, swap detection, and order change detection.
"""

from difflib import SequenceMatcher
from typing import Dict, List, Set, Tuple

from ate_smt7_diff.models import DiffType, FlowDiff, TestItem


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
