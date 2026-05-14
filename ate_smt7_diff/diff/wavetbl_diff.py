#!/usr/bin/env python3
"""Wavetable diff algorithms for WAVETBL block comparison."""

from ate_smt7_diff.models import (
    WaveTblBlock,
    WaveTblDiff,
    WaveTblPinsGroup,
    WaveTblPinsGroupDiff,
)


def diff_wavetbl_pins_group(
    old_group: WaveTblPinsGroup,
    new_group: WaveTblPinsGroup,
) -> WaveTblPinsGroupDiff | None:
    """Compute differences between two WAVETBL PINS groups."""
    old_rows = {r.label: r for r in old_group.rows}
    new_rows = {r.label: r for r in new_group.rows}

    old_labels = set(old_rows.keys())
    new_labels = set(new_rows.keys())

    rows_added = tuple(new_rows[k] for k in new_labels - old_labels)
    rows_removed = tuple(old_rows[k] for k in old_labels - new_labels)
    rows_changed = tuple(
        (old_rows[k], new_rows[k]) for k in old_labels & new_labels if old_rows[k] != new_rows[k]
    )

    brk_changed = old_group.brk != new_group.brk
    f_changed = old_group.f != new_group.f

    if (
        not rows_added
        and not rows_removed
        and not rows_changed
        and not brk_changed
        and not f_changed
    ):
        return None

    return WaveTblPinsGroupDiff(
        pins_name=old_group.pins_name or new_group.pins_name,
        rows_added=rows_added,
        rows_removed=rows_removed,
        rows_changed=rows_changed,
        brk_old=old_group.brk,
        brk_new=new_group.brk,
        f_old=old_group.f,
        f_new=new_group.f,
    )


def diff_wavetbl_blocks(
    suite_name: str,
    wavetbl_name: str,
    old_block: WaveTblBlock | None,
    new_block: WaveTblBlock | None,
) -> WaveTblDiff | None:
    """Compute differences between two WAVETBL blocks."""
    if old_block is None and new_block is None:
        return None

    if old_block is None:
        return WaveTblDiff(
            suite_name=suite_name,
            wavetbl_name=wavetbl_name,
            new_block=new_block,
        )

    if new_block is None:
        return WaveTblDiff(
            suite_name=suite_name,
            wavetbl_name=wavetbl_name,
            old_block=old_block,
        )

    old_keys = set(old_block.pins_groups.keys())
    new_keys = set(new_block.pins_groups.keys())

    pins_groups_added = {k: new_block.pins_groups[k] for k in new_keys - old_keys}
    pins_groups_removed = {k: old_block.pins_groups[k] for k in old_keys - new_keys}
    pins_groups_changed = {}

    for k in old_keys & new_keys:
        pg_diff = diff_wavetbl_pins_group(
            old_block.pins_groups[k],
            new_block.pins_groups[k],
        )
        if pg_diff is not None:
            pins_groups_changed[k] = pg_diff

    if not pins_groups_added and not pins_groups_removed and not pins_groups_changed:
        return None

    return WaveTblDiff(
        suite_name=suite_name,
        wavetbl_name=wavetbl_name,
        pins_groups_added=pins_groups_added,
        pins_groups_removed=pins_groups_removed,
        pins_groups_changed=pins_groups_changed,
    )


def diff_wavetbls(
    suite_name: str,
    old_blocks: dict[str, WaveTblBlock],
    new_blocks: dict[str, WaveTblBlock],
) -> list[WaveTblDiff]:
    """Compute differences across all WAVETBL blocks for a suite.

    Added and removed blocks are first compared by pins_groups keys.
    When an added block and a removed block share the exact same set
    of pins group names, they are reported as a replacement
    (replaced_from) rather than separate add/remove entries.

    If after exact-key matching exactly one added and one removed
    block remain unmatched, they are paired as a replacement
    regardless of content differences (fallback heuristic).
    """
    all_names = set(old_blocks.keys()) | set(new_blocks.keys())
    result: list[WaveTblDiff] = []
    added_diffs: list[WaveTblDiff] = []
    removed_diffs: list[WaveTblDiff] = []

    for name in sorted(all_names):
        diff = diff_wavetbl_blocks(
            suite_name=suite_name,
            wavetbl_name=name,
            old_block=old_blocks.get(name),
            new_block=new_blocks.get(name),
        )
        if diff is None:
            continue
        if diff.new_block and not diff.old_block:
            added_diffs.append(diff)
        elif diff.old_block and not diff.new_block:
            removed_diffs.append(diff)
        else:
            result.append(diff)

    matched_added_ids: set[int] = set()
    matched_removed_ids: set[int] = set()

    # Step 1: Exact match by pins_groups keys
    for a_diff in added_diffs:
        a_keys = set(a_diff.new_block.pins_groups.keys()) if a_diff.new_block else set()
        for r_diff in removed_diffs:
            if id(r_diff) in matched_removed_ids:
                continue
            r_keys = set(r_diff.old_block.pins_groups.keys()) if r_diff.old_block else set()
            if a_keys and a_keys == r_keys:
                result.append(
                    WaveTblDiff(
                        suite_name=suite_name,
                        wavetbl_name=a_diff.wavetbl_name,
                        new_block=a_diff.new_block,
                        replaced_from=r_diff.wavetbl_name,
                    )
                )
                matched_added_ids.add(id(a_diff))
                matched_removed_ids.add(id(r_diff))
                break

    remaining_added = [d for d in added_diffs if id(d) not in matched_added_ids]
    remaining_removed = [d for d in removed_diffs if id(d) not in matched_removed_ids]

    # Step 2: Fallback - if exactly one unmatched added and one unmatched removed,
    # pair them as replacement regardless of content differences.
    if len(remaining_added) == 1 and len(remaining_removed) == 1:
        a_diff = remaining_added[0]
        r_diff = remaining_removed[0]
        result.append(
            WaveTblDiff(
                suite_name=suite_name,
                wavetbl_name=a_diff.wavetbl_name,
                new_block=a_diff.new_block,
                replaced_from=r_diff.wavetbl_name,
            )
        )
        remaining_added = []
        remaining_removed = []

    result.extend(remaining_added)
    result.extend(remaining_removed)
    return result
