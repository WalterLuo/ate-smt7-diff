#!/usr/bin/env python3
"""Discovery module: run full diff and produce a structured summary."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from ate_smt7_diff.builder import diff_flow_files
from ate_smt7_diff.flow_matcher import FlowMatcher
from ate_smt7_diff.models import DiffReport


@dataclass
class SuiteChangeSummary:
    """Summary of changes for a single suite."""

    suite_name: str
    flow_changed: bool = False
    suite_config_changed: bool = False
    timing_changed: bool = False
    level_changed: bool = False
    testtable_changed: bool = False
    vector_changed: bool = False
    testmethod_changed: bool = False
    severity: str = "low"  # low, medium, high, critical


@dataclass
class FlowPairSummary:
    """Summary for a single old/new flow pair."""

    old_flow: str
    new_flow: str
    added_suites: list[str] = field(default_factory=list)
    removed_suites: list[str] = field(default_factory=list)
    order_changed_suites: list[str] = field(default_factory=list)
    suite_summaries: list[SuiteChangeSummary] = field(default_factory=list)
    has_config_changes: bool = False


@dataclass
class DiscoveryResult:
    """Top-level discovery result for a package pair."""

    old_package: str
    new_package: str
    total_pairs: int = 0
    pairs_with_changes: int = 0
    flow_summaries: list[FlowPairSummary] = field(default_factory=list)
    unmatched_old: list[str] = field(default_factory=list)
    unmatched_new: list[str] = field(default_factory=list)
    overall_severity: str = "low"


def discover(
    old_package: str,
    new_package: str,
    match_config: str | None = None,
    load_configs: bool = True,
) -> DiscoveryResult:
    """Run full diff discovery between two program packages.

    Args:
        old_package: Path to old program package directory.
        new_package: Path to new program package directory.
        match_config: Optional flow matching config path.
        load_configs: Whether to load timing/level/vector/testtable configs.
    """
    old_pkg = Path(old_package).expanduser().resolve()
    new_pkg = Path(new_package).expanduser().resolve()

    old_flow_dir = old_pkg / "testflow"
    new_flow_dir = new_pkg / "testflow"

    result = DiscoveryResult(
        old_package=str(old_pkg),
        new_package=str(new_pkg),
    )

    if not old_flow_dir.is_dir() or not new_flow_dir.is_dir():
        return result

    matcher = FlowMatcher.from_config(match_config)
    pairs = matcher.match_directories(old_flow_dir, new_flow_dir)

    old_names = {f.name for f in old_flow_dir.glob("*.flow")}
    new_names = {f.name for f in new_flow_dir.glob("*.flow")}
    matched_old = {o.name for o, _ in pairs}
    matched_new = {n.name for _, n in pairs}
    result.unmatched_old = sorted(old_names - matched_old)
    result.unmatched_new = sorted(new_names - matched_new)

    for old_flow, new_flow in pairs:
        report = diff_flow_files(
            str(old_flow),
            str(new_flow),
            include_suite_diff=load_configs,
            include_config_views=load_configs,
            include_testtable_diff=load_configs,
            include_testmethod_diff=load_configs,
        )
        summary = _summarize_report(str(old_flow), str(new_flow), report)
        result.flow_summaries.append(summary)

    result.total_pairs = len(result.flow_summaries)
    result.pairs_with_changes = sum(
        1
        for s in result.flow_summaries
        if s.added_suites
        or s.removed_suites
        or s.order_changed_suites
        or s.has_config_changes
    )
    result.overall_severity = _compute_overall_severity(result.flow_summaries)

    return result


def _summarize_report(old_flow: str, new_flow: str, report: DiffReport) -> FlowPairSummary:
    summary = FlowPairSummary(
        old_flow=old_flow,
        new_flow=new_flow,
        added_suites=report.added,
        removed_suites=report.removed,
        order_changed_suites=report.order_changed,
    )

    # Build per-suite summaries
    suite_names = set(report.added + report.removed)
    if report.old_tests and report.new_tests:
        suite_names.update(t.suite_name for t in report.old_tests)
        suite_names.update(t.suite_name for t in report.new_tests)

    for name in sorted(suite_names):
        sc = SuiteChangeSummary(suite_name=name)
        if name in report.added or name in report.removed:
            sc.flow_changed = True
            sc.severity = "high"

        # Check suite config diff
        if report.suite_config_report:
            for diff in report.suite_config_report.diffs:
                if diff.suite_name == name and diff.has_changes:
                    sc.suite_config_changed = True
                    sc.severity = _max_severity(sc.severity, "medium")

        # Check timing diffs
        if report.timing_spec_diffs:
            for diff in report.timing_spec_diffs:
                if diff.suite_name == name:
                    sc.timing_changed = True
                    sc.severity = _max_severity(sc.severity, "high")

        # Check level diffs
        if report.level_spec_diffs:
            for diff in report.level_spec_diffs:
                if diff.suite_name == name:
                    sc.level_changed = True
                    sc.severity = _max_severity(sc.severity, "high")

        # Check testtable diffs
        if report.testtable_diffs:
            for diff in report.testtable_diffs:
                if diff.suite_name == name:
                    sc.testtable_changed = True
                    sc.severity = _max_severity(sc.severity, "medium")

        # Check vector diffs
        if report.vector_diffs:
            for diff in report.vector_diffs:
                if diff.suite_name == name:
                    sc.vector_changed = True
                    sc.severity = _max_severity(sc.severity, "medium")

        # Check testmethod diffs
        if report.testmethod_diffs:
            for diff in report.testmethod_diffs:
                if diff.suite_name == name:
                    sc.testmethod_changed = True
                    sc.severity = _max_severity(sc.severity, "medium")

        summary.suite_summaries.append(sc)

    summary.has_config_changes = any(
        sc.suite_config_changed
        or sc.timing_changed
        or sc.level_changed
        or sc.testtable_changed
        or sc.vector_changed
        or sc.testmethod_changed
        for sc in summary.suite_summaries
    )

    return summary


def _max_severity(a: str, b: str) -> str:
    order = {"low": 0, "medium": 1, "high": 2, "critical": 3}
    return a if order.get(a, 0) >= order.get(b, 0) else b


def _compute_overall_severity(summaries: list[FlowPairSummary]) -> str:
    sev = "low"
    for s in summaries:
        for sc in s.suite_summaries:
            sev = _max_severity(sev, sc.severity)
    return sev
