#!/usr/bin/env python3
"""Tests for agent suggest module."""

from ate_smt7_diff.agent.discover import DiscoveryResult, FlowPairSummary, SuiteChangeSummary
from ate_smt7_diff.agent.suggest import suggest


class TestSuggest:
    def test_empty_result(self) -> None:
        result = DiscoveryResult(old_package="old", new_package="new")
        suggestions = suggest(result)
        assert suggestions == []

    def test_unmatched_old(self) -> None:
        result = DiscoveryResult(
            old_package="old",
            new_package="new",
            unmatched_old=["a.flow", "b.flow"],
        )
        suggestions = suggest(result)
        assert len(suggestions) == 1
        assert suggestions[0].category == "flow"
        assert suggestions[0].severity == "high"
        assert "a.flow" in suggestions[0].message

    def test_removed_suites(self) -> None:
        result = DiscoveryResult(
            old_package="old",
            new_package="new",
            flow_summaries=[
                FlowPairSummary(
                    old_flow="a.flow",
                    new_flow="b.flow",
                    removed_suites=["S1", "S2"],
                    suite_summaries=[
                        SuiteChangeSummary(suite_name="S1", flow_changed=True, severity="high"),
                        SuiteChangeSummary(suite_name="S2", flow_changed=True, severity="high"),
                    ],
                )
            ],
        )
        suggestions = suggest(result)
        assert any(s.category == "flow" and "删除" in s.message for s in suggestions)

    def test_timing_changes(self) -> None:
        result = DiscoveryResult(
            old_package="old",
            new_package="new",
            flow_summaries=[
                FlowPairSummary(
                    old_flow="a.flow",
                    new_flow="b.flow",
                    suite_summaries=[
                        SuiteChangeSummary(
                            suite_name="S1",
                            timing_changed=True,
                            severity="high",
                        ),
                    ],
                )
            ],
        )
        suggestions = suggest(result)
        assert any(s.category == "timing" for s in suggestions)

    def test_priority_order(self) -> None:
        result = DiscoveryResult(
            old_package="old",
            new_package="new",
            unmatched_new=["x.flow"],
            flow_summaries=[
                FlowPairSummary(
                    old_flow="a.flow",
                    new_flow="b.flow",
                    suite_summaries=[
                        SuiteChangeSummary(
                            suite_name="S1",
                            suite_config_changed=True,
                            severity="low",
                        ),
                    ],
                )
            ],
        )
        suggestions = suggest(result)
        assert suggestions[0].severity == "high"
