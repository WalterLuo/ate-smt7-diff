#!/usr/bin/env python3
"""Tests for agent explain module."""

from ate_smt7_diff.agent.discover import DiscoveryResult, FlowPairSummary, SuiteChangeSummary
from ate_smt7_diff.agent.explain import explain


class TestExplain:
    def test_empty_result(self) -> None:
        result = DiscoveryResult(old_package="old", new_package="new")
        explanations = explain(result)
        assert explanations == []

    def test_flow_added(self) -> None:
        result = DiscoveryResult(
            old_package="old",
            new_package="new",
            flow_summaries=[
                FlowPairSummary(
                    old_flow="a.flow",
                    new_flow="b.flow",
                    added_suites=["S1"],
                    suite_summaries=[
                        SuiteChangeSummary(suite_name="S1", flow_changed=True),
                    ],
                )
            ],
        )
        explanations = explain(result)
        assert any(e.category == "flow" and e.change_type == "added" for e in explanations)

    def test_focus_category(self) -> None:
        result = DiscoveryResult(
            old_package="old",
            new_package="new",
            flow_summaries=[
                FlowPairSummary(
                    old_flow="a.flow",
                    new_flow="b.flow",
                    suite_summaries=[
                        SuiteChangeSummary(suite_name="S1", timing_changed=True),
                        SuiteChangeSummary(suite_name="S2", level_changed=True),
                    ],
                )
            ],
        )
        explanations = explain(result, focus_category="timing")
        assert all(e.category == "timing" for e in explanations)
        assert len(explanations) == 1

    def test_focus_suite(self) -> None:
        result = DiscoveryResult(
            old_package="old",
            new_package="new",
            flow_summaries=[
                FlowPairSummary(
                    old_flow="a.flow",
                    new_flow="b.flow",
                    suite_summaries=[
                        SuiteChangeSummary(suite_name="S1", timing_changed=True),
                        SuiteChangeSummary(suite_name="S2", level_changed=True),
                    ],
                )
            ],
        )
        explanations = explain(result, focus_suite="S1")
        assert all(e.suite_name == "S1" for e in explanations)
