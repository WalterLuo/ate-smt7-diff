#!/usr/bin/env python3
"""Tests for agent validate module."""

from ate_smt7_diff.agent.discover import DiscoveryResult, FlowPairSummary, SuiteChangeSummary
from ate_smt7_diff.agent.validate import validate


class TestValidate:
    def test_empty_result_passes(self) -> None:
        result = DiscoveryResult(old_package="old", new_package="new")
        validation = validate(result)
        assert validation.passed is True
        assert validation.findings == []

    def test_unmatched_old_warning(self) -> None:
        result = DiscoveryResult(
            old_package="old",
            new_package="new",
            unmatched_old=["a.flow"],
        )
        validation = validate(result)
        assert validation.passed is True
        assert any(f.rule == "unmatched_old_flows" for f in validation.findings)

    def test_removed_suite_error(self) -> None:
        result = DiscoveryResult(
            old_package="old",
            new_package="new",
            flow_summaries=[
                FlowPairSummary(
                    old_flow="a.flow",
                    new_flow="b.flow",
                    removed_suites=["S1"],
                )
            ],
        )
        validation = validate(result)
        assert validation.passed is False
        assert any(f.rule == "suites_removed" for f in validation.findings)

    def test_timing_without_level_info(self) -> None:
        result = DiscoveryResult(
            old_package="old",
            new_package="new",
            flow_summaries=[
                FlowPairSummary(
                    old_flow="a.flow",
                    new_flow="b.flow",
                    suite_summaries=[
                        SuiteChangeSummary(suite_name="S1", timing_changed=True),
                    ],
                )
            ],
        )
        validation = validate(result)
        assert any(f.rule == "timing_without_level" for f in validation.findings)

    def test_summary_counts(self) -> None:
        result = DiscoveryResult(
            old_package="old",
            new_package="new",
            unmatched_old=["a.flow"],
            flow_summaries=[
                FlowPairSummary(
                    old_flow="a.flow",
                    new_flow="b.flow",
                    removed_suites=["S1"],
                )
            ],
        )
        validation = validate(result)
        assert validation.summary.get("warning", 0) >= 1
        assert validation.summary.get("error", 0) >= 1
