#!/usr/bin/env python3
"""
Level spec and EQNSET diff algorithms.
"""

from ate_smt7_diff.diff.utils import diff_dicts
from ate_smt7_diff.models import (
    EqnSetBlock,
    EqnSetDiff,
    LevelSetPinConfig,
    LevelSpec,
    LevelSpecDiff,
)


def diff_level_specs(
    suite_name: str,
    old_specs: dict[str, LevelSpec] | None,
    new_specs: dict[str, LevelSpec] | None,
) -> LevelSpecDiff | None:
    """Compute level spec differences between two spec dictionaries."""
    if old_specs is None and new_specs is None:
        return None

    if old_specs is None:
        return LevelSpecDiff(suite_name=suite_name, added=new_specs or {})

    if new_specs is None:
        return LevelSpecDiff(suite_name=suite_name, removed=old_specs)

    result = diff_dicts(
        old_specs,
        new_specs,
        compare=lambda a, b: (
            a.actual == b.actual
            and a.min == b.min
            and a.max == b.max
            and a.units == b.units
            and a.comment == b.comment
        ),
    )
    if result is None:
        return None
    added, removed, changed = result

    return LevelSpecDiff(
        suite_name=suite_name,
        added=added,
        removed=removed,
        changed=changed,
    )


def _diff_levelset_pins(
    old_pins: dict[str, LevelSetPinConfig],
    new_pins: dict[str, LevelSetPinConfig],
) -> dict[str, tuple[LevelSetPinConfig, LevelSetPinConfig]]:
    """Compare PINS groups within a single LEVELSET."""
    return {
        name: (old_pins[name], new_pins[name])
        for name in set(old_pins.keys()) & set(new_pins.keys())
        if old_pins[name] != new_pins[name]
    }


def diff_eqnset_blocks(
    suite_name: str,
    old_block: EqnSetBlock | None,
    new_block: EqnSetBlock | None,
) -> EqnSetDiff | None:
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
    dpspins_added, dpspins_removed, dpspins_changed = diff_dicts(
        old_block.dpspins, new_block.dpspins
    ) or ({}, {}, {})

    # LEVELSET diff
    levelsets_added, levelsets_removed, _ = diff_dicts(
        old_block.levelsets, new_block.levelsets
    ) or ({}, {}, {})
    levelsets_changed: dict[int, dict[str, tuple[LevelSetPinConfig, LevelSetPinConfig]]] = {}
    for k in set(old_block.levelsets.keys()) & set(new_block.levelsets.keys()):
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
