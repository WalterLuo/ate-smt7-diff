#!/usr/bin/env python3
"""Built-in diff plugins.

Each plugin encapsulates one diff type so that builder/__init__.py does
not need to hard-code individual diff calls.
"""

from __future__ import annotations

from typing import Any

from ate_smt7_diff.models import SuiteConfigView
from ate_smt7_diff.plugins.registry import register


class SuiteConfigPlugin:
    """Diff test suite configuration parameters."""

    name = "suite_config"
    requires_views = False

    def run(
        self,
        old_path: str,
        new_path: str,
        common_suites: set[str],
        old_views: dict[str, SuiteConfigView] | None,
        new_views: dict[str, SuiteConfigView] | None,
        fs: Any | None = None,
    ) -> dict[str, Any]:
        from ate_smt7_diff.diff.suite_diff import diff_suite_configs

        report = diff_suite_configs(old_path, new_path, common_suites, fs)
        return {"suite_config_report": report}


class LevelSpecPlugin:
    """Diff level specifications for common suites."""

    name = "level_spec"
    requires_views = True

    def run(
        self,
        old_path: str,
        new_path: str,
        common_suites: set[str],
        old_views: dict[str, SuiteConfigView] | None,
        new_views: dict[str, SuiteConfigView] | None,
        fs: Any | None = None,
    ) -> dict[str, Any]:
        from ate_smt7_diff.diff.level_diff import diff_level_specs

        diffs = []
        for suite_name in sorted(common_suites):
            old_v = old_views.get(suite_name) if old_views else None
            new_v = new_views.get(suite_name) if new_views else None
            if old_v and new_v:
                diff = diff_level_specs(suite_name, old_v.level_specs, new_v.level_specs)
                if diff and diff.has_changes:
                    diffs.append(diff)
        return {"level_spec_diffs": diffs if diffs else None}


class EqnSetPlugin:
    """Diff level EQNSET blocks for common suites."""

    name = "eqnset"
    requires_views = True

    def run(
        self,
        old_path: str,
        new_path: str,
        common_suites: set[str],
        old_views: dict[str, SuiteConfigView] | None,
        new_views: dict[str, SuiteConfigView] | None,
        fs: Any | None = None,
    ) -> dict[str, Any]:
        from ate_smt7_diff.diff.level_diff import diff_eqnset_blocks

        diffs = []
        for suite_name in sorted(common_suites):
            old_v = old_views.get(suite_name) if old_views else None
            new_v = new_views.get(suite_name) if new_views else None
            if old_v and new_v:
                diff = diff_eqnset_blocks(suite_name, old_v.eqnset_block, new_v.eqnset_block)
                if diff and diff.has_changes:
                    diffs.append(diff)
        return {"eqnset_diffs": diffs if diffs else None}


class TimingPlugin:
    """Diff timing specs and EQNSET blocks for common suites.

    This single plugin produces both ``timing_spec_diffs`` and
    ``timing_eqnset_diffs`` because the two are computed together
    via the port-spec vs regular dispatch logic.
    """

    name = "timing"
    requires_views = True

    def run(
        self,
        old_path: str,
        new_path: str,
        common_suites: set[str],
        old_views: dict[str, SuiteConfigView] | None,
        new_views: dict[str, SuiteConfigView] | None,
        fs: Any | None = None,
    ) -> dict[str, Any]:
        from ate_smt7_diff.builder.timing_diff_dispatch import (
            _diff_port_timing,
            _diff_regular_timing,
        )
        from ate_smt7_diff.models import TimingEqnSetDiff, TimingSpecDiff

        timing_spec_diffs: list[TimingSpecDiff] = []
        timing_eqnset_diffs: list[TimingEqnSetDiff] = []

        for suite_name in sorted(common_suites):
            old_v = old_views.get(suite_name) if old_views else None
            new_v = new_views.get(suite_name) if new_views else None
            if not old_v or not new_v:
                continue
            if old_v.timing_eqn_set is None and new_v.timing_eqn_set is None:
                _diff_port_timing(
                    suite_name, old_v, new_v, timing_spec_diffs, timing_eqnset_diffs
                )
            else:
                _diff_regular_timing(
                    suite_name, old_v, new_v, timing_spec_diffs, timing_eqnset_diffs
                )

        return {
            "timing_spec_diffs": timing_spec_diffs if timing_spec_diffs else None,
            "timing_eqnset_diffs": timing_eqnset_diffs if timing_eqnset_diffs else None,
        }


class WaveTblPlugin:
    """Diff timing WAVETBL blocks for common suites."""

    name = "timing_wavetbl"
    requires_views = True

    def run(
        self,
        old_path: str,
        new_path: str,
        common_suites: set[str],
        old_views: dict[str, SuiteConfigView] | None,
        new_views: dict[str, SuiteConfigView] | None,
        fs: Any | None = None,
    ) -> dict[str, Any]:
        from ate_smt7_diff.diff.wavetbl_diff import diff_wavetbls

        diffs = []
        for suite_name in sorted(common_suites):
            old_v = old_views.get(suite_name) if old_views else None
            new_v = new_views.get(suite_name) if new_views else None
            if old_v and new_v:
                wt_diffs = diff_wavetbls(
                    suite_name,
                    old_v.timing_wavetbl_blocks,
                    new_v.timing_wavetbl_blocks,
                )
                diffs.extend(wt_diffs)
        return {"timing_wavetbl_diffs": diffs if diffs else None}


class VectorPlugin:
    """Diff vector pattern mappings for common suites."""

    name = "vector"
    requires_views = True

    def run(
        self,
        old_path: str,
        new_path: str,
        common_suites: set[str],
        old_views: dict[str, SuiteConfigView] | None,
        new_views: dict[str, SuiteConfigView] | None,
        fs: Any | None = None,
    ) -> dict[str, Any]:
        from ate_smt7_diff.diff.vector_diff import diff_vectors

        diffs = diff_vectors(
            sorted(common_suites),
            old_views or {},
            new_views or {},
        )
        return {"vector_diffs": diffs if diffs else None}


class TestMethodPlugin:
    """Diff testmethod references for common suites."""

    name = "testmethod"
    requires_views = True

    def run(
        self,
        old_path: str,
        new_path: str,
        common_suites: set[str],
        old_views: dict[str, SuiteConfigView] | None,
        new_views: dict[str, SuiteConfigView] | None,
        fs: Any | None = None,
    ) -> dict[str, Any]:
        from ate_smt7_diff.diff.testmethod_diff import diff_testmethods

        diffs = diff_testmethods(
            sorted(common_suites),
            old_views or {},
            new_views or {},
        )
        return {"testmethod_diffs": diffs if diffs else None}


class TestTablePlugin:
    """Diff testtable CSV rows for common suites.

    Can operate with or without config views. When views are absent it
    independently loads the testtable files.
    """

    name = "testtable"
    requires_views = False

    def run(
        self,
        old_path: str,
        new_path: str,
        common_suites: set[str],
        old_views: dict[str, SuiteConfigView] | None,
        new_views: dict[str, SuiteConfigView] | None,
        fs: Any | None = None,
    ) -> dict[str, Any]:
        from ate_smt7_diff.builder.context import load_program_context
        from ate_smt7_diff.diff.testtable_diff import diff_testtables
        from ate_smt7_diff.parsers.testtable_parser import TestTableLoader

        if old_views is not None and new_views is not None:
            old_rows_by_suite = {
                suite_name: view.testtable_rows
                for suite_name, view in old_views.items()
                if view.testtable_rows is not None
            }
            new_rows_by_suite = {
                suite_name: view.testtable_rows
                for suite_name, view in new_views.items()
                if view.testtable_rows is not None
            }
        else:
            old_ctx = load_program_context(old_path, fs)
            new_ctx = load_program_context(new_path, fs)
            old_testtable = (
                TestTableLoader(str(old_ctx.testtable_path), fs)
                if old_ctx.testtable_path
                else None
            )
            new_testtable = (
                TestTableLoader(str(new_ctx.testtable_path), fs)
                if new_ctx.testtable_path
                else None
            )
            old_rows_by_suite = old_testtable.rows_by_suite if old_testtable else {}
            new_rows_by_suite = new_testtable.rows_by_suite if new_testtable else {}

        diffs = diff_testtables(
            sorted(common_suites),
            old_rows_by_suite,
            new_rows_by_suite,
        )
        return {"testtable_diffs": diffs if diffs else None}


# ------------------------------------------------------------------
# Auto-register built-in plugins at import time
# ------------------------------------------------------------------

register("suite_config", SuiteConfigPlugin())
register("level_spec", LevelSpecPlugin())
register("eqnset", EqnSetPlugin())
register("timing", TimingPlugin())
register("timing_wavetbl", WaveTblPlugin())
register("vector", VectorPlugin())
register("testmethod", TestMethodPlugin())
register("testtable", TestTablePlugin())
