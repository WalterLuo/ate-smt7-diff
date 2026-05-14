#!/usr/bin/env python3
"""Markdown formatting for level spec and EQNSET diffs."""

from ate_smt7_diff.formatters.shared import fields_str, field_changes, fmt_val
from ate_smt7_diff.models import EqnSetDiff, LevelSpecDiff


# ---------------------------------------------------------------------------
# Level spec
# ---------------------------------------------------------------------------


def _format_level_spec_markdown(diff: LevelSpecDiff) -> list[str]:
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
        lines.append("")
        lines.append("| Spec | Field | Old | New |")
        lines.append("|------|-------|-----|-----|")
        for name, (old_s, new_s) in diff.changed.items():
            if old_s.actual != new_s.actual:
                lines.append(
                    f"| `{name}` | actual | `{old_s.actual}` | `{fmt_val(new_s.actual)}` |"
                )
            if old_s.min != new_s.min:
                lines.append(f"| `{name}` | min | `{old_s.min}` | `{fmt_val(new_s.min)}` |")
            if old_s.max != new_s.max:
                lines.append(f"| `{name}` | max | `{old_s.max}` | `{fmt_val(new_s.max)}` |")
            if old_s.units != new_s.units:
                lines.append(f"| `{name}` | units | `{old_s.units}` | `{fmt_val(new_s.units)}` |")
            if old_s.comment != new_s.comment:
                lines.append(
                    f"| `{name}` | comment | `{old_s.comment}` | `{fmt_val(new_s.comment)}` |"
                )
    return lines


# ---------------------------------------------------------------------------
# EQNSET (level)
# ---------------------------------------------------------------------------


def _eqnset_change_key(diff: EqnSetDiff) -> tuple:
    """Return a hashable key representing the structural changes of an EqnSetDiff.

    Suites with identical keys have identical add/remove/change patterns.
    """

    def _dpspin_cfg_items(cfg_dict):
        return tuple(
            (name, tuple(sorted(cfg.all_fields().items())))
            for name, cfg in sorted(cfg_dict.items())
        )

    def _levelset_items(ls_dict):
        return tuple(
            (
                idx,
                tuple(
                    (name, tuple(sorted(cfg.all_fields().items())))
                    for name, cfg in sorted(pins.items())
                ),
            )
            for idx, pins in sorted(ls_dict.items())
        )

    def _changed_dpspin_items(chg_dict):
        return tuple(
            (
                name,
                tuple(sorted(old_c.all_fields().items())),
                tuple(sorted(new_c.all_fields().items())),
            )
            for name, (old_c, new_c) in sorted(chg_dict.items())
        )

    def _changed_levelset_items(chg_dict):
        return tuple(
            (
                idx,
                tuple(
                    (
                        name,
                        tuple(sorted(old_c.all_fields().items())),
                        tuple(sorted(new_c.all_fields().items())),
                    )
                    for name, (old_c, new_c) in sorted(pins.items())
                ),
            )
            for idx, pins in sorted(chg_dict.items())
        )

    return (
        _dpspin_cfg_items(diff.dpspins_added),
        _dpspin_cfg_items(diff.dpspins_removed),
        _changed_dpspin_items(diff.dpspins_changed),
        _levelset_items(diff.levelsets_added),
        _levelset_items(diff.levelsets_removed),
        _changed_levelset_items(diff.levelsets_changed),
    )


def _aggregate_eqnset_diffs(diffs: list[EqnSetDiff]) -> tuple[list[EqnSetDiff], dict[tuple, list[str]]]:
    """Separate unique diffs from common-pattern diffs.

    Returns ``(unique_diffs, pattern_groups)`` where pattern_groups maps a
    change-key to the list of suite names that share that pattern.
    """
    groups: dict[tuple, list[str]] = {}
    for diff in diffs:
        key = _eqnset_change_key(diff)
        groups.setdefault(key, []).append(diff.suite_name)

    seen_keys: set[tuple] = set()
    unique_diffs: list[EqnSetDiff] = []
    pattern_groups: dict[tuple, list[str]] = {}
    for diff in diffs:
        key = _eqnset_change_key(diff)
        if key in seen_keys:
            continue
        seen_keys.add(key)
        if len(groups[key]) > 1:
            pattern_groups[key] = groups[key]
        else:
            unique_diffs.append(diff)

    return unique_diffs, pattern_groups


def _format_eqnset_pattern_markdown(pattern_diff: EqnSetDiff, suites: list[str]) -> list[str]:
    """Format an aggregated EQNSET pattern as Markdown lines."""
    lines = []
    lines.append(
        f"> **Note:** The following identical EQNSET changes apply to **{len(suites)} suites**."
    )
    lines.append("")
    lines.append("### Common Change Pattern")

    if pattern_diff.dpspins_added or pattern_diff.dpspins_removed or pattern_diff.dpspins_changed:
        lines.append("")
        lines.append("| Component | Change |")
        lines.append("|-----------|--------|")
        for name, cfg in sorted(pattern_diff.dpspins_added.items()):
            fstr = fields_str(cfg)
            lines.append(f"| DPSPINS | `{name}`: {fstr} (added) |")
        for name, cfg in sorted(pattern_diff.dpspins_removed.items()):
            fstr = fields_str(cfg)
            lines.append(f"| DPSPINS | `{name}`: {fstr} (removed) |")
        for name, (old_c, new_c) in sorted(pattern_diff.dpspins_changed.items()):
            changes = []
            for key, old_val, new_val in field_changes(old_c, new_c):
                if not new_val:
                    changes.append(f"`{key} {old_val}` removed")
                else:
                    changes.append(f"`{key}` {old_val} -> {new_val}")
            if changes:
                lines.append(f"| DPSPINS | `{name}`: {', '.join(changes)} |")

    if pattern_diff.levelsets_added or pattern_diff.levelsets_removed or pattern_diff.levelsets_changed:
        for idx, pins in sorted(pattern_diff.levelsets_added.items()):
            for name, cfg in sorted(pins.items()):
                fstr = fields_str(cfg)
                lines.append(f"| LEVELSET {idx} | `{name}`: {fstr} (added) |")
        for idx, pins in sorted(pattern_diff.levelsets_removed.items()):
            for name, cfg in sorted(pins.items()):
                fstr = fields_str(cfg)
                lines.append(f"| LEVELSET {idx} | `{name}`: {fstr} (removed) |")
        for idx, pins_chg in sorted(pattern_diff.levelsets_changed.items()):
            for name, (old_c, new_c) in sorted(pins_chg.items()):
                changes = []
                for key, old_val, new_val in field_changes(old_c, new_c):
                    if not new_val:
                        changes.append(f"`{key} {old_val}` removed")
                    else:
                        changes.append(f"`{key}` {old_val} -> {new_val}")
                if changes:
                    lines.append(f"| LEVELSET {idx} | `{name}`: {', '.join(changes)} |")

    lines.append("")
    lines.append("### Affected Suites")
    lines.append(", ".join(f"`{s}`" for s in suites))
    return lines


def _format_eqnset_markdown(diff: EqnSetDiff) -> list[str]:
    """Format a single EqnSetDiff as Markdown lines."""
    lines = []
    lines.append(f'### {diff.suite_name} (EQNSET {diff.eqnset_index} "{diff.eqnset_name}")')

    if diff.dpspins_added or diff.dpspins_removed or diff.dpspins_changed:
        lines.append("")
        lines.append("#### DPSPINS")
        lines.append("")
        if diff.dpspins_added:
            lines.append("**Added:**")
            for name, cfg in diff.dpspins_added.items():
                fstr = fields_str(cfg)
                lines.append(f"- `{name}`: {fstr}")
            lines.append("")
        if diff.dpspins_removed:
            lines.append("**Removed:**")
            for name, cfg in diff.dpspins_removed.items():
                fstr = fields_str(cfg)
                lines.append(f"- ~~`{name}`: {fstr}~~")
            lines.append("")
        if diff.dpspins_changed:
            lines.append("**Changed:**")
            lines.append("")
            lines.append("| Pin | Field | Old | New |")
            lines.append("|-----|-------|-----|-----|")
            for name, (old_c, new_c) in diff.dpspins_changed.items():
                for key, old_val, new_val in field_changes(old_c, new_c):
                    lines.append(f"| `{name}` | {key} | `{old_val}` | `{fmt_val(new_val)}` |")

    if diff.levelsets_added or diff.levelsets_removed or diff.levelsets_changed:
        lines.append("")
        lines.append("#### LEVELSET")
        lines.append("")
        if diff.levelsets_added:
            lines.append("**Added:**")
            for idx, pins in diff.levelsets_added.items():
                lines.append(f"- LEVELSET {idx}:")
                for name, cfg in pins.items():
                    fstr = fields_str(cfg)
                    lines.append(f"  - `{name}`: {fstr}")
            lines.append("")
        if diff.levelsets_removed:
            lines.append("**Removed:**")
            for idx, pins in diff.levelsets_removed.items():
                lines.append(f"- LEVELSET {idx}:")
                for name, cfg in pins.items():
                    fstr = fields_str(cfg)
                    lines.append(f"  - ~~`{name}`: {fstr}~~")
            lines.append("")
        if diff.levelsets_changed:
            lines.append("**Changed:**")
            lines.append("")
            lines.append("| LEVELSET | PINS | Field | Old | New |")
            lines.append("|----------|------|-------|-----|-----|")
            for idx, pins in diff.levelsets_changed.items():
                for name, (old_c, new_c) in pins.items():
                    for key, old_val, new_val in field_changes(old_c, new_c):
                        lines.append(
                            f"| {idx} | `{name}` | {key} | `{old_val}` | `{fmt_val(new_val)}` |"
                        )

    return lines
