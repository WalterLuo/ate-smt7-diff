#!/usr/bin/env python3
"""Full EQNSET block diff including PINS groups and TIMINGSET entries."""

from ate_smt7_diff.diff.utils import diff_dicts
from ate_smt7_diff.models import (
    TimingEqnSetBlock,
    TimingEqnSetDiff,
    TimingPinConfig,
    TimingSetConfig,
)


def _diff_pins_group(
    old_pins: dict[str, TimingPinConfig],
    new_pins: dict[str, TimingPinConfig],
) -> dict[str, tuple[TimingPinConfig, TimingPinConfig]]:
    """Compare PINS groups within EQNSET blocks."""
    return {
        name: (old_pins[name], new_pins[name])
        for name in set(old_pins.keys()) & set(new_pins.keys())
        if old_pins[name] != new_pins[name]
    }


def _diff_timingsets(
    old_ts: dict[int, TimingSetConfig],
    new_ts: dict[int, TimingSetConfig],
) -> dict[int, tuple[TimingSetConfig, TimingSetConfig]]:
    """Compare TIMINGSET entries within EQNSET blocks."""
    return {
        idx: (old_ts[idx], new_ts[idx])
        for idx in set(old_ts.keys()) & set(new_ts.keys())
        if old_ts[idx] != new_ts[idx]
    }


def diff_timing_eqnset_blocks_full(
    suite_name: str,
    old_block: TimingEqnSetBlock | None,
    new_block: TimingEqnSetBlock | None,
) -> TimingEqnSetDiff | None:
    """Compute full EQNSET block differences including pins and timingsets."""
    if old_block is None and new_block is None:
        return None

    eqnset_index = (
        old_block.eqnset_index if old_block else (new_block.eqnset_index if new_block else 0)
    )
    eqnset_name = (
        old_block.eqnset_name if old_block else (new_block.eqnset_name if new_block else "")
    )

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
    specs_result = diff_dicts(
        old_block.specs,
        new_block.specs,
        compare=lambda a, b: (
            a.value == b.value and a.units == b.units and a.comment == b.comment
        ),
    )
    specs_added, specs_removed, specs_changed = specs_result or ({}, {}, {})

    # PINS diff
    pins_added, pins_removed, pins_changed = diff_dicts(
        old_block.pins_groups, new_block.pins_groups
    ) or ({}, {}, {})

    # TIMINGSET diff
    timingsets_added, timingsets_removed, timingsets_changed = diff_dicts(
        old_block.timingsets, new_block.timingsets
    ) or ({}, {}, {})

    if not (
        specs_added
        or specs_removed
        or specs_changed
        or pins_added
        or pins_removed
        or pins_changed
        or timingsets_added
        or timingsets_removed
        or timingsets_changed
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
