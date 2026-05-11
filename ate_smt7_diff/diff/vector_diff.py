#!/usr/bin/env python3
"""
Vector / pattern mapping diff algorithms.

Compares pattern mappings between old and new programs for common suites.
If mappings are identical, checks underlying file modification dates.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional

from ate_smt7_diff.models import (
    VectorFileDateChange,
    VectorSuiteDiff,
    VectorSuiteMapping,
)


def _check_file_dates(
    old_mapping: VectorSuiteMapping,
    new_mapping: VectorSuiteMapping,
) -> List[VectorFileDateChange]:
    """Check modification dates of mapped files when mappings are identical."""
    changes: List[VectorFileDateChange] = []

    old_files = {
        m.pattern_name: m.mapped_file or m.pattern_name
        for m in old_mapping.pattern_mappings
    }
    new_files = {
        m.pattern_name: m.mapped_file or m.pattern_name
        for m in new_mapping.pattern_mappings
    }

    for pattern_name in sorted(set(old_files.keys()) & set(new_files.keys())):
        old_file = old_files[pattern_name]
        new_file = new_files[pattern_name]

        old_path = Path(old_mapping.path) / old_file
        new_path = Path(new_mapping.path) / new_file

        try:
            old_mtime = old_path.stat().st_mtime
            new_mtime = new_path.stat().st_mtime
            if old_mtime != new_mtime:
                changes.append(
                    VectorFileDateChange(
                        file_path=str(new_path),
                        old_mtime=old_mtime,
                        new_mtime=new_mtime,
                    )
                )
        except (FileNotFoundError, PermissionError, OSError) as e:
            logging.warning(
                "Failed to stat vector file %s or %s: %s",
                old_path, new_path, e,
            )

    return changes


def diff_vectors(
    common_suites: List[str],
    old_views: Dict[str, "SuiteConfigView"],
    new_views: Dict[str, "SuiteConfigView"],
) -> List[VectorSuiteDiff]:
    """Compare vector mappings for all common suites.

    For each suite:
    - If both have ``override_seqlbl`` with same value: compare mappings.
      If mappings differ, report ``changed``. If mappings are identical,
      check file modification dates and report ``file_date_changed`` if
      any differ.
    - If only old has ``override_seqlbl``: report ``removed``.
    - If only new has ``override_seqlbl``: report ``added``.
    - Neither has: skip.

    Returns a list of VectorSuiteDiff with changes only.
    """
    diffs: List[VectorSuiteDiff] = []

    for suite_name in sorted(common_suites):
        old_v = old_views.get(suite_name)
        new_v = new_views.get(suite_name)
        if not old_v or not new_v:
            continue

        old_mapping: Optional[VectorSuiteMapping] = old_v.vector_mappings
        new_mapping: Optional[VectorSuiteMapping] = new_v.vector_mappings

        if old_mapping is None and new_mapping is None:
            continue

        if old_mapping is not None and new_mapping is None:
            diffs.append(
                VectorSuiteDiff(
                    suite_name=suite_name,
                    diff_type="removed",
                    old_mappings=old_mapping.pattern_mappings,
                )
            )
            continue

        if old_mapping is None and new_mapping is not None:
            diffs.append(
                VectorSuiteDiff(
                    suite_name=suite_name,
                    diff_type="added",
                    new_mappings=new_mapping.pattern_mappings,
                )
            )
            continue

        # Both have mappings
        assert old_mapping is not None
        assert new_mapping is not None

        # Compare pattern mappings only (path differs because programs are in different dirs)
        if old_mapping.pattern_mappings != new_mapping.pattern_mappings:
            diffs.append(
                VectorSuiteDiff(
                    suite_name=suite_name,
                    diff_type="changed",
                    old_mappings=old_mapping.pattern_mappings,
                    new_mappings=new_mapping.pattern_mappings,
                )
            )
            continue

        # Mappings identical — check file dates
        file_date_changes = _check_file_dates(old_mapping, new_mapping)
        if file_date_changes:
            diffs.append(
                VectorSuiteDiff(
                    suite_name=suite_name,
                    diff_type="file_date_changed",
                    old_mappings=old_mapping.pattern_mappings,
                    new_mappings=new_mapping.pattern_mappings,
                    file_date_changes=tuple(file_date_changes),
                )
            )

    return diffs
