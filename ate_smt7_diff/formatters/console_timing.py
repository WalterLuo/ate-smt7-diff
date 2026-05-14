#!/usr/bin/env python3
"""Console formatting for timing spec, EQNSET, and wavetable diffs."""

from ate_smt7_diff.formatters.shared import (
    field_changes,
    fields_str,
    fmt_val,
    truncate_name,
)
from ate_smt7_diff.models import (
    TimingEqnSetBlock,
    TimingEqnSetDiff,
    TimingSpecDiff,
    WaveTblBlock,
    WaveTblDiff,
)


def _match_pin_list_changes(
    pins_added: dict,
    pins_removed: dict,
) -> tuple[list[tuple[str, str, str]], dict, dict]:
    """Match added/removed PINS groups with identical edge values.

    Returns (matched, remaining_added, remaining_removed) where matched
    is a list of (old_name, new_name, delta_str).
    """
    matched: list[tuple[str, str, str]] = []
    remaining_added = dict(pins_added)
    remaining_removed = dict(pins_removed)

    for r_name, r_cfg in list(remaining_removed.items()):
        for a_name, a_cfg in list(remaining_added.items()):
            if r_cfg == a_cfg:
                old_pins = set(r_name.split())
                new_pins = set(a_name.split())
                removed_pins = sorted(old_pins - new_pins)
                added_pins = sorted(new_pins - old_pins)
                parts = []
                if removed_pins:
                    parts.append(f"Removed {', '.join(removed_pins)}")
                if added_pins:
                    parts.append(f"Added {', '.join(added_pins)}")
                delta_str = "; ".join(parts)
                matched.append((r_name, a_name, delta_str))
                del remaining_added[a_name]
                del remaining_removed[r_name]
                break

    return matched, remaining_added, remaining_removed


def _format_eqnset_block_console(block: TimingEqnSetBlock) -> list[str]:
    """Format EQNSET block content as console lines."""
    lines = []
    if block.specs:
        lines.append("    SPECS:")
        for name, spec in block.specs.items():
            lines.append(f"      {name}: value={spec.value}, units={spec.units}")
    if block.pins_groups:
        lines.append("    PINS:")
        for name, cfg in block.pins_groups.items():
            lines.append(f"      {name}: {fields_str(cfg)}")
    if block.timingsets:
        lines.append("    TIMINGSET:")
        for idx, cfg in block.timingsets.items():
            lines.append(f"      TIMINGSET {idx}: {fields_str(cfg)}")
    return lines


def _format_timing_eqnset_console(diff: TimingEqnSetDiff) -> list[str]:
    """Format a single TimingEqnSetDiff as console lines."""
    lines = []

    # Replacement
    if diff.replaced_from_name:
        lines.append(
            f"{diff.suite_name}: Timing EQNSET Replaced: "
            f'{diff.replaced_from_index} "{diff.replaced_from_name}" -> '
            f'{diff.eqnset_index} "{diff.eqnset_name}"'
        )
        if diff.new_block:
            lines.append("  New EQNSET content:")
            lines.extend(_format_eqnset_block_console(diff.new_block))
        return lines

    lines.append(f'{diff.suite_name} (EQNSET {diff.eqnset_index} "{diff.eqnset_name}"):')
    if diff.specs_added:
        lines.append("  SPECS Added:")
        for name, spec in diff.specs_added.items():
            lines.append(f"    + {name}: value={spec.value}, units={spec.units}")
    if diff.specs_removed:
        lines.append("  SPECS Removed:")
        for name, spec in diff.specs_removed.items():
            lines.append(f"    - {name}: value={spec.value}, units={spec.units}")
    if diff.specs_changed:
        lines.append("  SPECS Changed:")
        for name, (old_s, new_s) in diff.specs_changed.items():
            changes = []
            if old_s.value != new_s.value:
                changes.append(f"value {old_s.value} -> {fmt_val(new_s.value)}")
            if old_s.units != new_s.units:
                changes.append(f"units {old_s.units} -> {fmt_val(new_s.units)}")
            if old_s.comment != new_s.comment:
                changes.append(f"comment {old_s.comment} -> {fmt_val(new_s.comment)}")
            lines.append(f"    ~ {name}: {', '.join(changes)}")
    matched, rem_added, rem_removed = _match_pin_list_changes(diff.pins_added, diff.pins_removed)
    if matched:
        lines.append("  PINS Modified:")
        for old_name, _new_name, delta in matched:
            lines.append(f"    ~ {truncate_name(old_name)} -> {delta}")
    if rem_added:
        lines.append("  PINS Added:")
        for name, cfg in rem_added.items():
            lines.append(f"    + {truncate_name(name)}: {fields_str(cfg)}")
    if rem_removed:
        lines.append("  PINS Removed:")
        for name, cfg in rem_removed.items():
            lines.append(f"    - {truncate_name(name)}: {fields_str(cfg)}")
    if diff.pins_changed:
        lines.append("  Edge Changed:")
        for name, (old_c, new_c) in diff.pins_changed.items():
            changes = [f"{k} {ov} -> {fmt_val(nv)}" for k, ov, nv in field_changes(old_c, new_c)]
            display_name = truncate_name(name)
            if len(changes) == 1:
                lines.append(f"    ~ {display_name}: {changes[0]}")
            else:
                lines.append(f"    ~ {display_name}:")
                for ch in changes:
                    lines.append(f"      ~ {ch}")
    if diff.timingsets_added:
        lines.append("  TIMINGSET Added:")
        for idx, cfg in diff.timingsets_added.items():
            lines.append(f"    + TIMINGSET {idx}: {fields_str(cfg)}")
    if diff.timingsets_removed:
        lines.append("  TIMINGSET Removed:")
        for idx, cfg in diff.timingsets_removed.items():
            lines.append(f"    - TIMINGSET {idx}: {fields_str(cfg)}")
    if diff.timingsets_changed:
        lines.append("  TIMINGSET Changed:")
        for idx, (old_c, new_c) in diff.timingsets_changed.items():
            changes = [f"{k} {ov} -> {fmt_val(nv)}" for k, ov, nv in field_changes(old_c, new_c)]
            lines.append(f"    ~ TIMINGSET {idx}: {', '.join(changes)}")
    return lines


def _format_timing_spec_console(diff: TimingSpecDiff) -> list[str]:
    """Format a single TimingSpecDiff as console lines."""
    lines = []

    # Replacement
    if diff.replaced_from:
        lines.append(
            f"{diff.suite_name}: Timing Spec Replaced: {diff.replaced_from} -> {diff.spec_name}"
        )
        if diff.new_specs:
            lines.append("  New spec content:")
            for name, spec in diff.new_specs.items():
                lines.append(f"    {name}: value={spec.value}, units={spec.units}")
        return lines

    lines.append(f'{diff.suite_name} ({diff.spec_type} spec "{diff.spec_name}"):')
    if diff.added:
        lines.append("  Added:")
        for name, spec in diff.added.items():
            lines.append(f"    + {name}: value={spec.value}, units={spec.units}")
    if diff.removed:
        lines.append("  Removed:")
        for name, spec in diff.removed.items():
            lines.append(f"    - {name}: value={spec.value}, units={spec.units}")
    if diff.changed:
        lines.append("  Changed:")
        for name, (old_s, new_s) in diff.changed.items():
            changes = []
            if old_s.value != new_s.value:
                changes.append(f"value {old_s.value} -> {fmt_val(new_s.value)}")
            if old_s.units != new_s.units:
                changes.append(f"units {old_s.units} -> {fmt_val(new_s.units)}")
            if old_s.comment != new_s.comment:
                changes.append(f"comment {old_s.comment} -> {fmt_val(new_s.comment)}")
            lines.append(f"    ~ {name}: {', '.join(changes)}")
    return lines


def _format_wavetbl_block_content(block: WaveTblBlock, marker: str) -> list[str]:
    """Format full WAVETBL block content with a +/- marker."""
    lines = []
    for name, group in block.pins_groups.items():
        lines.append(f"    {marker} {name}")
        for row in group.rows:
            lines.append(f'      {row.label} "{row.edge_spec}" {row.state}')
        if group.brk:
            lines.append(f'      brk "{group.brk}"')
        if group.f:
            lines.append(f'      f "{group.f}"')
    return lines


def _format_wavetbl_console(diff: WaveTblDiff) -> list[str]:
    """Format a single WaveTblDiff as console lines."""
    lines = []

    # Replacement
    if diff.replaced_from:
        lines.append(
            f"{diff.suite_name}: WAVETBL Replaced: {diff.replaced_from} -> {diff.wavetbl_name}"
        )
        if diff.new_block:
            lines.extend(_format_wavetbl_block_content(diff.new_block, "+"))
        return lines

    lines.append(f'{diff.suite_name} (WAVETBL "{diff.wavetbl_name}"):')

    # Whole block added/removed
    if diff.new_block and not diff.old_block:
        lines.append("  WAVETBL Added:")
        lines.extend(_format_wavetbl_block_content(diff.new_block, "+"))
    elif diff.old_block and not diff.new_block:
        lines.append("  WAVETBL Removed:")
        lines.extend(_format_wavetbl_block_content(diff.old_block, "-"))

    # Internal PINS changes (only when both blocks exist with same name)
    if diff.pins_groups_added:
        lines.append("  PINS Added:")
        for name, group in diff.pins_groups_added.items():
            lines.append(f"    + {name}")
            for row in group.rows:
                lines.append(f'      {row.label} "{row.edge_spec}" {row.state}')
            if group.brk:
                lines.append(f'      brk "{group.brk}"')
            if group.f:
                lines.append(f'      f "{group.f}"')
    if diff.pins_groups_removed:
        lines.append("  PINS Removed:")
        for name, group in diff.pins_groups_removed.items():
            lines.append(f"    - {name}")
            for row in group.rows:
                lines.append(f'      {row.label} "{row.edge_spec}" {row.state}')
            if group.brk:
                lines.append(f'      brk "{group.brk}"')
            if group.f:
                lines.append(f'      f "{group.f}"')
    if diff.pins_groups_changed:
        lines.append("  PINS Changed:")
        for name, pg_diff in diff.pins_groups_changed.items():
            lines.append(f"    ~ {name}")
            for row in pg_diff.rows_added:
                lines.append(f'      + {row.label} "{row.edge_spec}" {row.state}')
            for row in pg_diff.rows_removed:
                lines.append(f'      - {row.label} "{row.edge_spec}" {row.state}')
            for old_r, new_r in pg_diff.rows_changed:
                changes = []
                if old_r.edge_spec != new_r.edge_spec:
                    changes.append(f'edge_spec "{old_r.edge_spec}" -> "{new_r.edge_spec}"')
                if old_r.state != new_r.state:
                    changes.append(f'state "{old_r.state}" -> "{new_r.state}"')
                lines.append(f"      ~ {old_r.label}: {', '.join(changes)}")
            if pg_diff.brk_old != pg_diff.brk_new:
                lines.append(f'      ~ brk "{pg_diff.brk_old}" -> "{pg_diff.brk_new}"')
            if pg_diff.f_old != pg_diff.f_new:
                lines.append(f'      ~ f "{pg_diff.f_old}" -> "{pg_diff.f_new}"')
    return lines
