#!/usr/bin/env python3
"""
Level spec and EQNSET diff algorithms.
"""

from typing import Dict, Optional, Tuple

from ate_smt7_diff.models import (
    EqnSetBlock,
    EqnSetDiff,
    LevelSetPinConfig,
    LevelSpec,
    LevelSpecDiff,
)


def diff_level_specs(
    suite_name: str,
    old_specs: Optional[Dict[str, LevelSpec]],
    new_specs: Optional[Dict[str, LevelSpec]],
) -> Optional[LevelSpecDiff]:
    """Compute level spec differences between two spec dictionaries."""
    if old_specs is None and new_specs is None:
        return None

    if old_specs is None:
        return LevelSpecDiff(suite_name=suite_name, added=new_specs or {})

    if new_specs is None:
        return LevelSpecDiff(suite_name=suite_name, removed=old_specs)

    old_keys = set(old_specs.keys())
    new_keys = set(new_specs.keys())

    added = {k: new_specs[k] for k in new_keys - old_keys}
    removed = {k: old_specs[k] for k in old_keys - new_keys}
    changed = {}
    for k in old_keys & new_keys:
        old_s = old_specs[k]
        new_s = new_specs[k]
        if (
            old_s.actual != new_s.actual
            or old_s.min != new_s.min
            or old_s.max != new_s.max
            or old_s.units != new_s.units
            or old_s.comment != new_s.comment
        ):
            changed[k] = (old_s, new_s)

    return LevelSpecDiff(
        suite_name=suite_name,
        added=added,
        removed=removed,
        changed=changed,
    )


def _diff_levelset_pins(
    old_pins: Dict[str, LevelSetPinConfig],
    new_pins: Dict[str, LevelSetPinConfig],
) -> Dict[str, Tuple[LevelSetPinConfig, LevelSetPinConfig]]:
    """Compare PINS groups within a single LEVELSET."""
    return {
        name: (old_pins[name], new_pins[name])
        for name in set(old_pins.keys()) & set(new_pins.keys())
        if old_pins[name] != new_pins[name]
    }


def diff_eqnset_blocks(
    suite_name: str,
    old_block: Optional[EqnSetBlock],
    new_block: Optional[EqnSetBlock],
) -> Optional[EqnSetDiff]:
    """Compute EQNSET block differences between two program versions."""
    if old_block is None and new_block is None:
        return None

    if old_block is None:
        return EqnSetDiff(
            suite_name=suite_name,
            eqnset_index=new_block.eqnset_index if new_block else 0,
            eqnset_name=new_block.eqnset_name if new_block else "",
            dpspins_added=new_block.dpspins if new_block else {},
            levelsets_added=new_block.levelsets if new_block else {},
        )

    if new_block is None:
        return EqnSetDiff(
            suite_name=suite_name,
            eqnset_index=old_block.eqnset_index,
            eqnset_name=old_block.eqnset_name,
            dpspins_removed=old_block.dpspins,
            levelsets_removed=old_block.levelsets,
        )

    # DPSPINS diff
    old_dps_keys = set(old_block.dpspins.keys())
    new_dps_keys = set(new_block.dpspins.keys())
    dpspins_added = {k: new_block.dpspins[k] for k in new_dps_keys - old_dps_keys}
    dpspins_removed = {k: old_block.dpspins[k] for k in old_dps_keys - new_dps_keys}
    dpspins_changed = {
        k: (old_block.dpspins[k], new_block.dpspins[k])
        for k in old_dps_keys & new_dps_keys
        if old_block.dpspins[k] != new_block.dpspins[k]
    }

    # LEVELSET diff
    old_ls_keys = set(old_block.levelsets.keys())
    new_ls_keys = set(new_block.levelsets.keys())
    levelsets_added = {k: new_block.levelsets[k] for k in new_ls_keys - old_ls_keys}
    levelsets_removed = {k: old_block.levelsets[k] for k in old_ls_keys - new_ls_keys}
    levelsets_changed: Dict[int, Dict[str, Tuple[LevelSetPinConfig, LevelSetPinConfig]]] = {}
    for k in old_ls_keys & new_ls_keys:
        old_pins = old_block.levelsets[k]
        new_pins = new_block.levelsets[k]
        pin_diff = _diff_levelset_pins(old_pins, new_pins)
        # Also include added/removed pins within the same levelset as changed
        old_pin_keys = set(old_pins.keys())
        new_pin_keys = set(new_pins.keys())
        for pk in new_pin_keys - old_pin_keys:
            pin_diff[pk] = (LevelSetPinConfig(), new_pins[pk])
        for pk in old_pin_keys - new_pin_keys:
            pin_diff[pk] = (old_pins[pk], LevelSetPinConfig())
        if pin_diff:
            levelsets_changed[k] = pin_diff

    return EqnSetDiff(
        suite_name=suite_name,
        eqnset_index=old_block.eqnset_index,
        eqnset_name=old_block.eqnset_name,
        dpspins_added=dpspins_added,
        dpspins_removed=dpspins_removed,
        dpspins_changed=dpspins_changed,
        levelsets_added=levelsets_added,
        levelsets_removed=levelsets_removed,
        levelsets_changed=levelsets_changed,
    )
