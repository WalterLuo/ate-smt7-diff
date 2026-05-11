#!/usr/bin/env python3
"""
Markdown formatter for diff reports.
"""

from typing import List

from ate_smt7_diff.models import DiffReport, DiffType, EqnSetDiff, LevelSpecDiff, SuiteConfigReport, TimingEqnSetBlock, TimingEqnSetDiff, TimingSpecDiff, WaveTblDiff


def _fmt_val(val: str) -> str:
    """Format a value, showing 'removed' when empty."""
    return val if val else "removed"


def _format_level_spec_markdown(diff: LevelSpecDiff) -> List[str]:
    """Format a single LevelSpecDiff as Markdown lines."""
    lines = []
    lines.append(f"### {diff.suite_name}")
    if diff.added:
        lines.append("")
        lines.append("**Added:**")
        for name, spec in diff.added.items():
            lines.append(f"- `{name}`: actual={spec.actual}, units={spec.units}")
    if diff.removed:
        lines.append("")
        lines.append("**Removed:**")
        for name, spec in diff.removed.items():
            lines.append(f"- ~~`{name}`: actual={spec.actual}, units={spec.units}~~")
    if diff.changed:
        lines.append("")
        lines.append("**Changed:**")
        lines.append("| Spec | Field | Old | New |")
        lines.append("|------|-------|-----|-----|")
        for name, (old_s, new_s) in diff.changed.items():
            if old_s.actual != new_s.actual:
                lines.append(f"| `{name}` | actual | `{old_s.actual}` | `{_fmt_val(new_s.actual)}` |")
            if old_s.min != new_s.min:
                lines.append(f"| `{name}` | min | `{old_s.min}` | `{_fmt_val(new_s.min)}` |")
            if old_s.max != new_s.max:
                lines.append(f"| `{name}` | max | `{old_s.max}` | `{_fmt_val(new_s.max)}` |")
            if old_s.units != new_s.units:
                lines.append(f"| `{name}` | units | `{old_s.units}` | `{_fmt_val(new_s.units)}` |")
            if old_s.comment != new_s.comment:
                lines.append(f"| `{name}` | comment | `{old_s.comment}` | `{_fmt_val(new_s.comment)}` |")
    return lines


def _format_eqnset_markdown(diff: EqnSetDiff) -> List[str]:
    """Format a single EqnSetDiff as Markdown lines."""
    lines = []
    lines.append(f"### {diff.suite_name} (EQNSET {diff.eqnset_index} \"{diff.eqnset_name}\")")

    if diff.dpspins_added or diff.dpspins_removed or diff.dpspins_changed:
        lines.append("")
        lines.append("#### DPSPINS")
        lines.append("")
        if diff.dpspins_added:
            lines.append("**Added:**")
            for name, cfg in diff.dpspins_added.items():
                fields_str = ", ".join(f"{k}={v}" for k, v in cfg.all_fields().items())
                lines.append(f"- `{name}`: {fields_str}")
            lines.append("")
        if diff.dpspins_removed:
            lines.append("**Removed:**")
            for name, cfg in diff.dpspins_removed.items():
                fields_str = ", ".join(f"{k}={v}" for k, v in cfg.all_fields().items())
                lines.append(f"- ~~`{name}`: {fields_str}~~")
            lines.append("")
        if diff.dpspins_changed:
            lines.append("**Changed:**")
            lines.append("| Pin | Field | Old | New |")
            lines.append("|-----|-------|-----|-----|")
            for name, (old_c, new_c) in diff.dpspins_changed.items():
                old_fields = old_c.all_fields()
                new_fields = new_c.all_fields()
                for key in sorted(set(old_fields.keys()) | set(new_fields.keys())):
                    old_val = old_fields.get(key, "")
                    new_val = new_fields.get(key, "")
                    if old_val != new_val:
                        lines.append(f"| `{name}` | {key} | `{old_val}` | `{_fmt_val(new_val)}` |")

    if diff.levelsets_added or diff.levelsets_removed or diff.levelsets_changed:
        lines.append("")
        lines.append("#### LEVELSET")
        lines.append("")
        if diff.levelsets_added:
            lines.append("**Added:**")
            for idx, pins in diff.levelsets_added.items():
                lines.append(f"- LEVELSET {idx}:")
                for name, cfg in pins.items():
                    fields_str = ", ".join(f"{k}={v}" for k, v in cfg.all_fields().items())
                    lines.append(f"  - `{name}`: {fields_str}")
            lines.append("")
        if diff.levelsets_removed:
            lines.append("**Removed:**")
            for idx, pins in diff.levelsets_removed.items():
                lines.append(f"- LEVELSET {idx}:")
                for name, cfg in pins.items():
                    fields_str = ", ".join(f"{k}={v}" for k, v in cfg.all_fields().items())
                    lines.append(f"  - ~~`{name}`: {fields_str}~~")
            lines.append("")
        if diff.levelsets_changed:
            lines.append("**Changed:**")
            lines.append("| LEVELSET | PINS | Field | Old | New |")
            lines.append("|----------|------|-------|-----|-----|")
            for idx, pins in diff.levelsets_changed.items():
                for name, (old_c, new_c) in pins.items():
                    old_fields = old_c.all_fields()
                    new_fields = new_c.all_fields()
                    for key in sorted(set(old_fields.keys()) | set(new_fields.keys())):
                        old_val = old_fields.get(key, "")
                        new_val = new_fields.get(key, "")
                        if old_val != new_val:
                            lines.append(f"| {idx} | `{name}` | {key} | `{old_val}` | `{_fmt_val(new_val)}` |")

    return lines


def _format_eqnset_block_markdown(block: TimingEqnSetBlock) -> List[str]:
    """Format EQNSET block content as Markdown lines."""
    lines = []
    if block.specs:
        lines.append("")
        lines.append("| Spec | Value | Units |")
        lines.append("|------|-------|-------|")
        for name, spec in block.specs.items():
            lines.append(f"| `{name}` | `{spec.value}` | `{spec.units}` |")
    if block.pins_groups:
        lines.append("")
        lines.append("| PINS | Fields |")
        lines.append("|------|--------|")
        for name, cfg in block.pins_groups.items():
            fields_str = ", ".join(f"{k}={v}" for k, v in cfg.all_fields().items())
            lines.append(f"| `{name}` | {fields_str} |")
    if block.timingsets:
        lines.append("")
        lines.append("| TIMINGSET | Fields |")
        lines.append("|-----------|--------|")
        for idx, cfg in block.timingsets.items():
            fields_str = ", ".join(f"{k}={v}" for k, v in cfg.all_fields().items())
            lines.append(f"| {idx} | {fields_str} |")
    return lines


def _format_timing_eqnset_markdown(diff: TimingEqnSetDiff) -> List[str]:
    """Format a single TimingEqnSetDiff as Markdown lines."""
    lines = []

    # Replacement
    if diff.replaced_from_name:
        lines.append(
            f"### {diff.suite_name}: Timing EQNSET Replaced: "
            f"{diff.replaced_from_index} \"{diff.replaced_from_name}\" -> "
            f"{diff.eqnset_index} \"{diff.eqnset_name}\""
        )
        if diff.new_block:
            lines.append("")
            lines.append("**New EQNSET content:**")
            lines.extend(_format_eqnset_block_markdown(diff.new_block))
        return lines

    lines.append(f"### {diff.suite_name} (EQNSET {diff.eqnset_index} \"{diff.eqnset_name}\")")

    if diff.specs_added or diff.specs_removed or diff.specs_changed:
        lines.append("")
        lines.append("#### SPECS")
        lines.append("")
        if diff.specs_added:
            lines.append("**Added:**")
            for name, spec in diff.specs_added.items():
                lines.append(f"- `{name}`: value={spec.value}, units={spec.units}")
            lines.append("")
        if diff.specs_removed:
            lines.append("**Removed:**")
            for name, spec in diff.specs_removed.items():
                lines.append(f"- ~~`{name}`: value={spec.value}, units={spec.units}~~")
            lines.append("")
        if diff.specs_changed:
            lines.append("**Changed:**")
            lines.append("| Spec | Field | Old | New |")
            lines.append("|------|-------|-----|-----|")
            for name, (old_s, new_s) in diff.specs_changed.items():
                if old_s.value != new_s.value:
                    lines.append(f"| `{name}` | value | `{old_s.value}` | `{_fmt_val(new_s.value)}` |")
                if old_s.units != new_s.units:
                    lines.append(f"| `{name}` | units | `{old_s.units}` | `{_fmt_val(new_s.units)}` |")
                if old_s.comment != new_s.comment:
                    lines.append(f"| `{name}` | comment | `{old_s.comment}` | `{_fmt_val(new_s.comment)}` |")

    if diff.pins_added or diff.pins_removed or diff.pins_changed:
        lines.append("")
        lines.append("#### PINS")
        lines.append("")
        if diff.pins_added:
            lines.append("**Added:**")
            for name, cfg in diff.pins_added.items():
                fields_str = ", ".join(f"{k}={v}" for k, v in cfg.all_fields().items())
                lines.append(f"- `{name}`: {fields_str}")
            lines.append("")
        if diff.pins_removed:
            lines.append("**Removed:**")
            for name, cfg in diff.pins_removed.items():
                fields_str = ", ".join(f"{k}={v}" for k, v in cfg.all_fields().items())
                lines.append(f"- ~~`{name}`: {fields_str}~~")
            lines.append("")
        if diff.pins_changed:
            lines.append("**Changed:**")
            lines.append("| PINS | Field | Old | New |")
            lines.append("|------|-------|-----|-----|")
            for name, (old_c, new_c) in diff.pins_changed.items():
                old_fields = old_c.all_fields()
                new_fields = new_c.all_fields()
                for key in sorted(set(old_fields.keys()) | set(new_fields.keys())):
                    old_val = old_fields.get(key, "")
                    new_val = new_fields.get(key, "")
                    if old_val != new_val:
                        lines.append(f"| `{name}` | {key} | `{old_val}` | `{_fmt_val(new_val)}` |")

    if diff.timingsets_added or diff.timingsets_removed or diff.timingsets_changed:
        lines.append("")
        lines.append("#### TIMINGSET")
        lines.append("")
        if diff.timingsets_added:
            lines.append("**Added:**")
            for idx, cfg in diff.timingsets_added.items():
                fields_str = ", ".join(f"{k}={v}" for k, v in cfg.all_fields().items())
                lines.append(f"- TIMINGSET {idx}: {fields_str}")
            lines.append("")
        if diff.timingsets_removed:
            lines.append("**Removed:**")
            for idx, cfg in diff.timingsets_removed.items():
                fields_str = ", ".join(f"{k}={v}" for k, v in cfg.all_fields().items())
                lines.append(f"- ~~TIMINGSET {idx}: {fields_str}~~")
            lines.append("")
        if diff.timingsets_changed:
            lines.append("**Changed:**")
            lines.append("| TIMINGSET | Field | Old | New |")
            lines.append("|-----------|-------|-----|-----|")
            for idx, (old_c, new_c) in diff.timingsets_changed.items():
                old_fields = old_c.all_fields()
                new_fields = new_c.all_fields()
                for key in sorted(set(old_fields.keys()) | set(new_fields.keys())):
                    old_val = old_fields.get(key, "")
                    new_val = new_fields.get(key, "")
                    if old_val != new_val:
                        lines.append(f"| {idx} | {key} | `{old_val}` | `{_fmt_val(new_val)}` |")

    return lines


def _format_timing_spec_markdown(diff: TimingSpecDiff) -> List[str]:
    """Format a single TimingSpecDiff as Markdown lines."""
    lines = []

    # Replacement
    if diff.replaced_from:
        lines.append(
            f"### {diff.suite_name}: Timing Spec Replaced: "
            f"{diff.replaced_from} -> {diff.spec_name}"
        )
        if diff.new_specs:
            lines.append("")
            lines.append("**New spec content:**")
            lines.append("")
            lines.append("| Spec | Value | Units |")
            lines.append("|------|-------|-------|")
            for name, spec in diff.new_specs.items():
                lines.append(f"| `{name}` | `{spec.value}` | `{spec.units}` |")
        return lines

    lines.append(f"### {diff.suite_name} ({diff.spec_type} spec \"{diff.spec_name}\")")
    if diff.added:
        lines.append("")
        lines.append("**Added:**")
        for name, spec in diff.added.items():
            lines.append(f"- `{name}`: value={spec.value}, units={spec.units}")
    if diff.removed:
        lines.append("")
        lines.append("**Removed:**")
        for name, spec in diff.removed.items():
            lines.append(f"- ~~`{name}`: value={spec.value}, units={spec.units}~~")
    if diff.changed:
        lines.append("")
        lines.append("**Changed:**")
        lines.append("| Spec | Field | Old | New |")
        lines.append("|------|-------|-----|-----|")
        for name, (old_s, new_s) in diff.changed.items():
            if old_s.value != new_s.value:
                lines.append(f"| `{name}` | value | `{old_s.value}` | `{_fmt_val(new_s.value)}` |")
            if old_s.units != new_s.units:
                lines.append(f"| `{name}` | units | `{old_s.units}` | `{_fmt_val(new_s.units)}` |")
            if old_s.comment != new_s.comment:
                lines.append(f"| `{name}` | comment | `{old_s.comment}` | `{_fmt_val(new_s.comment)}` |")
    return lines


def _format_wavetbl_block_markdown(block: "WaveTblBlock", marker: str) -> List[str]:
    """Format full WAVETBL block content in Markdown."""
    lines = []
    for name, group in block.pins_groups.items():
        if marker == "+":
            lines.append(f"- `{name}`")
        else:
            lines.append(f"- ~~`{name}`~~")
        for row in group.rows:
            if marker == "+":
                lines.append(f"  - `{row.label}` \"`{row.edge_spec}`\" `{row.state}`")
            else:
                lines.append(f"  - ~~`{row.label}` \"`{row.edge_spec}`\" `{row.state}`~~")
        if group.brk:
            if marker == "+":
                lines.append(f"  - `brk` \"`{group.brk}`\"")
            else:
                lines.append(f"  - ~~`brk` \"`{group.brk}`\"~~")
        if group.f:
            if marker == "+":
                lines.append(f"  - `f` \"`{group.f}`\"")
            else:
                lines.append(f"  - ~~`f` \"`{group.f}`\"~~")
    return lines


def _format_wavetbl_markdown(diff: WaveTblDiff) -> List[str]:
    """Format a single WaveTblDiff as Markdown lines."""
    lines = []
    if diff.replaced_from:
        lines.append(f"### {diff.suite_name}: WAVETBL Replaced: {diff.replaced_from} -> {diff.wavetbl_name}")
        if diff.new_block:
            lines.append("")
            lines.extend(_format_wavetbl_block_markdown(diff.new_block, "+"))
        return lines

    lines.append(f"### {diff.suite_name} (WAVETBL \"{diff.wavetbl_name}\")")

    # Whole block added/removed
    if diff.new_block and not diff.old_block:
        lines.append("")
        lines.append("#### WAVETBL Added")
        lines.append("")
        lines.extend(_format_wavetbl_block_markdown(diff.new_block, "+"))
    elif diff.old_block and not diff.new_block:
        lines.append("")
        lines.append("#### WAVETBL Removed")
        lines.append("")
        lines.extend(_format_wavetbl_block_markdown(diff.old_block, "-"))

    # Internal PINS changes (both blocks exist: same-name diff or replacement)
    if diff.pins_groups_added or diff.pins_groups_removed or diff.pins_groups_changed:
        lines.append("")
        lines.append("#### PINS Groups")
        lines.append("")

    if diff.pins_groups_added:
        lines.append("**Added:**")
        for name, group in diff.pins_groups_added.items():
            lines.append(f"- `{name}`")
            for row in group.rows:
                lines.append(f"  - `{row.label}` \"`{row.edge_spec}`\" `{row.state}`")
            if group.brk:
                lines.append(f"  - `brk` \"`{group.brk}`\"")
            if group.f:
                lines.append(f"  - `f` \"`{group.f}`\"")
        lines.append("")

    if diff.pins_groups_removed:
        lines.append("**Removed:**")
        for name, group in diff.pins_groups_removed.items():
            lines.append(f"- ~~`{name}`~~")
            for row in group.rows:
                lines.append(f"  - ~~`{row.label}` \"`{row.edge_spec}`\" `{row.state}`~~")
            if group.brk:
                lines.append(f"  - ~~`brk` \"`{group.brk}`\"~~")
            if group.f:
                lines.append(f"  - ~~`f` \"`{group.f}`\"~~")
        lines.append("")

    if diff.pins_groups_changed:
        lines.append("**Changed:**")
        lines.append("| PINS | Row | Field | Old | New |")
        lines.append("|------|-----|-------|-----|-----|")
        for name, pg_diff in diff.pins_groups_changed.items():
            for row in pg_diff.rows_added:
                lines.append(f"| `{name}` | `{row.label}` | added | | `{row.edge_spec}` `{row.state}` |")
            for row in pg_diff.rows_removed:
                lines.append(f"| `{name}` | `{row.label}` | removed | `{row.edge_spec}` `{row.state}` | |")
            for old_r, new_r in pg_diff.rows_changed:
                if old_r.edge_spec != new_r.edge_spec:
                    lines.append(f"| `{name}` | `{old_r.label}` | edge_spec | `{old_r.edge_spec}` | `{new_r.edge_spec}` |")
                if old_r.state != new_r.state:
                    lines.append(f"| `{name}` | `{old_r.label}` | state | `{old_r.state}` | `{new_r.state}` |")
            if pg_diff.brk_old != pg_diff.brk_new:
                lines.append(f"| `{name}` | `brk` | value | `{pg_diff.brk_old}` | `{pg_diff.brk_new}` |")
            if pg_diff.f_old != pg_diff.f_new:
                lines.append(f"| `{name}` | `f` | value | `{pg_diff.f_old}` | `{pg_diff.f_new}` |")

    return lines


def format_suite_markdown(report: SuiteConfigReport) -> str:
    """Format suite config diff as Markdown."""
    lines = []
    lines.append("## Suite Configuration Diff")
    lines.append("")
    lines.append(
        f"- **Common suites**: {len(report.common_suites)} "
        f"({len(report.suites_with_changes)} with changes)"
    )

    if report.skipped_suites:
        lines.append("")
        lines.append(f"- **Skipped** (not in test_suites): {len(report.skipped_suites)}")
        for name in report.skipped_suites:
            lines.append(f"  - `{name}`")

    for diff in report.diffs:
        if not diff.has_changes:
            continue

        lines.append("")
        lines.append(f"### {diff.suite_name}")

        if diff.changed:
            lines.append("")
            lines.append("| Key | Old Value | New Value |")
            lines.append("|-----|-----------|-----------|")
            for key, (old_val, new_val) in diff.changed.items():
                lines.append(f"| `{key}` | `{old_val}` | `{_fmt_val(new_val)}` |")

        if diff.added:
            lines.append("")
            lines.append("**Added:**")
            for key, val in diff.added.items():
                lines.append(f"- `{key}` = `{val}`")

        if diff.removed:
            lines.append("")
            lines.append("**Removed:**")
            for key, val in diff.removed.items():
                lines.append(f"- ~~`{key}` = `{val}`~~")

    return "\n".join(lines)


def format_markdown(report: DiffReport) -> str:
    """Format diff report as Markdown."""
    lines = []
    lines.append("# SMT7 Flow Diff Report")
    lines.append("")
    lines.append(f"- **Old**: `{report.old_file}` ({len(report.old_tests)} tests)")
    lines.append(f"- **New**: `{report.new_file}` ({len(report.new_tests)} tests)")
    lines.append("")

    if report.added:
        lines.append(f"## Added Tests ({len(report.added)})")
        for name in report.added:
            lines.append(f"- **{name}**")
        lines.append("")

    if report.removed:
        lines.append(f"## Removed Tests ({len(report.removed)})")
        for name in report.removed:
            lines.append(f"- ~~{name}~~")
        lines.append("")

    if report.moved:
        lines.append(f"## Moved Tests ({len(report.moved)})")
        for name in report.moved:
            entries = [d for d in report.diffs if d.suite_name == name and d.diff_type == DiffType.MOVED]
            for d in entries:
                old_pos = d.old_index + 1 if d.old_index is not None else '?'
                new_pos = d.new_index + 1 if d.new_index is not None else '?'
                lines.append(f"- **{name}**: position {old_pos} → {new_pos}")
        lines.append("")

    if report.order_changed:
        lines.append(f"## Order Changed Tests ({len(report.order_changed)})")
        for name in report.order_changed:
            lines.append(f"- **{name}**")
        lines.append("")

    unchanged_count = len(report.unchanged)
    lines.append(f"## Unchanged Tests: {unchanged_count}")
    lines.append("")

    # Summary table
    lines.append("## Summary")
    lines.append("| Metric | Count |")
    lines.append("|--------|-------|")
    lines.append(f"| Total Old Tests | {len(report.old_tests)} |")
    lines.append(f"| Total New Tests | {len(report.new_tests)} |")
    lines.append(f"| Added | {len(report.added)} |")
    lines.append(f"| Removed | {len(report.removed)} |")
    lines.append(f"| Moved | {len(report.moved)} |")
    lines.append(f"| Order Changed | {len(report.order_changed)} |")
    lines.append(f"| Unchanged | {unchanged_count} |")

    if report.suite_config_report is not None:
        lines.append("")
        lines.append(format_suite_markdown(report.suite_config_report))

    if report.level_spec_diffs:
        lines.append("")
        lines.append("## Level Spec Diff")
        lines.append("")
        for diff in report.level_spec_diffs:
            lines.extend(_format_level_spec_markdown(diff))

    if report.eqnset_diffs:
        lines.append("")
        lines.append("## EQNSET Diff")
        lines.append("")
        for diff in report.eqnset_diffs:
            lines.extend(_format_eqnset_markdown(diff))

    if report.timing_spec_diffs:
        lines.append("")
        lines.append("## Timing Spec Diff")
        lines.append("")
        for diff in report.timing_spec_diffs:
            lines.extend(_format_timing_spec_markdown(diff))

    if report.timing_eqnset_diffs:
        lines.append("")
        lines.append("## Timing EQNSET Diff")
        lines.append("")
        for diff in report.timing_eqnset_diffs:
            lines.extend(_format_timing_eqnset_markdown(diff))

    if report.timing_wavetbl_diffs:
        lines.append("")
        lines.append("## Timing Wavetable Diff")
        lines.append("")
        for diff in report.timing_wavetbl_diffs:
            lines.extend(_format_wavetbl_markdown(diff))

    return "\n".join(lines)
