#!/usr/bin/env python3
"""Explanation module: produce structured explanations for specific diffs."""

from __future__ import annotations

from dataclasses import dataclass, field

from ate_smt7_diff.agent.discover import DiscoveryResult, FlowPairSummary


@dataclass
class ExplanationItem:
    """Structured explanation for a single change."""

    suite_name: str
    category: str  # flow, timing, level, testtable, vector, testmethod, suite_config
    change_type: str  # added, removed, changed, order_changed
    description: str
    details: dict[str, object] = field(default_factory=dict)


def explain(
    result: DiscoveryResult,
    focus_category: str | None = None,
    focus_suite: str | None = None,
) -> list[ExplanationItem]:
    """Generate structured explanations for discovered changes.

    Args:
        result: Discovery result from discover().
        focus_category: Optional filter by category (timing, level, etc.).
        focus_suite: Optional filter by suite name.
    """
    explanations: list[ExplanationItem] = []

    for summary in result.flow_summaries:
        _explain_pair(summary, explanations, focus_category, focus_suite)

    return explanations


def _explain_pair(
    summary: FlowPairSummary,
    explanations: list[ExplanationItem],
    focus_category: str | None,
    focus_suite: str | None,
) -> None:
    for sc in summary.suite_summaries:
        if focus_suite and sc.suite_name != focus_suite:
            continue

        # Flow-level changes
        if sc.flow_changed and (not focus_category or focus_category == "flow"):
            if sc.suite_name in summary.added_suites:
                explanations.append(
                    ExplanationItem(
                        suite_name=sc.suite_name,
                        category="flow",
                        change_type="added",
                        description=f"Suite '{sc.suite_name}' 在新版本 flow 中被新增",
                    )
                )
            elif sc.suite_name in summary.removed_suites:
                explanations.append(
                    ExplanationItem(
                        suite_name=sc.suite_name,
                        category="flow",
                        change_type="removed",
                        description=f"Suite '{sc.suite_name}' 在新版本 flow 中被删除",
                    )
                )

        # Config-level changes
        if sc.timing_changed and (not focus_category or focus_category == "timing"):
            explanations.append(
                ExplanationItem(
                    suite_name=sc.suite_name,
                    category="timing",
                    change_type="changed",
                    description=f"Suite '{sc.suite_name}' 的 timing 配置发生变更，"
                    "可能包括 spec 值、pin 参数或 timingset 调整",
                )
            )

        if sc.level_changed and (not focus_category or focus_category == "level"):
            explanations.append(
                ExplanationItem(
                    suite_name=sc.suite_name,
                    category="level",
                    change_type="changed",
                    description=f"Suite '{sc.suite_name}' 的 level 配置发生变更，"
                    "可能包括电压、电流或 pin level 调整",
                )
            )

        if sc.testtable_changed and (not focus_category or focus_category == "testtable"):
            explanations.append(
                ExplanationItem(
                    suite_name=sc.suite_name,
                    category="testtable",
                    change_type="changed",
                    description=f"Suite '{sc.suite_name}' 的 testtable 发生变更，"
                    "可能包括 USL/LSL limit 调整",
                )
            )

        if sc.vector_changed and (not focus_category or focus_category == "vector"):
            explanations.append(
                ExplanationItem(
                    suite_name=sc.suite_name,
                    category="vector",
                    change_type="changed",
                    description=f"Suite '{sc.suite_name}' 的 vector pattern 映射发生变更，"
                    "可能包括 pattern 文件名或路径调整",
                )
            )

        if sc.testmethod_changed and (not focus_category or focus_category == "testmethod"):
            explanations.append(
                ExplanationItem(
                    suite_name=sc.suite_name,
                    category="testmethod",
                    change_type="changed",
                    description=f"Suite '{sc.suite_name}' 的 testmethod 发生变更，"
                    "可能包括 test class、testmethod ID 或源文件修改",
                )
            )

        if sc.suite_config_changed and (not focus_category or focus_category == "suite_config"):
            explanations.append(
                ExplanationItem(
                    suite_name=sc.suite_name,
                    category="suite_config",
                    change_type="changed",
                    description=f"Suite '{sc.suite_name}' 的 suite 参数配置发生变更，"
                    "可能包括 flow 中的 override 参数调整",
                )
            )
