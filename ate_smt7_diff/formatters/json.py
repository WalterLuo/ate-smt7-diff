#!/usr/bin/env python3
"""JSON formatter for diff reports."""

import json

from ate_smt7_diff.formatters.json_level import (
    _format_eqnset_json,
    _format_level_spec_json,
)
from ate_smt7_diff.formatters.json_suite import (
    _format_testmethod_json,
    _format_testtable_json,
    _format_vector_json,
)
from ate_smt7_diff.formatters.json_timing import (
    _format_timing_eqnset_json,
    _format_timing_spec_json,
    _format_wavetbl_json,
)
from ate_smt7_diff.models import DiffReport, SuiteConfigReport


def format_suite_json(report: SuiteConfigReport) -> dict:
    """Format suite config diff as a JSON-serializable dict."""
    from ate_smt7_diff.formatters.shared import arc as _arc

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
            _format_level_spec_json(diff) for diff in report.level_spec_diffs
        ]

    if report.eqnset_diffs:
        result["eqnset_diff"] = [_format_eqnset_json(diff) for diff in report.eqnset_diffs]

    if report.timing_spec_diffs:
        result["timing_spec_diff"] = [
            _format_timing_spec_json(diff) for diff in report.timing_spec_diffs
        ]

    if report.timing_eqnset_diffs:
        result["timing_eqnset_diff"] = [
            _format_timing_eqnset_json(diff) for diff in report.timing_eqnset_diffs
        ]

    if report.timing_wavetbl_diffs:
        result["timing_wavetbl_diff"] = [
            _format_wavetbl_json(diff) for diff in report.timing_wavetbl_diffs
        ]

    if report.testtable_diffs:
        result["testtable_diff"] = [
            _format_testtable_json(diff) for diff in report.testtable_diffs
        ]

    if report.vector_diffs:
        result["vector_diff"] = [
            _format_vector_json(diff) for diff in report.vector_diffs
        ]

    if report.testmethod_diffs:
        result["testmethod_diff"] = [
            _format_testmethod_json(diff) for diff in report.testmethod_diffs
        ]

    return json.dumps(result, indent=2, ensure_ascii=False)
