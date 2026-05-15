#!/usr/bin/env python3
"""Tests for agent discover module."""

import pytest

from ate_smt7_diff.agent.discover import (
    DiscoveryResult,
    FlowPairSummary,
    SuiteChangeSummary,
    _compute_overall_severity,
    _max_severity,
    discover,
)


class TestMaxSeverity:
    def test_same(self) -> None:
        assert _max_severity("low", "low") == "low"

    def test_higher_wins(self) -> None:
        assert _max_severity("low", "high") == "high"
        assert _max_severity("high", "low") == "high"

    def test_critical_beats_all(self) -> None:
        assert _max_severity("medium", "critical") == "critical"
        assert _max_severity("critical", "high") == "critical"


class TestComputeOverallSeverity:
    def test_empty(self) -> None:
        assert _compute_overall_severity([]) == "low"

    def test_all_low(self) -> None:
        summary = FlowPairSummary(
            old_flow="a.flow",
            new_flow="b.flow",
            suite_summaries=[
                SuiteChangeSummary(suite_name="S1", severity="low"),
                SuiteChangeSummary(suite_name="S2", severity="low"),
            ],
        )
        assert _compute_overall_severity([summary]) == "low"

    def test_mixed(self) -> None:
        summary = FlowPairSummary(
            old_flow="a.flow",
            new_flow="b.flow",
            suite_summaries=[
                SuiteChangeSummary(suite_name="S1", severity="low"),
                SuiteChangeSummary(suite_name="S2", severity="high"),
            ],
        )
        assert _compute_overall_severity([summary]) == "high"


class TestDiscoverIntegration:
    def test_discover_example_packages(self) -> None:
        result = discover("Test1/example1", "Test2/example2", load_configs=False)
        assert result.total_pairs == 8
        assert result.old_package.endswith("Test1/example1")
        assert result.new_package.endswith("Test2/example2")

    def test_discover_missing_directories(self) -> None:
        result = discover("/nonexistent/old", "/nonexistent/new")
        assert result.total_pairs == 0
        assert result.flow_summaries == []

    def test_discover_with_configs(self) -> None:
        result = discover("Test1/example1", "Test2/example2", load_configs=True)
        assert result.total_pairs == 8
        assert result.overall_severity in ("low", "medium", "high", "critical")

    def test_flow_summaries_populated(self) -> None:
        result = discover("Test1/example1", "Test2/example2", load_configs=False)
        for summary in result.flow_summaries:
            assert summary.old_flow
            assert summary.new_flow
            assert isinstance(summary.suite_summaries, list)
