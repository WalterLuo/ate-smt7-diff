#!/usr/bin/env python3
"""Shared serialization and formatting helpers for all output formatters."""

from typing import Callable, TypeVar

from ate_smt7_diff.models import (
    LevelSetPinConfig,
    LevelSpec,
    TestTableRow,
    TimingSpec,
    VectorPatternMapping,
    WaveTblPinsGroup,
    WaveTblRow,
)

T = TypeVar("T")


# ---------------------------------------------------------------------------
# Value formatting
# ---------------------------------------------------------------------------


def fmt_val(val: str) -> str:
    """Format a value, showing 'removed' when empty."""
    return val if val else "removed"


def truncate_name(name: str, max_len: int = 60) -> str:
    """Truncate a long pin group name for compact display."""
    if len(name) <= max_len:
        return name
    head = name[:30]
    tail = name[-25:]
    return f"{head}...{tail}"


# ---------------------------------------------------------------------------
# Config object helpers
# ---------------------------------------------------------------------------


def fields_str(cfg) -> str:
    """Format any config object's fields as 'k=v, k=v'."""
    return ", ".join(f"{k}={v}" for k, v in cfg.all_fields().items())


def field_changes(old_cfg, new_cfg) -> list[tuple[str, str, str]]:
    """Return sorted list of (key, old_val, new_val) for fields that differ.

    Both configs must implement ``all_fields()`` returning a dict.
    """
    old_fields = old_cfg.all_fields()
    new_fields = new_cfg.all_fields()
    changes: list[tuple[str, str, str]] = []
    for key in sorted(set(old_fields.keys()) | set(new_fields.keys())):
        old_val = old_fields.get(key, "")
        new_val = new_fields.get(key, "")
        if old_val != new_val:
            changes.append((key, old_val, new_val))
    return changes


# ---------------------------------------------------------------------------
# Model-to-dict serialization (used by JSON formatter and reusable by others)
# ---------------------------------------------------------------------------


def timing_spec_dict(spec: TimingSpec) -> dict:
    return {"value": spec.value, "units": spec.units, "comment": spec.comment}


def level_spec_dict(spec: LevelSpec) -> dict:
    return {
        "actual": spec.actual,
        "min": spec.min,
        "max": spec.max,
        "units": spec.units,
        "comment": spec.comment,
    }


def wavetbl_row_dict(row: WaveTblRow) -> dict:
    return {"label": row.label, "edge_spec": row.edge_spec, "state": row.state}


def wavetbl_pins_group_dict(group: WaveTblPinsGroup) -> dict:
    return {
        "rows": [wavetbl_row_dict(r) for r in group.rows],
        "brk": group.brk,
        "f": group.f,
    }


def testtable_row_dict(row: TestTableRow) -> dict:
    return {
        "test_name": row.test_name,
        "test_number": row.test_number,
        "columns": row.columns,
    }


def vector_mapping_dict(m: VectorPatternMapping) -> dict:
    return {
        "pattern_name": m.pattern_name,
        "mapped_file": m.mapped_file,
        "is_direct": m.is_direct,
    }


# ---------------------------------------------------------------------------
# ARC (added/removed/changed) serialization helpers
# ---------------------------------------------------------------------------


def arc(
    added: dict[str, T],
    removed: dict[str, T],
    changed: dict[str, tuple[T, T]],
    serialize: Callable[[T], dict],
) -> dict:
    """Build added/removed/changed dict."""
    return {
        "added": {k: serialize(v) for k, v in added.items()},
        "removed": {k: serialize(v) for k, v in removed.items()},
        "changed": {
            k: {"old": serialize(old_v), "new": serialize(new_v)}
            for k, (old_v, new_v) in changed.items()
        },
    }


def arc_all_fields(
    added: dict[str, LevelSetPinConfig],
    removed: dict[str, LevelSetPinConfig],
    changed: dict[str, tuple[LevelSetPinConfig, LevelSetPinConfig]],
) -> dict:
    return arc(added, removed, changed, lambda cfg: cfg.all_fields())


def timing_arc(
    added: dict[str, TimingSpec],
    removed: dict[str, TimingSpec],
    changed: dict[str, tuple[TimingSpec, TimingSpec]],
) -> dict:
    return arc(added, removed, changed, timing_spec_dict)


def levelset_group_arc(
    added: dict[int, dict[str, LevelSetPinConfig]],
    removed: dict[int, dict[str, LevelSetPinConfig]],
    changed: dict[int, dict[str, tuple[LevelSetPinConfig, LevelSetPinConfig]]],
) -> dict:
    """Serialize LEVELSET pin groups (outer key is stringified int)."""
    return {
        "added": {
            str(idx): {name: cfg.all_fields() for name, cfg in pins.items()}
            for idx, pins in added.items()
        },
        "removed": {
            str(idx): {name: cfg.all_fields() for name, cfg in pins.items()}
            for idx, pins in removed.items()
        },
        "changed": {
            str(idx): {
                name: {"old": old_c.all_fields(), "new": new_c.all_fields()}
                for name, (old_c, new_c) in pins.items()
            }
            for idx, pins in changed.items()
        },
    }


def timing_eqnset_block_dict(block) -> dict:
    return {
        "specs": {
            name: timing_spec_dict(spec) for name, spec in block.specs.items()
        },
        "pins": {
            name: cfg.all_fields() for name, cfg in block.pins_groups.items()
        },
        "timingsets": {
            str(idx): cfg.all_fields() for idx, cfg in block.timingsets.items()
        },
    }
