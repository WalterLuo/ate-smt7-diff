#!/usr/bin/env python3
"""
JSON formatter for diff reports.
"""

import json
from typing import Dict, List

from ate_smt7_diff.models import DiffReport, SuiteConfigReport


def format_suite_json(report: SuiteConfigReport) -> dict:
    """Format suite config diff as a JSON-serializable dict."""
    diffs = []
    for diff in report.diffs:
        if not diff.has_changes:
            continue
        diffs.append({
            "suite_name": diff.suite_name,
            "changed": {
                k: {"old": ov, "new": nv}
                for k, (ov, nv) in diff.changed.items()
            },
            "added": diff.added,
            "removed": diff.removed,
        })

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

    old_pos_map: Dict[str, List[int]] = {}
    for i, t in enumerate(report.old_tests):
        old_pos_map.setdefault(t.suite_name, []).append(i)

    new_pos_map: Dict[str, List[int]] = {}
    for i, t in enumerate(report.new_tests):
        new_pos_map.setdefault(t.suite_name, []).append(i)

    for name in report.order_changed:
        old_order = old_pos_map.get(name, [None])[0]
        new_order = new_pos_map.get(name, [None])[0]
        order_changed_entries.append({
            "test_name": name,
            "old_order": (old_order + 1) if old_order is not None else None,
            "new_order": (new_order + 1) if new_order is not None else None,
        })

    result = {
        "added_tests": report.added,
        "removed_tests": report.removed,
        "order_changed": order_changed_entries,
        "summary": {
            "added_count": len(report.added),
            "removed_count": len(report.removed),
            "order_changed_count": len(report.order_changed),
        }
    }

    if report.suite_config_report is not None:
        suite_json = format_suite_json(report.suite_config_report)
        result["suite_config_diff"] = suite_json["suite_config_diff"]

    if report.level_spec_diffs:
        result["level_spec_diff"] = [
            {
                "suite_name": diff.suite_name,
                "added": {
                    name: {
                        "actual": spec.actual,
                        "min": spec.min,
                        "max": spec.max,
                        "units": spec.units,
                        "comment": spec.comment,
                    }
                    for name, spec in diff.added.items()
                },
                "removed": {
                    name: {
                        "actual": spec.actual,
                        "min": spec.min,
                        "max": spec.max,
                        "units": spec.units,
                        "comment": spec.comment,
                    }
                    for name, spec in diff.removed.items()
                },
                "changed": {
                    name: {
                        "old": {
                            "actual": old_s.actual,
                            "min": old_s.min,
                            "max": old_s.max,
                            "units": old_s.units,
                            "comment": old_s.comment,
                        },
                        "new": {
                            "actual": new_s.actual,
                            "min": new_s.min,
                            "max": new_s.max,
                            "units": new_s.units,
                            "comment": new_s.comment,
                        },
                    }
                    for name, (old_s, new_s) in diff.changed.items()
                },
            }
            for diff in report.level_spec_diffs
        ]

    if report.eqnset_diffs:
        result["eqnset_diff"] = [
            {
                "suite_name": diff.suite_name,
                "eqnset_index": diff.eqnset_index,
                "eqnset_name": diff.eqnset_name,
                "dpspins": {
                    "added": {
                        name: cfg.all_fields()
                        for name, cfg in diff.dpspins_added.items()
                    },
                    "removed": {
                        name: cfg.all_fields()
                        for name, cfg in diff.dpspins_removed.items()
                    },
                    "changed": {
                        name: {
                            "old": old_c.all_fields(),
                            "new": new_c.all_fields(),
                        }
                        for name, (old_c, new_c) in diff.dpspins_changed.items()
                    },
                },
                "levelsets": {
                    "added": {
                        str(idx): {
                            name: cfg.all_fields()
                            for name, cfg in pins.items()
                        }
                        for idx, pins in diff.levelsets_added.items()
                    },
                    "removed": {
                        str(idx): {
                            name: cfg.all_fields()
                            for name, cfg in pins.items()
                        }
                        for idx, pins in diff.levelsets_removed.items()
                    },
                    "changed": {
                        str(idx): {
                            name: {
                                "old": old_c.all_fields(),
                                "new": new_c.all_fields(),
                            }
                            for name, (old_c, new_c) in pins.items()
                        }
                        for idx, pins in diff.levelsets_changed.items()
                    },
                },
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
                "new_specs": {
                    name: {
                        "value": spec.value,
                        "units": spec.units,
                        "comment": spec.comment,
                    }
                    for name, spec in (diff.new_specs or {}).items()
                } if diff.replaced_from else None,
                "added": {
                    name: {
                        "value": spec.value,
                        "units": spec.units,
                        "comment": spec.comment,
                    }
                    for name, spec in diff.added.items()
                },
                "removed": {
                    name: {
                        "value": spec.value,
                        "units": spec.units,
                        "comment": spec.comment,
                    }
                    for name, spec in diff.removed.items()
                },
                "changed": {
                    name: {
                        "old": {
                            "value": old_s.value,
                            "units": old_s.units,
                            "comment": old_s.comment,
                        },
                        "new": {
                            "value": new_s.value,
                            "units": new_s.units,
                            "comment": new_s.comment,
                        },
                    }
                    for name, (old_s, new_s) in diff.changed.items()
                },
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
                "replaced_block": {
                    "specs": {
                        name: {"value": spec.value, "units": spec.units, "comment": spec.comment}
                        for name, spec in diff.new_block.specs.items()
                    },
                    "pins": {
                        name: cfg.all_fields()
                        for name, cfg in diff.new_block.pins_groups.items()
                    },
                    "timingsets": {
                        str(idx): cfg.all_fields()
                        for idx, cfg in diff.new_block.timingsets.items()
                    },
                } if diff.replaced_from_name and diff.new_block else None,
                "specs": {
                    "added": {
                        name: {"value": spec.value, "units": spec.units, "comment": spec.comment}
                        for name, spec in diff.specs_added.items()
                    },
                    "removed": {
                        name: {"value": spec.value, "units": spec.units, "comment": spec.comment}
                        for name, spec in diff.specs_removed.items()
                    },
                    "changed": {
                        name: {
                            "old": {"value": old_s.value, "units": old_s.units, "comment": old_s.comment},
                            "new": {"value": new_s.value, "units": new_s.units, "comment": new_s.comment},
                        }
                        for name, (old_s, new_s) in diff.specs_changed.items()
                    },
                },
                "pins": {
                    "added": {
                        name: cfg.all_fields()
                        for name, cfg in diff.pins_added.items()
                    },
                    "removed": {
                        name: cfg.all_fields()
                        for name, cfg in diff.pins_removed.items()
                    },
                    "changed": {
                        name: {
                            "old": old_c.all_fields(),
                            "new": new_c.all_fields(),
                        }
                        for name, (old_c, new_c) in diff.pins_changed.items()
                    },
                },
                "timingsets": {
                    "added": {
                        str(idx): cfg.all_fields()
                        for idx, cfg in diff.timingsets_added.items()
                    },
                    "removed": {
                        str(idx): cfg.all_fields()
                        for idx, cfg in diff.timingsets_removed.items()
                    },
                    "changed": {
                        str(idx): {
                            "old": old_c.all_fields(),
                            "new": new_c.all_fields(),
                        }
                        for idx, (old_c, new_c) in diff.timingsets_changed.items()
                    },
                },
            }
            for diff in report.timing_eqnset_diffs
        ]

    if report.timing_wavetbl_diffs:
        result["timing_wavetbl_diff"] = [
            {
                "suite_name": diff.suite_name,
                "wavetbl_name": diff.wavetbl_name,
                "replaced_from": diff.replaced_from,
                "replaced_block": {
                    "pins_groups": {
                        name: {
                            "rows": [
                                {"label": row.label, "edge_spec": row.edge_spec, "state": row.state}
                                for row in group.rows
                            ],
                            "brk": group.brk,
                            "f": group.f,
                        }
                        for name, group in diff.new_block.pins_groups.items()
                    }
                } if diff.replaced_from and diff.new_block else None,
                "added_block": {
                    "pins_groups": {
                        name: {
                            "rows": [
                                {"label": row.label, "edge_spec": row.edge_spec, "state": row.state}
                                for row in group.rows
                            ],
                            "brk": group.brk,
                            "f": group.f,
                        }
                        for name, group in diff.new_block.pins_groups.items()
                    }
                } if diff.new_block and not diff.old_block and not diff.replaced_from else None,
                "removed_block": {
                    "pins_groups": {
                        name: {
                            "rows": [
                                {"label": row.label, "edge_spec": row.edge_spec, "state": row.state}
                                for row in group.rows
                            ],
                            "brk": group.brk,
                            "f": group.f,
                        }
                        for name, group in diff.old_block.pins_groups.items()
                    }
                } if diff.old_block and not diff.new_block and not diff.replaced_from else None,
                "pins_groups": {
                    "added": {
                        name: {
                            "rows": [
                                {"label": row.label, "edge_spec": row.edge_spec, "state": row.state}
                                for row in group.rows
                            ],
                            "brk": group.brk,
                            "f": group.f,
                        }
                        for name, group in diff.pins_groups_added.items()
                    },
                    "removed": {
                        name: {
                            "rows": [
                                {"label": row.label, "edge_spec": row.edge_spec, "state": row.state}
                                for row in group.rows
                            ],
                            "brk": group.brk,
                            "f": group.f,
                        }
                        for name, group in diff.pins_groups_removed.items()
                    },
                    "changed": {
                        name: {
                            "rows_added": [
                                {"label": row.label, "edge_spec": row.edge_spec, "state": row.state}
                                for row in pg_diff.rows_added
                            ],
                            "rows_removed": [
                                {"label": row.label, "edge_spec": row.edge_spec, "state": row.state}
                                for row in pg_diff.rows_removed
                            ],
                            "rows_changed": [
                                {
                                    "old": {"label": old_r.label, "edge_spec": old_r.edge_spec, "state": old_r.state},
                                    "new": {"label": new_r.label, "edge_spec": new_r.edge_spec, "state": new_r.state},
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
                } if diff.old_block and diff.new_block and not diff.replaced_from else None,
            }
            for diff in report.timing_wavetbl_diffs
        ]

    return json.dumps(result, indent=2, ensure_ascii=False)
