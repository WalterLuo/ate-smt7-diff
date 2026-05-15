#!/usr/bin/env python3
"""Suggestion module: generate actionable insights from discovery results."""

from __future__ import annotations

from dataclasses import dataclass, field

from ate_smt7_diff.agent.discover import DiscoveryResult, FlowPairSummary


@dataclass
class SuggestionItem:
    """A single actionable suggestion."""

    category: str  # flow, timing, level, testtable, vector, testmethod, suite_config
    severity: str  # low, medium, high, critical
    message: str
    affected_suites: list[str] = field(default_factory=list)
    affected_flows: list[str] = field(default_factory=list)


def suggest(result: DiscoveryResult) -> list[SuggestionItem]:
    """Generate smart suggestions from a discovery result.

    Returns a list of prioritized suggestions.
    """
    suggestions: list[SuggestionItem] = []

    # Check for unmatched files
    if result.unmatched_old:
        suggestions.append(
            SuggestionItem(
                category="flow",
                severity="high",
                message=f"有 {len(result.unmatched_old)} 个旧版本 flow 文件未匹配到新版本，"
                f"可能已被删除或重命名: {', '.join(result.unmatched_old[:3])}",
                affected_flows=result.unmatched_old,
            )
        )

    if result.unmatched_new:
        suggestions.append(
            SuggestionItem(
                category="flow",
                severity="high",
                message=f"有 {len(result.unmatched_new)} 个新版本 flow 文件未匹配到旧版本，"
                f"可能是新增: {', '.join(result.unmatched_new[:3])}",
                affected_flows=result.unmatched_new,
            )
        )

    for summary in result.flow_summaries:
        _suggest_for_pair(summary, suggestions)

    # Sort by severity descending
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    suggestions.sort(key=lambda x: severity_order.get(x.severity, 4))
    return suggestions


def _suggest_for_pair(
    summary: FlowPairSummary, suggestions: list[SuggestionItem]
) -> None:
    flow_name = summary.new_flow or summary.old_flow

    if summary.added_suites:
        suggestions.append(
            SuggestionItem(
                category="flow",
                severity="medium",
                message=f"Flow '{flow_name}' 中新增了 {len(summary.added_suites)} 个 test suite，"
                f"请确认是否为预期添加: {', '.join(summary.added_suites[:3])}",
                affected_suites=summary.added_suites,
                affected_flows=[flow_name],
            )
        )

    if summary.removed_suites:
        suggestions.append(
            SuggestionItem(
                category="flow",
                severity="high",
                message=f"Flow '{flow_name}' 中删除了 {len(summary.removed_suites)} 个 test suite，"
                f"请检查是否有遗漏: {', '.join(summary.removed_suites[:3])}",
                affected_suites=summary.removed_suites,
                affected_flows=[flow_name],
            )
        )

    if summary.order_changed_suites:
        suggestions.append(
            SuggestionItem(
                category="flow",
                severity="low",
                message=f"Flow '{flow_name}' 中有 {len(summary.order_changed_suites)} 个 suite 执行顺序发生变化，"
                f"可能影响 test flow 逻辑: {', '.join(summary.order_changed_suites[:3])}",
                affected_suites=summary.order_changed_suites,
                affected_flows=[flow_name],
            )
        )

    # Per-suite config suggestions
    timing_suites: list[str] = []
    level_suites: list[str] = []
    testtable_suites: list[str] = []
    vector_suites: list[str] = []
    testmethod_suites: list[str] = []
    suite_config_suites: list[str] = []

    for sc in summary.suite_summaries:
        if sc.timing_changed:
            timing_suites.append(sc.suite_name)
        if sc.level_changed:
            level_suites.append(sc.suite_name)
        if sc.testtable_changed:
            testtable_suites.append(sc.suite_name)
        if sc.vector_changed:
            vector_suites.append(sc.suite_name)
        if sc.testmethod_changed:
            testmethod_suites.append(sc.suite_name)
        if sc.suite_config_changed:
            suite_config_suites.append(sc.suite_name)

    if timing_suites:
        suggestions.append(
            SuggestionItem(
                category="timing",
                severity="high",
                message=f"有 {len(timing_suites)} 个 suite 的 timing 配置发生变更，"
                f"请重点 review: {', '.join(timing_suites[:3])}",
                affected_suites=timing_suites,
                affected_flows=[flow_name],
            )
        )

    if level_suites:
        suggestions.append(
            SuggestionItem(
                category="level",
                severity="high",
                message=f"有 {len(level_suites)} 个 suite 的 level 配置发生变更，"
                f"请确认电压/电流设置: {', '.join(level_suites[:3])}",
                affected_suites=level_suites,
                affected_flows=[flow_name],
            )
        )

    if testtable_suites:
        suggestions.append(
            SuggestionItem(
                category="testtable",
                severity="medium",
                message=f"有 {len(testtable_suites)} 个 suite 的 testtable (USL/LSL) 发生变更，"
                f"请确认 limit 调整是否合理: {', '.join(testtable_suites[:3])}",
                affected_suites=testtable_suites,
                affected_flows=[flow_name],
            )
        )

    if vector_suites:
        suggestions.append(
            SuggestionItem(
                category="vector",
                severity="medium",
                message=f"有 {len(vector_suites)} 个 suite 的 vector pattern 映射发生变更，"
                f"请确认 pattern 文件是否正确: {', '.join(vector_suites[:3])}",
                affected_suites=vector_suites,
                affected_flows=[flow_name],
            )
        )

    if testmethod_suites:
        suggestions.append(
            SuggestionItem(
                category="testmethod",
                severity="medium",
                message=f"有 {len(testmethod_suites)} 个 suite 的 testmethod 发生变更，"
                f"请确认 test class 或 ID 是否正确: {', '.join(testmethod_suites[:3])}",
                affected_suites=testmethod_suites,
                affected_flows=[flow_name],
            )
        )

    if suite_config_suites:
        suggestions.append(
            SuggestionItem(
                category="suite_config",
                severity="low",
                message=f"有 {len(suite_config_suites)} 个 suite 的参数配置发生变更，"
                f"请检查 override 参数: {', '.join(suite_config_suites[:3])}",
                affected_suites=suite_config_suites,
                affected_flows=[flow_name],
            )
        )
