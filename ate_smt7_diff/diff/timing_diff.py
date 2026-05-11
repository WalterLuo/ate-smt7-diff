#!/usr/bin/env python3
"""
Timing spec diff algorithms.
"""

from typing import Dict, List, Optional, Tuple

from ate_smt7_diff.models import (
    TimingEqnSetBlock,
    TimingEqnSetDiff,
    TimingPinConfig,
    TimingSetConfig,
    TimingSpec,
    TimingSpecDiff,
    WaveTblBlock,
    WaveTblDiff,
    WaveTblPinsGroup,
    WaveTblPinsGroupDiff,
    WaveTblRow,
)


def diff_timing_specs(
    suite_name: str,
    spec_type: str,
    spec_name: str,
    old_specs: Optional[Dict[str, TimingSpec]],
    new_specs: Optional[Dict[str, TimingSpec]],
) -> Optional[TimingSpecDiff]:
    """Compute timing spec differences between two spec dictionaries."""
    if old_specs is None and new_specs is None:
        return None

    if old_specs is None:
        return TimingSpecDiff(
            suite_name=suite_name,
            spec_type=spec_type,
            spec_name=spec_name,
            added=new_specs or {},
        )

    if new_specs is None:
        return TimingSpecDiff(
            suite_name=suite_name,
            spec_type=spec_type,
            spec_name=spec_name,
            removed=old_specs,
        )

    old_keys = set(old_specs.keys())
    new_keys = set(new_specs.keys())

    added = {k: new_specs[k] for k in new_keys - old_keys}
    removed = {k: old_specs[k] for k in old_keys - new_keys}
    changed = {}
    for k in old_keys & new_keys:
        old_s = old_specs[k]
        new_s = new_specs[k]
        if (
            old_s.value != new_s.value
            or old_s.units != new_s.units
            or old_s.comment != new_s.comment
        ):
            changed[k] = (old_s, new_s)

    if not added and not removed and not changed:
        return None

    return TimingSpecDiff(
        suite_name=suite_name,
        spec_type=spec_type,
        spec_name=spec_name,
        added=added,
        removed=removed,
        changed=changed,
    )


def diff_timing_eqnset_blocks(
    suite_name: str,
    old_block: Optional[TimingEqnSetBlock],
    new_block: Optional[TimingEqnSetBlock],
) -> Optional[TimingSpecDiff]:
    """Compute EQSP TIM,SPS block differences between two program versions."""
    if old_block is None and new_block is None:
        return None

    spec_name = ""
    if old_block:
        spec_name = old_block.eqnset_name
    elif new_block:
        spec_name = new_block.eqnset_name

    return diff_timing_specs(
        suite_name=suite_name,
        spec_type="regular",
        spec_name=spec_name,
        old_specs=old_block.specs if old_block else None,
        new_specs=new_block.specs if new_block else None,
    )


def _diff_pins_group(
    old_pins: Dict[str, TimingPinConfig],
    new_pins: Dict[str, TimingPinConfig],
) -> Dict[str, Tuple[TimingPinConfig, TimingPinConfig]]:
    """Compare PINS groups within EQNSET blocks."""
    return {
        name: (old_pins[name], new_pins[name])
        for name in set(old_pins.keys()) & set(new_pins.keys())
        if old_pins[name] != new_pins[name]
    }


def _diff_timingsets(
    old_ts: Dict[int, TimingSetConfig],
    new_ts: Dict[int, TimingSetConfig],
) -> Dict[int, Tuple[TimingSetConfig, TimingSetConfig]]:
    """Compare TIMINGSET entries within EQNSET blocks."""
    return {
        idx: (old_ts[idx], new_ts[idx])
        for idx in set(old_ts.keys()) & set(new_ts.keys())
        if old_ts[idx] != new_ts[idx]
    }


def diff_timing_eqnset_blocks_full(
    suite_name: str,
    old_block: Optional[TimingEqnSetBlock],
    new_block: Optional[TimingEqnSetBlock],
) -> Optional[TimingEqnSetDiff]:
    """Compute full EQNSET block differences including pins and timingsets."""
    if old_block is None and new_block is None:
        return None

    eqnset_index = old_block.eqnset_index if old_block else (new_block.eqnset_index if new_block else 0)
    eqnset_name = old_block.eqnset_name if old_block else (new_block.eqnset_name if new_block else "")

    if old_block is None:
        return TimingEqnSetDiff(
            suite_name=suite_name,
            eqnset_index=eqnset_index,
            eqnset_name=eqnset_name,
            specs_added=new_block.specs if new_block else {},
            pins_added=new_block.pins_groups if new_block else {},
            timingsets_added=new_block.timingsets if new_block else {},
        )

    if new_block is None:
        return TimingEqnSetDiff(
            suite_name=suite_name,
            eqnset_index=eqnset_index,
            eqnset_name=eqnset_name,
            specs_removed=old_block.specs,
            pins_removed=old_block.pins_groups,
            timingsets_removed=old_block.timingsets,
        )

    # SPECS diff
    old_spec_keys = set(old_block.specs.keys())
    new_spec_keys = set(new_block.specs.keys())
    specs_added = {k: new_block.specs[k] for k in new_spec_keys - old_spec_keys}
    specs_removed = {k: old_block.specs[k] for k in old_spec_keys - new_spec_keys}
    specs_changed = {}
    for k in old_spec_keys & new_spec_keys:
        old_s = old_block.specs[k]
        new_s = new_block.specs[k]
        if (
            old_s.value != new_s.value
            or old_s.units != new_s.units
            or old_s.comment != new_s.comment
        ):
            specs_changed[k] = (old_s, new_s)

    # PINS diff
    old_pin_keys = set(old_block.pins_groups.keys())
    new_pin_keys = set(new_block.pins_groups.keys())
    pins_added = {k: new_block.pins_groups[k] for k in new_pin_keys - old_pin_keys}
    pins_removed = {k: old_block.pins_groups[k] for k in old_pin_keys - new_pin_keys}
    pins_changed = _diff_pins_group(old_block.pins_groups, new_block.pins_groups)

    # TIMINGSET diff
    old_ts_keys = set(old_block.timingsets.keys())
    new_ts_keys = set(new_block.timingsets.keys())
    timingsets_added = {k: new_block.timingsets[k] for k in new_ts_keys - old_ts_keys}
    timingsets_removed = {k: old_block.timingsets[k] for k in old_ts_keys - new_ts_keys}
    timingsets_changed = _diff_timingsets(old_block.timingsets, new_block.timingsets)

    if not (
        specs_added or specs_removed or specs_changed
        or pins_added or pins_removed or pins_changed
        or timingsets_added or timingsets_removed or timingsets_changed
    ):
        return None

    return TimingEqnSetDiff(
        suite_name=suite_name,
        eqnset_index=eqnset_index,
        eqnset_name=eqnset_name,
        specs_added=specs_added,
        specs_removed=specs_removed,
        specs_changed=specs_changed,
        pins_added=pins_added,
        pins_removed=pins_removed,
        pins_changed=pins_changed,
        timingsets_added=timingsets_added,
        timingsets_removed=timingsets_removed,
        timingsets_changed=timingsets_changed,
    )


def diff_wavetbl_pins_group(
    old_group: WaveTblPinsGroup,
    new_group: WaveTblPinsGroup,
) -> Optional[WaveTblPinsGroupDiff]:
    """Compute differences between two WAVETBL PINS groups."""
    old_rows = {r.label: r for r in old_group.rows}
    new_rows = {r.label: r for r in new_group.rows}

    old_labels = set(old_rows.keys())
    new_labels = set(new_rows.keys())

    rows_added = tuple(new_rows[k] for k in new_labels - old_labels)
    rows_removed = tuple(old_rows[k] for k in old_labels - new_labels)
    rows_changed = tuple(
        (old_rows[k], new_rows[k])
        for k in old_labels & new_labels
        if old_rows[k] != new_rows[k]
    )

    brk_changed = old_group.brk != new_group.brk
    f_changed = old_group.f != new_group.f

    if not rows_added and not rows_removed and not rows_changed and not brk_changed and not f_changed:
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
    old_block: Optional[WaveTblBlock],
    new_block: Optional[WaveTblBlock],
) -> Optional[WaveTblDiff]:
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
    old_blocks: Dict[str, WaveTblBlock],
    new_blocks: Dict[str, WaveTblBlock],
) -> List[WaveTblDiff]:
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
    result: List[WaveTblDiff] = []
    added_diffs: List[WaveTblDiff] = []
    removed_diffs: List[WaveTblDiff] = []

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

    matched_added_ids: Set[int] = set()
    matched_removed_ids: Set[int] = set()

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
