#!/usr/bin/env python3
"""
Timing spec diff algorithms.
"""

from typing import Dict, Optional, Tuple

from ate_smt7_diff.models import (
    TimingEqnSetBlock,
    TimingEqnSetDiff,
    TimingPinConfig,
    TimingSetConfig,
    TimingSpec,
    TimingSpecDiff,
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
