#!/usr/bin/env python3
"""JSON serialization helpers for timing spec, EQNSET, and wavetable diffs."""

from ate_smt7_diff.formatters.shared import (
    arc as _arc,
    arc_all_fields as _arc_all_fields,
    levelset_group_arc as _levelset_group_arc,
    timing_arc as _timing_arc,
    timing_eqnset_block_dict as _timing_eqnset_block_dict,
    timing_spec_dict as _timing_spec_dict,
    wavetbl_pins_group_dict as _wavetbl_pins_group_dict,
    wavetbl_row_dict as _wavetbl_row_dict,
)
from ate_smt7_diff.models import TimingEqnSetDiff, TimingSpecDiff, WaveTblDiff


def _format_timing_spec_json(diff: TimingSpecDiff) -> dict:
    """Serialize a TimingSpecDiff as a JSON dict."""
    return {
        "suite_name": diff.suite_name,
        "spec_type": diff.spec_type,
        "spec_name": diff.spec_name,
        "replaced_from": diff.replaced_from,
        "new_specs": (
            {
                name: _timing_spec_dict(spec)
                for name, spec in (diff.new_specs or {}).items()
            }
            if diff.replaced_from
            else None
        ),
        **_timing_arc(diff.added, diff.removed, diff.changed),
    }


def _format_timing_eqnset_json(diff: TimingEqnSetDiff) -> dict:
    """Serialize a TimingEqnSetDiff as a JSON dict."""
    return {
        "suite_name": diff.suite_name,
        "eqnset_index": diff.eqnset_index,
        "eqnset_name": diff.eqnset_name,
        "replaced_from_index": diff.replaced_from_index,
        "replaced_from_name": diff.replaced_from_name,
        "replaced_block": (
            _timing_eqnset_block_dict(diff.new_block)
            if diff.replaced_from_name and diff.new_block
            else None
        ),
        "specs": _timing_arc(
            diff.specs_added, diff.specs_removed, diff.specs_changed
        ),
        "pins": _arc_all_fields(
            diff.pins_added, diff.pins_removed, diff.pins_changed
        ),
        "timingsets": _levelset_group_arc(
            diff.timingsets_added, diff.timingsets_removed, diff.timingsets_changed
        ),
    }


def _format_wavetbl_json(diff: WaveTblDiff) -> dict:
    """Serialize a WaveTblDiff as a JSON dict."""
    return {
        "suite_name": diff.suite_name,
        "wavetbl_name": diff.wavetbl_name,
        "replaced_from": diff.replaced_from,
        "replaced_block": (
            {
                "pins_groups": {
                    name: _wavetbl_pins_group_dict(group)
                    for name, group in diff.new_block.pins_groups.items()
                }
            }
            if diff.replaced_from and diff.new_block
            else None
        ),
        "added_block": (
            {
                "pins_groups": {
                    name: _wavetbl_pins_group_dict(group)
                    for name, group in diff.new_block.pins_groups.items()
                }
            }
            if diff.new_block and not diff.old_block and not diff.replaced_from
            else None
        ),
        "removed_block": (
            {
                "pins_groups": {
                    name: _wavetbl_pins_group_dict(group)
                    for name, group in diff.old_block.pins_groups.items()
                }
            }
            if diff.old_block and not diff.new_block and not diff.replaced_from
            else None
        ),
        "pins_groups": (
            {
                "added": {
                    name: _wavetbl_pins_group_dict(group)
                    for name, group in diff.pins_groups_added.items()
                },
                "removed": {
                    name: _wavetbl_pins_group_dict(group)
                    for name, group in diff.pins_groups_removed.items()
                },
                "changed": {
                    name: {
                        "rows_added": [
                            _wavetbl_row_dict(r) for r in pg_diff.rows_added
                        ],
                        "rows_removed": [
                            _wavetbl_row_dict(r) for r in pg_diff.rows_removed
                        ],
                        "rows_changed": [
                            {
                                "old": _wavetbl_row_dict(old_r),
                                "new": _wavetbl_row_dict(new_r),
                            }
                            for old_r, new_r in pg_diff.rows_changed
                        ],
                        "brk_old": pg_diff.brk_old,
                        "brk_new": pg_diff.brk_new,
                        "f_old": pg_diff.f_old,
                        "f_new": pg_diff.f_new,
                    }
                    for name, pg_diff in diff.pins_groups_changed.items()
                },
            }
            if diff.old_block and diff.new_block and not diff.replaced_from
            else None
        ),
    }
