#!/usr/bin/env python3
"""Timing spec diff algorithms for SPECSET and EQSP TIM,SPS blocks."""

from ate_smt7_diff.diff.utils import diff_dicts
from ate_smt7_diff.models import TimingEqnSetBlock, TimingSpecDiff


def diff_timing_specs(
    suite_name: str,
    spec_type: str,
    spec_name: str,
    old_specs: dict[str, "TimingSpec"] | None,
    new_specs: dict[str, "TimingSpec"] | None,
) -> TimingSpecDiff | None:
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

    result = diff_dicts(
        old_specs,
        new_specs,
        compare=lambda a, b: (
            a.value == b.value and a.units == b.units and a.comment == b.comment
        ),
    )
    if result is None:
        return None
    added, removed, changed = result
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
    old_block: TimingEqnSetBlock | None,
    new_block: TimingEqnSetBlock | None,
) -> TimingSpecDiff | None:
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
