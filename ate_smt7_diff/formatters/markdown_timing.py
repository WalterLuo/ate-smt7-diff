#!/usr/bin/env python3
"""Markdown formatting for timing spec, EQNSET, and wavetable diffs."""

from ate_smt7_diff.formatters.shared import fields_str, field_changes, fmt_val
from ate_smt7_diff.models import (
    TimingEqnSetBlock,
    TimingEqnSetDiff,
    TimingSpecDiff,
    WaveTblBlock,
    WaveTblDiff,
)


# ---------------------------------------------------------------------------
# Timing EQNSET
# ---------------------------------------------------------------------------


def _format_eqnset_block_markdown(block: TimingEqnSetBlock) -> list[str]:
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
            fstr = fields_str(cfg)
            lines.append(f"| `{name}` | {fstr} |")
    if block.timingsets:
        lines.append("")
        lines.append("| TIMINGSET | Fields |")
        lines.append("|-----------|--------|")
        for idx, cfg in block.timingsets.items():
            fstr = fields_str(cfg)
            lines.append(f"| {idx} | {fstr} |")
    return lines


def _aggregate_timing_eqnset_replacements(
    diffs: list[TimingEqnSetDiff],
) -> dict[tuple[int, str, int, str], list[TimingEqnSetDiff]]:
    """Group timing EQNSET diffs that are identical replacements."""
    groups: dict[tuple[int, str, int, str], list[TimingEqnSetDiff]] = {}
    for diff in diffs:
        if diff.replaced_from_name:
            key = (diff.replaced_from_index, diff.replaced_from_name, diff.eqnset_index, diff.eqnset_name)
            groups.setdefault(key, []).append(diff)
    return groups


def _format_timing_eqnset_markdown(diff: TimingEqnSetDiff) -> list[str]:
    """Format a single TimingEqnSetDiff as Markdown lines."""
    lines = []

    if diff.replaced_from_name:
        lines.append(
            f"### {diff.suite_name}: Timing EQNSET Replaced: "
            f'{diff.replaced_from_index} "{diff.replaced_from_name}" -> '
            f'{diff.eqnset_index} "{diff.eqnset_name}"'
        )
        if diff.new_block:
            lines.append("")
            lines.append("**New EQNSET content:**")
            lines.extend(_format_eqnset_block_markdown(diff.new_block))
        return lines

    lines.append(f'### {diff.suite_name} (EQNSET {diff.eqnset_index} "{diff.eqnset_name}")')

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
                    lines.append(
                        f"| `{name}` | value | `{old_s.value}` | `{fmt_val(new_s.value)}` |"
                    )
                if old_s.units != new_s.units:
                    lines.append(
                        f"| `{name}` | units | `{old_s.units}` | `{fmt_val(new_s.units)}` |"
                    )
                if old_s.comment != new_s.comment:
                    lines.append(
                        f"| `{name}` | comment | `{old_s.comment}` | `{fmt_val(new_s.comment)}` |"
                    )

    if diff.pins_added or diff.pins_removed or diff.pins_changed:
        lines.append("")
        lines.append("#### PINS")
        lines.append("")
        if diff.pins_added:
            lines.append("**Added:**")
            for name, cfg in diff.pins_added.items():
                fstr = fields_str(cfg)
                lines.append(f"- `{name}`: {fstr}")
            lines.append("")
        if diff.pins_removed:
            lines.append("**Removed:**")
            for name, cfg in diff.pins_removed.items():
                fstr = fields_str(cfg)
                lines.append(f"- ~~`{name}`: {fstr}~~")
            lines.append("")
        if diff.pins_changed:
            lines.append("**Changed:**")
            lines.append("")
            lines.append("| PINS | Field | Old | New |")
            lines.append("|------|-------|-----|-----|")
            for name, (old_c, new_c) in diff.pins_changed.items():
                for key, old_val, new_val in field_changes(old_c, new_c):
                    lines.append(f"| `{name}` | {key} | `{old_val}` | `{fmt_val(new_val)}` |")

    if diff.timingsets_added or diff.timingsets_removed or diff.timingsets_changed:
        lines.append("")
        lines.append("#### TIMINGSET")
        lines.append("")
        if diff.timingsets_added:
            lines.append("**Added:**")
            for idx, cfg in diff.timingsets_added.items():
                fstr = fields_str(cfg)
                lines.append(f"- TIMINGSET {idx}: {fstr}")
            lines.append("")
        if diff.timingsets_removed:
            lines.append("**Removed:**")
            for idx, cfg in diff.timingsets_removed.items():
                fstr = fields_str(cfg)
                lines.append(f"- ~~TIMINGSET {idx}: {fstr}~~")
            lines.append("")
        if diff.timingsets_changed:
            lines.append("**Changed:**")
            lines.append("")
            lines.append("| TIMINGSET | Field | Old | New |")
            lines.append("|-----------|-------|-----|-----|")
            for idx, (old_c, new_c) in diff.timingsets_changed.items():
                for key, old_val, new_val in field_changes(old_c, new_c):
                    lines.append(f"| {idx} | {key} | `{old_val}` | `{fmt_val(new_val)}` |")

    return lines


# ---------------------------------------------------------------------------
# Timing spec
# ---------------------------------------------------------------------------


def _format_timing_spec_markdown(diff: TimingSpecDiff) -> list[str]:
    """Format a single TimingSpecDiff as Markdown lines."""
    lines = []

    if diff.replaced_from:
        lines.append(
            f"### {diff.suite_name}: Timing Spec Replaced: {diff.replaced_from} -> {diff.spec_name}"
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

    lines.append(f'### {diff.suite_name} ({diff.spec_type} spec "{diff.spec_name}")')
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
        lines.append("")
        lines.append("| Spec | Field | Old | New |")
        lines.append("|------|-------|-----|-----|")
        for name, (old_s, new_s) in diff.changed.items():
            if old_s.value != new_s.value:
                lines.append(f"| `{name}` | value | `{old_s.value}` | `{fmt_val(new_s.value)}` |")
            if old_s.units != new_s.units:
                lines.append(f"| `{name}` | units | `{old_s.units}` | `{fmt_val(new_s.units)}` |")
            if old_s.comment != new_s.comment:
                lines.append(
                    f"| `{name}` | comment | `{old_s.comment}` | `{fmt_val(new_s.comment)}` |"
                )
    return lines


# ---------------------------------------------------------------------------
# Wavetable
# ---------------------------------------------------------------------------


def _format_wavetbl_block_markdown(block: "WaveTblBlock", marker: str) -> list[str]:
    """Format full WAVETBL block content in Markdown."""
    lines = []
    for name, group in block.pins_groups.items():
        if marker == "+":
            lines.append(f"- `{name}`")
        else:
            lines.append(f"- ~~`{name}`~~")
        for row in group.rows:
            if marker == "+":
                lines.append(f'  - `{row.label}` "`{row.edge_spec}`" `{row.state}`')
            else:
                lines.append(f'  - ~~`{row.label}` "`{row.edge_spec}`" `{row.state}`~~')
        if group.brk:
            if marker == "+":
                lines.append(f'  - `brk` "`{group.brk}`"')
            else:
                lines.append(f'  - ~~`brk` "`{group.brk}`"~~')
        if group.f:
            if marker == "+":
                lines.append(f'  - `f` "`{group.f}`"')
            else:
                lines.append(f'  - ~~`f` "`{group.f}`"~~')
    return lines


def _aggregate_wavetbl_replacements(
    diffs: list[WaveTblDiff],
) -> dict[tuple[str, str], list[WaveTblDiff]]:
    """Group wavetable diffs that are identical replacements."""
    groups: dict[tuple[str, str], list[WaveTblDiff]] = {}
    for diff in diffs:
        if diff.replaced_from:
            key = (diff.replaced_from, diff.wavetbl_name)
            groups.setdefault(key, []).append(diff)
    return groups


def _format_wavetbl_markdown(diff: WaveTblDiff) -> list[str]:
    """Format a single WaveTblDiff as Markdown lines."""
    lines = []
    if diff.replaced_from:
        lines.append(
            f"### {diff.suite_name}: WAVETBL Replaced: {diff.replaced_from} -> {diff.wavetbl_name}"
        )
        if diff.new_block:
            lines.append("")
            lines.extend(_format_wavetbl_block_markdown(diff.new_block, "+"))
        return lines

    lines.append(f'### {diff.suite_name} (WAVETBL "{diff.wavetbl_name}")')

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

    if diff.pins_groups_added or diff.pins_groups_removed or diff.pins_groups_changed:
        lines.append("")
        lines.append("#### PINS Groups")
        lines.append("")

    if diff.pins_groups_added:
        lines.append("**Added:**")
        for name, group in diff.pins_groups_added.items():
            lines.append(f"- `{name}`")
            for row in group.rows:
                lines.append(f'  - `{row.label}` "`{row.edge_spec}`" `{row.state}`')
            if group.brk:
                lines.append(f'  - `brk` "`{group.brk}`"')
            if group.f:
                lines.append(f'  - `f` "`{group.f}`"')
        lines.append("")

    if diff.pins_groups_removed:
        lines.append("**Removed:**")
        for name, group in diff.pins_groups_removed.items():
            lines.append(f"- ~~`{name}`~~")
            for row in group.rows:
                lines.append(f'  - ~~`{row.label}` "`{row.edge_spec}`" `{row.state}`~~')
            if group.brk:
                lines.append(f'  - ~~`brk` "`{group.brk}`"~~')
            if group.f:
                lines.append(f'  - ~~`f` "`{group.f}`"~~')
        lines.append("")

    if diff.pins_groups_changed:
        lines.append("**Changed:**")
        lines.append("")
        lines.append("| PINS | Row | Field | Old | New |")
        lines.append("|------|-----|-------|-----|-----|")
        for name, pg_diff in diff.pins_groups_changed.items():
            for row in pg_diff.rows_added:
                lines.append(
                    f"| `{name}` | `{row.label}` | added | | `{row.edge_spec}` `{row.state}` |"
                )
            for row in pg_diff.rows_removed:
                lines.append(
                    f"| `{name}` | `{row.label}` | removed | `{row.edge_spec}` `{row.state}` | |"
                )
            for old_r, new_r in pg_diff.rows_changed:
                if old_r.edge_spec != new_r.edge_spec:
                    lines.append(
                        f"| `{name}` | `{old_r.label}` | edge_spec | `{old_r.edge_spec}` | `{new_r.edge_spec}` |"
                    )
                if old_r.state != new_r.state:
                    lines.append(
                        f"| `{name}` | `{old_r.label}` | state | `{old_r.state}` | `{new_r.state}` |"
                    )
            if pg_diff.brk_old != pg_diff.brk_new:
                lines.append(
                    f"| `{name}` | `brk` | value | `{pg_diff.brk_old}` | `{pg_diff.brk_new}` |"
                )
            if pg_diff.f_old != pg_diff.f_new:
                lines.append(f"| `{name}` | `f` | value | `{pg_diff.f_old}` | `{pg_diff.f_new}` |")

    return lines
