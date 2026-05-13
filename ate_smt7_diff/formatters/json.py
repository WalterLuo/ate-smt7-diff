#!/usr/bin/env python3
"""
JSON formatter for diff reports.
"""

import json
from typing import Callable, TypeVar

from ate_smt7_diff.models import (
    DiffReport,
    LevelSetPinConfig,
    LevelSpec,
    SuiteConfigReport,
    TestTableRow,
    TimingSpec,
    VectorPatternMapping,
    WaveTblPinsGroup,
    WaveTblRow,
)

T = TypeVar("T")


def _timing_spec_dict(spec: TimingSpec) -> dict:
    return {"value": spec.value, "units": spec.units, "comment": spec.comment}


def _level_spec_dict(spec: LevelSpec) -> dict:
    return {
        "actual": spec.actual,
        "min": spec.min,
        "max": spec.max,
        "units": spec.units,
        "comment": spec.comment,
    }


def _wavetbl_row_dict(row: WaveTblRow) -> dict:
    return {"label": row.label, "edge_spec": row.edge_spec, "state": row.state}


def _wavetbl_pins_group_dict(group: WaveTblPinsGroup) -> dict:
    return {
        "rows": [_wavetbl_row_dict(r) for r in group.rows],
        "brk": group.brk,
        "f": group.f,
    }


def _testtable_row_dict(row: TestTableRow) -> dict:
    return {
        "test_name": row.test_name,
        "test_number": row.test_number,
        "columns": row.columns,
    }


def _vector_mapping_dict(m: VectorPatternMapping) -> dict:
    return {
        "pattern_name": m.pattern_name,
        "mapped_file": m.mapped_file,
        "is_direct": m.is_direct,
    }


def _arc(
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


def _arc_all_fields(
    added: dict[str, LevelSetPinConfig],
    removed: dict[str, LevelSetPinConfig],
    changed: dict[str, tuple[LevelSetPinConfig, LevelSetPinConfig]],
) -> dict:
    return _arc(added, removed, changed, lambda cfg: cfg.all_fields())


def _timing_arc(
    added: dict[str, TimingSpec],
    removed: dict[str, TimingSpec],
    changed: dict[str, tuple[TimingSpec, TimingSpec]],
) -> dict:
    return _arc(added, removed, changed, _timing_spec_dict)


def _levelset_group_arc(
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


def _timing_eqnset_block_dict(block) -> dict:
    return {
        "specs": {
            name: _timing_spec_dict(spec) for name, spec in block.specs.items()
        },
        "pins": {
            name: cfg.all_fields() for name, cfg in block.pins_groups.items()
        },
        "timingsets": {
            str(idx): cfg.all_fields() for idx, cfg in block.timingsets.items()
        },
    }


def format_suite_json(report: SuiteConfigReport) -> dict:
    """Format suite config diff as a JSON-serializable dict."""
    diffs = []
    for diff in report.diffs:
        if not diff.has_changes:
            continue
        diffs.append(
            {
                "suite_name": diff.suite_name,
                **_arc(diff.added, diff.removed, diff.changed, lambda v: v),
            }
        )

    return {
        "suite_config_diff": {
            "common_suites_count": len(report.common_suites),
            "suites_with_changes_count": len(report.suites_with_changes),
            "skipped_suites": report.skipped_suites,
            "diffs": diffs,
        }
    }


def format_json(report: DiffReport) -> str:
    """Format diff report as strict JSON per user specification."""
    # Build order_changed entries with first matched occurrence positions
    order_changed_entries = []

    old_pos_map: dict[str, list[int]] = {}
    for i, t in enumerate(report.old_tests):
        old_pos_map.setdefault(t.suite_name, []).append(i)

    new_pos_map: dict[str, list[int]] = {}
    for i, t in enumerate(report.new_tests):
        new_pos_map.setdefault(t.suite_name, []).append(i)

    for name in report.order_changed:
        old_order = old_pos_map.get(name, [None])[0]
        new_order = new_pos_map.get(name, [None])[0]
        order_changed_entries.append(
            {
                "test_name": name,
                "old_order": (old_order + 1) if old_order is not None else None,
                "new_order": (new_order + 1) if new_order is not None else None,
            }
        )

    result = {
        "added_tests": report.added,
        "removed_tests": report.removed,
        "order_changed": order_changed_entries,
        "summary": {
            "added_count": len(report.added),
            "removed_count": len(report.removed),
            "order_changed_count": len(report.order_changed),
        },
    }

    if report.suite_config_report is not None:
        suite_json = format_suite_json(report.suite_config_report)
        result["suite_config_diff"] = suite_json["suite_config_diff"]

    if report.level_spec_diffs:
        result["level_spec_diff"] = [
            {
                "suite_name": diff.suite_name,
                **_arc(diff.added, diff.removed, diff.changed, _level_spec_dict),
            }
            for diff in report.level_spec_diffs
        ]

    if report.eqnset_diffs:
        result["eqnset_diff"] = [
            {
                "suite_name": diff.suite_name,
                "eqnset_index": diff.eqnset_index,
                "eqnset_name": diff.eqnset_name,
                "dpspins": _arc_all_fields(
                    diff.dpspins_added, diff.dpspins_removed, diff.dpspins_changed
                ),
                "levelsets": _levelset_group_arc(
                    diff.levelsets_added, diff.levelsets_removed, diff.levelsets_changed
                ),
            }
            for diff in report.eqnset_diffs
        ]

    if report.timing_spec_diffs:
        result["timing_spec_diff"] = [
            {
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
            for diff in report.timing_spec_diffs
        ]

    if report.timing_eqnset_diffs:
        result["timing_eqnset_diff"] = [
            {
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
            for diff in report.timing_eqnset_diffs
        ]

    if report.timing_wavetbl_diffs:
        result["timing_wavetbl_diff"] = [
            {
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
            for diff in report.timing_wavetbl_diffs
        ]

    if report.testtable_diffs:
        result["testtable_diff"] = [
            {
                "suite_name": diff.suite_name,
                "rows_added": [_testtable_row_dict(r) for r in diff.rows_added],
                "rows_removed": [_testtable_row_dict(r) for r in diff.rows_removed],
                "rows_changed": [
                    {
                        "test_name": rd.test_name,
                        "test_number": rd.test_number,
                        "changed": {
                            col: {"old": old_val, "new": new_val}
                            for col, (old_val, new_val) in rd.changed.items()
                        },
                    }
                    for rd in diff.rows_changed
                ],
            }
            for diff in report.testtable_diffs
        ]

    if report.vector_diffs:
        result["vector_diff"] = [
            {
                "suite_name": diff.suite_name,
                "diff_type": diff.diff_type,
                "old_mappings": [
                    _vector_mapping_dict(m) for m in (diff.old_mappings or ())
                ],
                "new_mappings": [
                    _vector_mapping_dict(m) for m in (diff.new_mappings or ())
                ],
                "file_date_changes": [
                    {
                        "file_path": fc.file_path,
                        "old_mtime": fc.old_mtime,
                        "new_mtime": fc.new_mtime,
                    }
                    for fc in diff.file_date_changes
                ],
            }
            for diff in report.vector_diffs
        ]

    if report.testmethod_diffs:
        result["testmethod_diff"] = [
            {
                "suite_name": diff.suite_name,
                "diff_type": diff.diff_type,
                "old_tm_id": diff.old_tm_id,
                "new_tm_id": diff.new_tm_id,
                "old_class": diff.old_class,
                "new_class": diff.new_class,
                "file_diff": list(diff.file_diff),
            }
            for diff in report.testmethod_diffs
        ]

    return json.dumps(result, indent=2, ensure_ascii=False)
