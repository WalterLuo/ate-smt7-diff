#!/usr/bin/env python3
"""Console formatting for level spec and EQNSET diffs."""

from ate_smt7_diff.formatters.shared import field_changes, fields_str, fmt_val
from ate_smt7_diff.models import EqnSetDiff, LevelSpecDiff


def _format_level_spec_console(diff: LevelSpecDiff) -> list[str]:
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
            changes.append(f"actual {old_s.actual} -> {fmt_val(new_s.actual)}")
        if old_s.min != new_s.min:
            changes.append(f"min {old_s.min} -> {fmt_val(new_s.min)}")
        if old_s.max != new_s.max:
            changes.append(f"max {old_s.max} -> {fmt_val(new_s.max)}")
        if old_s.units != new_s.units:
            changes.append(f"units {old_s.units} -> {fmt_val(new_s.units)}")
        if old_s.comment != new_s.comment:
            changes.append(f"comment {old_s.comment} -> {fmt_val(new_s.comment)}")
        lines.append(f"    ~ {name}: {', '.join(changes)}")
    return lines


def _format_eqnset_console(diff: EqnSetDiff) -> list[str]:
    """Format a single EqnSetDiff as console lines."""
    lines = []
    lines.append(f'{diff.suite_name} (EQNSET {diff.eqnset_index} "{diff.eqnset_name}"):')
    if diff.dpspins_added:
        lines.append("  DPSPINS Added:")
        for name, cfg in diff.dpspins_added.items():
            lines.append(f"    + {name}: {fields_str(cfg)}")
    if diff.dpspins_removed:
        lines.append("  DPSPINS Removed:")
        for name, cfg in diff.dpspins_removed.items():
            lines.append(f"    - {name}: {fields_str(cfg)}")
    if diff.dpspins_changed:
        lines.append("  DPSPINS Changed:")
        for name, (old_c, new_c) in diff.dpspins_changed.items():
            changes = [f"{k} {ov} -> {fmt_val(nv)}" for k, ov, nv in field_changes(old_c, new_c)]
            lines.append(f"    ~ {name}: {', '.join(changes)}")
    if diff.levelsets_added:
        lines.append("  LEVELSET Added:")
        for idx, pins in diff.levelsets_added.items():
            lines.append(f"    + LEVELSET {idx}:")
            for name, cfg in pins.items():
                lines.append(
                    f"      + {name}: vih={cfg.vih}, vil={cfg.vil}, voh={cfg.voh}, vol={cfg.vol}"
                )
    if diff.levelsets_removed:
        lines.append("  LEVELSET Removed:")
        for idx, pins in diff.levelsets_removed.items():
            lines.append(f"    - LEVELSET {idx}:")
            for name, cfg in pins.items():
                lines.append(
                    f"      - {name}: vih={cfg.vih}, vil={cfg.vil}, voh={cfg.voh}, vol={cfg.vol}"
                )
    if diff.levelsets_changed:
        lines.append("  LEVELSET Changed:")
        for idx, pins in diff.levelsets_changed.items():
            lines.append(f"    ~ LEVELSET {idx}:")
            for name, (old_c, new_c) in pins.items():
                changes = [f"{k} {ov} -> {fmt_val(nv)}" for k, ov, nv in field_changes(old_c, new_c)]
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
