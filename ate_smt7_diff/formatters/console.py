#!/usr/bin/env python3
"""
Console formatter for diff reports.
"""

from typing import Dict, List, Tuple

from ate_smt7_diff.models import (
    DiffReport,
    DiffType,
    DpsPinConfig,
    EqnSetDiff,
    LevelSetPinConfig,
    LevelSpecDiff,
    SuiteConfigReport,
    TimingEqnSetBlock,
    TimingEqnSetDiff,
    TimingPinConfig,
    TimingSetConfig,
    TimingSpecDiff,
    WaveTblDiff,
    WaveTblPinsGroupDiff,
)


def _fmt_val(val: str) -> str:
    """Format a value, showing 'removed' when empty."""
    return val if val else "removed"


def _truncate_name(name: str, max_len: int = 60) -> str:
    """Truncate a long pin group name for compact display."""
    if len(name) <= max_len:
        return name
    head = name[:30]
    tail = name[-25:]
    return f"{head}...{tail}"


def _dpspin_fields_str(cfg: DpsPinConfig) -> str:
    """Format DpsPinConfig fields as a compact string."""
    fields = cfg.all_fields()
    return ", ".join(f"{k}={v}" for k, v in fields.items())


def _collect_dpspin_changes(old_c: DpsPinConfig, new_c: DpsPinConfig) -> List[str]:
    """Collect changed fields between two DpsPinConfig objects."""
    old_fields = old_c.all_fields()
    new_fields = new_c.all_fields()
    changes = []
    for key in set(old_fields.keys()) | set(new_fields.keys()):
        old_val = old_fields.get(key, "")
        new_val = new_fields.get(key, "")
        if old_val != new_val:
            changes.append(f"{key} {old_val} -> {_fmt_val(new_val)}")
    return changes


def _collect_levelset_changes(old_c: LevelSetPinConfig, new_c: LevelSetPinConfig) -> List[str]:
    """Collect changed fields between two LevelSetPinConfig objects."""
    old_fields = old_c.all_fields()
    new_fields = new_c.all_fields()
    changes = []
    for key in set(old_fields.keys()) | set(new_fields.keys()):
        old_val = old_fields.get(key, "")
        new_val = new_fields.get(key, "")
        if old_val != new_val:
            changes.append(f"{key} {old_val} -> {_fmt_val(new_val)}")
    return changes


def _format_level_spec_console(diff: LevelSpecDiff) -> List[str]:
    """Format a single LevelSpecDiff as console lines."""
    lines = []
    lines.append("  * level spec changes:")
    for name, spec in diff.added.items():
        lines.append(f"    + {name}: actual={spec.actual}, units={spec.units}")
    for name, spec in diff.removed.items():
        lines.append(f"    - {name}: actual={spec.actual}, units={spec.units}")
    for name, (old_s, new_s) in diff.changed.items():
        changes = []
        if old_s.actual != new_s.actual:
            changes.append(f"actual {old_s.actual} -> {_fmt_val(new_s.actual)}")
        if old_s.min != new_s.min:
            changes.append(f"min {old_s.min} -> {_fmt_val(new_s.min)}")
        if old_s.max != new_s.max:
            changes.append(f"max {old_s.max} -> {_fmt_val(new_s.max)}")
        if old_s.units != new_s.units:
            changes.append(f"units {old_s.units} -> {_fmt_val(new_s.units)}")
        if old_s.comment != new_s.comment:
            changes.append(f"comment {old_s.comment} -> {_fmt_val(new_s.comment)}")
        lines.append(f"    ~ {name}: {', '.join(changes)}")
    return lines


def _format_eqnset_console(diff: EqnSetDiff) -> List[str]:
    """Format a single EqnSetDiff as console lines."""
    lines = []
    lines.append(f"{diff.suite_name} (EQNSET {diff.eqnset_index} \"{diff.eqnset_name}\"):")
    if diff.dpspins_added:
        lines.append("  DPSPINS Added:")
        for name, cfg in diff.dpspins_added.items():
            lines.append(f"    + {name}: {_dpspin_fields_str(cfg)}")
    if diff.dpspins_removed:
        lines.append("  DPSPINS Removed:")
        for name, cfg in diff.dpspins_removed.items():
            lines.append(f"    - {name}: {_dpspin_fields_str(cfg)}")
    if diff.dpspins_changed:
        lines.append("  DPSPINS Changed:")
        for name, (old_c, new_c) in diff.dpspins_changed.items():
            changes = _collect_dpspin_changes(old_c, new_c)
            lines.append(f"    ~ {name}: {', '.join(changes)}")
    if diff.levelsets_added:
        lines.append("  LEVELSET Added:")
        for idx, pins in diff.levelsets_added.items():
            lines.append(f"    + LEVELSET {idx}:")
            for name, cfg in pins.items():
                lines.append(f"      + {name}: vih={cfg.vih}, vil={cfg.vil}, voh={cfg.voh}, vol={cfg.vol}")
    if diff.levelsets_removed:
        lines.append("  LEVELSET Removed:")
        for idx, pins in diff.levelsets_removed.items():
            lines.append(f"    - LEVELSET {idx}:")
            for name, cfg in pins.items():
                lines.append(f"      - {name}: vih={cfg.vih}, vil={cfg.vil}, voh={cfg.voh}, vol={cfg.vol}")
    if diff.levelsets_changed:
        lines.append("  LEVELSET Changed:")
        for idx, pins in diff.levelsets_changed.items():
            lines.append(f"    ~ LEVELSET {idx}:")
            for name, (old_c, new_c) in pins.items():
                changes = _collect_levelset_changes(old_c, new_c)
                is_new = not old_c.vih and not old_c.vil and not old_c.voh and not old_c.vol
                is_removed = not new_c.vih and not new_c.vil and not new_c.voh and not new_c.vol
                if changes:
                    marker = "~"
                elif is_new:
                    marker = "+"
                elif is_removed:
                    marker = "-"
                else:
                    marker = "~"
                if changes:
                    detail = ", ".join(changes)
                else:
                    detail = f"vih={new_c.vih}, vil={new_c.vil}, voh={new_c.voh}, vol={new_c.vol}"
                lines.append(f"      {marker} {name}: {detail}")
    return lines


def _timing_pin_fields_str(cfg: TimingPinConfig) -> str:
    """Format TimingPinConfig fields as a compact string."""
    fields = cfg.all_fields()
    return ", ".join(f"{k}={v}" for k, v in fields.items())


def _match_pin_list_changes(
    pins_added: Dict[str, TimingPinConfig],
    pins_removed: Dict[str, TimingPinConfig],
) -> Tuple[List[Tuple[str, str, str]], Dict[str, TimingPinConfig], Dict[str, TimingPinConfig]]:
    """Match added/removed PINS groups with identical edge values.

    Returns (matched, remaining_added, remaining_removed) where matched
    is a list of (old_name, new_name, delta_str).
    """
    matched: List[Tuple[str, str, str]] = []
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


def _collect_timing_pin_changes(old_c: TimingPinConfig, new_c: TimingPinConfig) -> List[str]:
    """Collect changed fields between two TimingPinConfig objects."""
    old_fields = old_c.all_fields()
    new_fields = new_c.all_fields()
    changes = []
    for key in set(old_fields.keys()) | set(new_fields.keys()):
        old_val = old_fields.get(key, "")
        new_val = new_fields.get(key, "")
        if old_val != new_val:
            changes.append(f"{key} {old_val} -> {_fmt_val(new_val)}")
    return changes


def _collect_timingset_changes(old_c: TimingSetConfig, new_c: TimingSetConfig) -> List[str]:
    """Collect changed fields between two TimingSetConfig objects."""
    old_fields = old_c.all_fields()
    new_fields = new_c.all_fields()
    changes = []
    for key in set(old_fields.keys()) | set(new_fields.keys()):
        old_val = old_fields.get(key, "")
        new_val = new_fields.get(key, "")
        if old_val != new_val:
            changes.append(f"{key} {old_val} -> {_fmt_val(new_val)}")
    return changes


def _format_eqnset_block_console(block: TimingEqnSetBlock) -> List[str]:
    """Format EQNSET block content as console lines."""
    lines = []
    if block.specs:
        lines.append("    SPECS:")
        for name, spec in block.specs.items():
            lines.append(f"      {name}: value={spec.value}, units={spec.units}")
    if block.pins_groups:
        lines.append("    PINS:")
        for name, cfg in block.pins_groups.items():
            lines.append(f"      {name}: {_timing_pin_fields_str(cfg)}")
    if block.timingsets:
        lines.append("    TIMINGSET:")
        for idx, cfg in block.timingsets.items():
            lines.append(f"      TIMINGSET {idx}: {_timing_pin_fields_str(cfg)}")
    return lines


def _format_timing_eqnset_console(diff: TimingEqnSetDiff) -> List[str]:
    """Format a single TimingEqnSetDiff as console lines."""
    lines = []

    # Replacement
    if diff.replaced_from_name:
        lines.append(
            f"{diff.suite_name}: Timing EQNSET Replaced: "
            f"{diff.replaced_from_index} \"{diff.replaced_from_name}\" -> "
            f"{diff.eqnset_index} \"{diff.eqnset_name}\""
        )
        if diff.new_block:
            lines.append("  New EQNSET content:")
            lines.extend(_format_eqnset_block_console(diff.new_block))
        return lines

    lines.append(f"{diff.suite_name} (EQNSET {diff.eqnset_index} \"{diff.eqnset_name}\"):")
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
                changes.append(f"value {old_s.value} -> {_fmt_val(new_s.value)}")
            if old_s.units != new_s.units:
                changes.append(f"units {old_s.units} -> {_fmt_val(new_s.units)}")
            if old_s.comment != new_s.comment:
                changes.append(f"comment {old_s.comment} -> {_fmt_val(new_s.comment)}")
            lines.append(f"    ~ {name}: {', '.join(changes)}")
    matched, rem_added, rem_removed = _match_pin_list_changes(diff.pins_added, diff.pins_removed)
    if matched:
        lines.append("  PINS Modified:")
        for old_name, _new_name, delta in matched:
            lines.append(f"    ~ {_truncate_name(old_name)} -> {delta}")
    if rem_added:
        lines.append("  PINS Added:")
        for name, cfg in rem_added.items():
            lines.append(f"    + {_truncate_name(name)}: {_timing_pin_fields_str(cfg)}")
    if rem_removed:
        lines.append("  PINS Removed:")
        for name, cfg in rem_removed.items():
            lines.append(f"    - {_truncate_name(name)}: {_timing_pin_fields_str(cfg)}")
    if diff.pins_changed:
        lines.append("  Edge Changed:")
        for name, (old_c, new_c) in diff.pins_changed.items():
            changes = _collect_timing_pin_changes(old_c, new_c)
            display_name = _truncate_name(name)
            if len(changes) == 1:
                lines.append(f"    ~ {display_name}: {changes[0]}")
            else:
                lines.append(f"    ~ {display_name}:")
                for ch in changes:
                    lines.append(f"      ~ {ch}")
    if diff.timingsets_added:
        lines.append("  TIMINGSET Added:")
        for idx, cfg in diff.timingsets_added.items():
            lines.append(f"    + TIMINGSET {idx}: {_timing_pin_fields_str(cfg)}")
    if diff.timingsets_removed:
        lines.append("  TIMINGSET Removed:")
        for idx, cfg in diff.timingsets_removed.items():
            lines.append(f"    - TIMINGSET {idx}: {_timing_pin_fields_str(cfg)}")
    if diff.timingsets_changed:
        lines.append("  TIMINGSET Changed:")
        for idx, (old_c, new_c) in diff.timingsets_changed.items():
            changes = _collect_timingset_changes(old_c, new_c)
            lines.append(f"    ~ TIMINGSET {idx}: {', '.join(changes)}")
    return lines


def _format_timing_spec_console(diff: TimingSpecDiff) -> List[str]:
    """Format a single TimingSpecDiff as console lines."""
    lines = []

    # Replacement
    if diff.replaced_from:
        lines.append(
            f"{diff.suite_name}: Timing Spec Replaced: "
            f"{diff.replaced_from} -> {diff.spec_name}"
        )
        if diff.new_specs:
            lines.append("  New spec content:")
            for name, spec in diff.new_specs.items():
                lines.append(f"    {name}: value={spec.value}, units={spec.units}")
        return lines

    lines.append(f"{diff.suite_name} ({diff.spec_type} spec \"{diff.spec_name}\"):")
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
                changes.append(f"value {old_s.value} -> {_fmt_val(new_s.value)}")
            if old_s.units != new_s.units:
                changes.append(f"units {old_s.units} -> {_fmt_val(new_s.units)}")
            if old_s.comment != new_s.comment:
                changes.append(f"comment {old_s.comment} -> {_fmt_val(new_s.comment)}")
            lines.append(f"    ~ {name}: {', '.join(changes)}")
    return lines


def _format_wavetbl_block_content(block: "WaveTblBlock", marker: str) -> List[str]:
    """Format full WAVETBL block content with a +/- marker."""
    lines = []
    for name, group in block.pins_groups.items():
        lines.append(f"    {marker} {name}")
        for row in group.rows:
            lines.append(f"      {row.label} \"{row.edge_spec}\" {row.state}")
        if group.brk:
            lines.append(f"      brk \"{group.brk}\"")
        if group.f:
            lines.append(f"      f \"{group.f}\"")
    return lines


def _format_wavetbl_console(diff: WaveTblDiff) -> List[str]:
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

    lines.append(f"{diff.suite_name} (WAVETBL \"{diff.wavetbl_name}\"):")

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
                lines.append(f"      {row.label} \"{row.edge_spec}\" {row.state}")
            if group.brk:
                lines.append(f"      brk \"{group.brk}\"")
            if group.f:
                lines.append(f"      f \"{group.f}\"")
    if diff.pins_groups_removed:
        lines.append("  PINS Removed:")
        for name, group in diff.pins_groups_removed.items():
            lines.append(f"    - {name}")
            for row in group.rows:
                lines.append(f"      {row.label} \"{row.edge_spec}\" {row.state}")
            if group.brk:
                lines.append(f"      brk \"{group.brk}\"")
            if group.f:
                lines.append(f"      f \"{group.f}\"")
    if diff.pins_groups_changed:
        lines.append("  PINS Changed:")
        for name, pg_diff in diff.pins_groups_changed.items():
            lines.append(f"    ~ {name}")
            for row in pg_diff.rows_added:
                lines.append(f"      + {row.label} \"{row.edge_spec}\" {row.state}")
            for row in pg_diff.rows_removed:
                lines.append(f"      - {row.label} \"{row.edge_spec}\" {row.state}")
            for old_r, new_r in pg_diff.rows_changed:
                changes = []
                if old_r.edge_spec != new_r.edge_spec:
                    changes.append(f'edge_spec "{old_r.edge_spec}" -> "{new_r.edge_spec}"')
                if old_r.state != new_r.state:
                    changes.append(f'state "{old_r.state}" -> "{new_r.state}"')
                lines.append(f"      ~ {old_r.label}: {', '.join(changes)}")
            if pg_diff.brk_old != pg_diff.brk_new:
                lines.append(f"      ~ brk \"{pg_diff.brk_old}\" -> \"{pg_diff.brk_new}\"")
            if pg_diff.f_old != pg_diff.f_new:
                lines.append(f"      ~ f \"{pg_diff.f_old}\" -> \"{pg_diff.f_new}\"")
    return lines


def format_suite_console(report: SuiteConfigReport) -> str:
    """Format suite config diff as colored console output."""
    lines = []
    lines.append("=" * 60)
    lines.append("Suite Configuration Diff Report")
    lines.append("=" * 60)
    lines.append(
        f"Common suites: {len(report.common_suites)} "
        f"({len(report.suites_with_changes)} with changes)"
    )

    if report.skipped_suites:
        lines.append("")
        lines.append(f"Missing from both test_suites: {len(report.skipped_suites)}")
        for name in report.skipped_suites:
            lines.append(f"  ? {name}")

    for diff in report.diffs:
        if not diff.has_changes:
            continue

        lines.append("")
        lines.append(f"{diff.suite_name}:")

        if diff.changed:
            lines.append("  changed:")
            for key, (old_val, new_val) in diff.changed.items():
                lines.append(f"    {key}: {old_val} -> {_fmt_val(new_val)}")

        if diff.added:
            lines.append("  added:")
            for key, val in diff.added.items():
                lines.append(f"    {key}: {val}")

        if diff.removed:
            lines.append("  removed:")
            for key, val in diff.removed.items():
                lines.append(f"    {key}: {val}")

    return "\n".join(lines)


def format_console(report: DiffReport) -> str:
    """Format diff report as colored console output."""
    lines = []
    lines.append("=" * 60)
    lines.append("SMT7 Flow Diff Report")
    lines.append("=" * 60)
    lines.append(f"Old: {report.old_file} ({len(report.old_tests)} tests)")
    lines.append(f"New: {report.new_file} ({len(report.new_tests)} tests)")
    lines.append("")

    if report.added:
        lines.append(f"Added Tests ({len(report.added)}):")
        for name in report.added:
            lines.append(f"  + {name}")
        lines.append("")

    if report.removed:
        lines.append(f"Removed Tests ({len(report.removed)}):")
        for name in report.removed:
            lines.append(f"  - {name}")
        lines.append("")

    if report.moved:
        lines.append(f"Moved Tests ({len(report.moved)}):")
        for name in report.moved:
            # Find the diff entries for this move
            entries = [d for d in report.diffs if d.suite_name == name and d.diff_type == DiffType.MOVED]
            for d in entries:
                old_pos = d.old_index + 1 if d.old_index is not None else '?'
                new_pos = d.new_index + 1 if d.new_index is not None else '?'
                old_grp = ' / '.join(d.old_group_path) if d.old_group_path else '(root)'
                new_grp = ' / '.join(d.new_group_path) if d.new_group_path else '(root)'
                move_info = f"    pos {old_pos} -> {new_pos}"
                if old_grp != new_grp:
                    move_info += f", group [{old_grp}] -> [{new_grp}]"
                lines.append(f"  ~ {name}{move_info}")
        lines.append("")

    if report.order_changed:
        lines.append(f"Order Changed Tests ({len(report.order_changed)}):")
        for name in report.order_changed:
            lines.append(f"  * {name}")
        lines.append("")

    unchanged_count = len(report.unchanged)
    lines.append(f"Unchanged Tests: {unchanged_count}")
    lines.append("")

    # Sequence diff detail
    lines.append("Sequence Diff Detail:")
    lines.append("-" * 60)
    for d in report.diffs:
        if d.diff_type == DiffType.UNCHANGED:
            continue
        symbol = {DiffType.ADDED: "+", DiffType.REMOVED: "-", DiffType.MOVED: "~"}.get(d.diff_type, "?")
        pos_info = ""
        if d.old_index is not None:
            pos_info += f" [old:{d.old_index + 1}]"
        if d.new_index is not None:
            pos_info += f" [new:{d.new_index + 1}]"
        grp = ""
        if d.new_group_path:
            grp = f" (in: {' / '.join(d.new_group_path)})"
        elif d.old_group_path:
            grp = f" (was in: {' / '.join(d.old_group_path)})"
        lines.append(f"  {symbol} {d.suite_name}{pos_info}{grp}")

    if report.suite_config_report is not None:
        lines.append("")
        lines.append(format_suite_console(report.suite_config_report))

    if report.old_suite_views is not None and report.new_suite_views is not None:
        lines.append("")
        lines.append("=" * 60)
        lines.append("Associated Config Views")
        lines.append("=" * 60)
        common = sorted(
            set(report.old_suite_views.keys()) & set(report.new_suite_views.keys())
        )
        # Build lookup for level spec diffs
        spec_diff_by_suite: Dict[str, LevelSpecDiff] = {}
        if report.level_spec_diffs:
            for diff in report.level_spec_diffs:
                spec_diff_by_suite[diff.suite_name] = diff
        for suite_name in common:
            old_v = report.old_suite_views[suite_name]
            new_v = report.new_suite_views[suite_name]
            lines.append(f"{suite_name}:")
            if old_v.timing_spec_set or new_v.timing_spec_set:
                old_t = old_v.timing_spec_set or "-"
                new_t = new_v.timing_spec_set or "-"
                marker = "  " if old_t == new_t else "* "
                lines.append(f"  {marker}timing spec: {old_t} -> {new_t}")
            if old_v.level_eqn_set is not None or new_v.level_eqn_set is not None:
                old_e = old_v.level_eqn_set if old_v.level_eqn_set is not None else "-"
                new_e = new_v.level_eqn_set if new_v.level_eqn_set is not None else "-"
                marker = "  " if old_e == new_e else "* "
                lines.append(f"  {marker}level EQNSET: {old_e} -> {new_e}")
            if old_v.level_spec_set is not None or new_v.level_spec_set is not None:
                old_s = old_v.level_spec_set if old_v.level_spec_set is not None else "-"
                new_s = new_v.level_spec_set if new_v.level_spec_set is not None else "-"
                marker = "  " if old_s == new_s else "* "
                lines.append(f"  {marker}level SPECSET: {old_s} -> {new_s}")
            if suite_name in spec_diff_by_suite:
                lines.extend(_format_level_spec_console(spec_diff_by_suite[suite_name]))

    if report.eqnset_diffs:
        lines.append("")
        lines.append("=" * 60)
        lines.append("EQNSET Diff")
        lines.append("=" * 60)
        for diff in report.eqnset_diffs:
            lines.extend(_format_eqnset_console(diff))

    if report.timing_spec_diffs:
        lines.append("")
        lines.append("=" * 60)
        lines.append("Timing Spec Diff")
        lines.append("=" * 60)
        for diff in report.timing_spec_diffs:
            lines.extend(_format_timing_spec_console(diff))

    if report.timing_eqnset_diffs:
        lines.append("")
        lines.append("=" * 60)
        lines.append("Timing EQNSET Diff")
        lines.append("=" * 60)
        for diff in report.timing_eqnset_diffs:
            lines.extend(_format_timing_eqnset_console(diff))

    if report.timing_wavetbl_diffs:
        lines.append("")
        lines.append("=" * 60)
        lines.append("Timing Wavetable Diff")
        lines.append("=" * 60)
        for diff in report.timing_wavetbl_diffs:
            lines.extend(_format_wavetbl_console(diff))

    return "\n".join(lines)
