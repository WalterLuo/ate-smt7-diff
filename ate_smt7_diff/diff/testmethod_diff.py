#!/usr/bin/env python3
"""
Testmethod diff algorithms.

Compares testmethod references and optionally source file contents
for common test suites between old and new programs.
"""

import difflib

from ate_smt7_diff.models import SuiteConfigView, TestMethodDiff, TestMethodInfo


def _compute_file_diff(old_info: TestMethodInfo, new_info: TestMethodInfo) -> tuple[str, ...]:
    """Return unified diff lines when two testmethod source files differ."""
    old_lines = (old_info.content or "").splitlines()
    new_lines = (new_info.content or "").splitlines()
    diff_lines = list(
        difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile=str(old_info.file_path) if old_info.file_path else "old",
            tofile=str(new_info.file_path) if new_info.file_path else "new",
            lineterm="",
        )
    )
    return tuple(diff_lines)


def diff_testmethods(
    common_suites: list[str],
    old_views: dict[str, "SuiteConfigView"],
    new_views: dict[str, "SuiteConfigView"],
) -> list[TestMethodDiff]:
    """Compare testmethod references and source files for all common suites.

    For each suite:
    - If both lack a testmethod -> skip.
    - If only one has a testmethod -> report as class_changed.
    - If both have testmethods:
      - Compare tm_id and testmethod_class.
      - If either changed -> report metadata change, skip file comparison.
      - If both unchanged:
        - If either file is missing -> file_not_found.
        - If file contents identical -> skip (no diff).
        - If file contents differ -> file_changed with unified diff.

    Returns a list of TestMethodDiff with changes only.
    """
    diffs: list[TestMethodDiff] = []

    for suite_name in sorted(common_suites):
        old_v = old_views.get(suite_name)
        new_v = new_views.get(suite_name)
        if not old_v or not new_v:
            continue

        old_tm = old_v.testmethod
        new_tm = new_v.testmethod

        if old_tm is None and new_tm is None:
            continue

        if old_tm is not None and new_tm is None:
            diffs.append(
                TestMethodDiff(
                    suite_name=suite_name,
                    diff_type="class_changed",
                    old_tm_id=old_tm.tm_id,
                    old_class=old_tm.testmethod_class,
                )
            )
            continue

        if old_tm is None and new_tm is not None:
            diffs.append(
                TestMethodDiff(
                    suite_name=suite_name,
                    diff_type="class_changed",
                    new_tm_id=new_tm.tm_id,
                    new_class=new_tm.testmethod_class,
                )
            )
            continue

        assert old_tm is not None
        assert new_tm is not None

        tm_id_changed = old_tm.tm_id != new_tm.tm_id
        class_changed = old_tm.testmethod_class != new_tm.testmethod_class

        if tm_id_changed and class_changed:
            diffs.append(
                TestMethodDiff(
                    suite_name=suite_name,
                    diff_type="both_changed",
                    old_tm_id=old_tm.tm_id,
                    new_tm_id=new_tm.tm_id,
                    old_class=old_tm.testmethod_class,
                    new_class=new_tm.testmethod_class,
                )
            )
            continue

        if tm_id_changed:
            diffs.append(
                TestMethodDiff(
                    suite_name=suite_name,
                    diff_type="tm_id_changed",
                    old_tm_id=old_tm.tm_id,
                    new_tm_id=new_tm.tm_id,
                    old_class=old_tm.testmethod_class,
                    new_class=new_tm.testmethod_class,
                )
            )
            continue

        if class_changed:
            diffs.append(
                TestMethodDiff(
                    suite_name=suite_name,
                    diff_type="class_changed",
                    old_tm_id=old_tm.tm_id,
                    new_tm_id=new_tm.tm_id,
                    old_class=old_tm.testmethod_class,
                    new_class=new_tm.testmethod_class,
                )
            )
            continue

        old_exists = old_tm.file_path is not None and old_tm.content is not None
        new_exists = new_tm.file_path is not None and new_tm.content is not None

        if not old_exists and not new_exists:
            # Both are built-in / missing — silently skip
            continue

        if not old_exists or not new_exists:
            diffs.append(
                TestMethodDiff(
                    suite_name=suite_name,
                    diff_type="file_not_found",
                    old_tm_id=old_tm.tm_id,
                    new_tm_id=new_tm.tm_id,
                    old_class=old_tm.testmethod_class,
                    new_class=new_tm.testmethod_class,
                )
            )
            continue

        if old_tm.content == new_tm.content:
            continue

        file_diff = _compute_file_diff(old_tm, new_tm)
        diffs.append(
            TestMethodDiff(
                suite_name=suite_name,
                diff_type="file_changed",
                old_tm_id=old_tm.tm_id,
                new_tm_id=new_tm.tm_id,
                old_class=old_tm.testmethod_class,
                new_class=new_tm.testmethod_class,
                file_diff=file_diff,
            )
        )

    return diffs
