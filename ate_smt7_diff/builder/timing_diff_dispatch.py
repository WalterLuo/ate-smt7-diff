#!/usr/bin/env python3
"""
Timing diff dispatch: port-spec vs regular timing diff logic.
"""

from ate_smt7_diff.diff.timing_diff import (
    diff_timing_eqnset_blocks,
    diff_timing_eqnset_blocks_full,
    diff_timing_specs,
)
from ate_smt7_diff.models import (
    SuiteConfigView,
    TimingEqnSetDiff,
    TimingSpecDiff,
)


def _diff_port_timing(
    suite_name: str,
    old_v: SuiteConfigView,
    new_v: SuiteConfigView,
    timing_spec_diffs: list[TimingSpecDiff],
    timing_eqnset_diffs: list[TimingEqnSetDiff],
) -> None:
    """Diff port-spec timing (no override_tim_equ_set)."""
    spec_name = old_v.timing_spec_set or new_v.timing_spec_set or ""

    if old_v.timing_spec_set != new_v.timing_spec_set:
        spec_diff = TimingSpecDiff(
            suite_name=suite_name,
            spec_type="port",
            spec_name=new_v.timing_spec_set or "",
            replaced_from=old_v.timing_spec_set,
            old_specs=old_v.timing_specs,
            new_specs=new_v.timing_specs,
        )
        if spec_diff.has_changes:
            timing_spec_diffs.append(spec_diff)
        return

    old_eqnsets = tuple(old_v.timing_spec_eqnsets or [])
    new_eqnsets = tuple(new_v.timing_spec_eqnsets or [])

    if old_eqnsets != new_eqnsets:
        old_eqnset_set: set[tuple[int, str]] = set(old_eqnsets)
        new_eqnset_set: set[tuple[int, str]] = set(new_eqnsets)
        common_eqnsets: set[tuple[int, str]] = old_eqnset_set & new_eqnset_set
        old_only: set[tuple[int, str]] = old_eqnset_set - new_eqnset_set
        new_only: set[tuple[int, str]] = new_eqnset_set - old_eqnset_set

        if len(old_only) == 1 and len(new_only) == 1:
            old_eq = old_only.pop()
            new_eq = new_only.pop()
            old_idx, old_name = old_eq
            new_idx, new_name = new_eq
            te_diff = TimingEqnSetDiff(
                suite_name=suite_name,
                eqnset_index=new_idx,
                eqnset_name=new_name,
                replaced_from_index=old_idx,
                replaced_from_name=old_name,
                new_block=new_v.timing_eqnset_blocks.get(new_idx),
            )
            if te_diff.has_changes:
                timing_eqnset_diffs.append(te_diff)
        else:
            for old_idx, old_name in old_only:
                old_block = old_v.timing_eqnset_blocks.get(old_idx)
                te_diff = TimingEqnSetDiff(
                    suite_name=suite_name,
                    eqnset_index=old_idx,
                    eqnset_name=old_name,
                    specs_removed=old_block.specs if old_block else {},
                    pins_removed=old_block.pins_groups if old_block else {},
                    timingsets_removed=old_block.timingsets if old_block else {},
                )
                if te_diff.has_changes:
                    timing_eqnset_diffs.append(te_diff)
            for new_idx, new_name in new_only:
                new_block = new_v.timing_eqnset_blocks.get(new_idx)
                te_diff = TimingEqnSetDiff(
                    suite_name=suite_name,
                    eqnset_index=new_idx,
                    eqnset_name=new_name,
                    specs_added=new_block.specs if new_block else {},
                    pins_added=new_block.pins_groups if new_block else {},
                    timingsets_added=new_block.timingsets if new_block else {},
                )
                if te_diff.has_changes:
                    timing_eqnset_diffs.append(te_diff)

        for eq_idx, _eq_name in common_eqnsets:
            old_block = old_v.timing_eqnset_blocks.get(eq_idx)
            new_block = new_v.timing_eqnset_blocks.get(eq_idx)
            te_diff = diff_timing_eqnset_blocks_full(
                suite_name=suite_name,
                old_block=old_block,
                new_block=new_block,
            )
            if te_diff and te_diff.has_changes:
                timing_eqnset_diffs.append(te_diff)
        return

    spec_diff = diff_timing_specs(
        suite_name=suite_name,
        spec_type="port",
        spec_name=spec_name,
        old_specs=old_v.timing_specs,
        new_specs=new_v.timing_specs,
    )
    if spec_diff and spec_diff.has_changes:
        timing_spec_diffs.append(spec_diff)

    for eq_idx, _eq_name in old_eqnsets:
        old_block = old_v.timing_eqnset_blocks.get(eq_idx)
        new_block = new_v.timing_eqnset_blocks.get(eq_idx)
        te_diff = diff_timing_eqnset_blocks_full(
            suite_name=suite_name,
            old_block=old_block,
            new_block=new_block,
        )
        if te_diff and te_diff.has_changes:
            timing_eqnset_diffs.append(te_diff)


def _diff_regular_timing(
    suite_name: str,
    old_v: SuiteConfigView,
    new_v: SuiteConfigView,
    timing_spec_diffs: list[TimingSpecDiff],
    timing_eqnset_diffs: list[TimingEqnSetDiff],
) -> None:
    """Diff regular timing (by override_tim_equ_set)."""
    if old_v.timing_eqn_set != new_v.timing_eqn_set:
        old_block = old_v.timing_eqnset_block
        new_block = new_v.timing_eqnset_block
        old_idx = old_v.timing_eqn_set or 0
        old_name = old_block.eqnset_name if old_block else ""
        te_diff = TimingEqnSetDiff(
            suite_name=suite_name,
            eqnset_index=new_v.timing_eqn_set or 0,
            eqnset_name=new_block.eqnset_name if new_block else "",
            replaced_from_index=old_idx,
            replaced_from_name=old_name,
            new_block=new_block,
        )
        if te_diff.has_changes:
            timing_eqnset_diffs.append(te_diff)
        return

    tim_diff = diff_timing_eqnset_blocks(
        suite_name=suite_name,
        old_block=old_v.timing_eqnset_block,
        new_block=new_v.timing_eqnset_block,
    )
    if tim_diff and tim_diff.has_changes:
        timing_spec_diffs.append(tim_diff)

    te_diff = diff_timing_eqnset_blocks_full(
        suite_name=suite_name,
        old_block=old_v.timing_eqnset_block,
        new_block=new_v.timing_eqnset_block,
    )
    if te_diff and te_diff.has_changes:
        timing_eqnset_diffs.append(te_diff)
