#!/usr/bin/env python3
"""JSON serialization helpers for testtable, vector, and testmethod diffs."""

from ate_smt7_diff.formatters.shared import (
    testtable_row_dict as _testtable_row_dict,
    vector_mapping_dict as _vector_mapping_dict,
)
from ate_smt7_diff.models import TestMethodDiff, TestTableSuiteDiff, VectorSuiteDiff


def _format_testtable_json(diff: TestTableSuiteDiff) -> dict:
    """Serialize a TestTableSuiteDiff as a JSON dict."""
    return {
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


def _format_vector_json(diff: VectorSuiteDiff) -> dict:
    """Serialize a VectorSuiteDiff as a JSON dict."""
    return {
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


def _format_testmethod_json(diff: TestMethodDiff) -> dict:
    """Serialize a TestMethodDiff as a JSON dict."""
    return {
        "suite_name": diff.suite_name,
        "diff_type": diff.diff_type,
        "old_tm_id": diff.old_tm_id,
        "new_tm_id": diff.new_tm_id,
        "old_class": diff.old_class,
        "new_class": diff.new_class,
        "file_diff": list(diff.file_diff),
    }
