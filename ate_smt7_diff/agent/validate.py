#!/usr/bin/env python3
"""Validation module: apply rules to detect anomalies in diff results."""

from __future__ import annotations

from dataclasses import dataclass, field

from ate_smt7_diff.agent.discover import DiscoveryResult, FlowPairSummary


@dataclass
class ValidationItem:
    """A single validation finding."""

    rule: str
    severity: str  # error, warning, info
    message: str
    affected_suites: list[str] = field(default_factory=list)
    affected_flows: list[str] = field(default_factory=list)


@dataclass
class ValidationResult:
    """Complete validation result."""

    passed: bool
    findings: list[ValidationItem]
    summary: dict[str, int] = field(default_factory=dict)


def validate(result: DiscoveryResult) -> ValidationResult:
    """Run validation rules against a discovery result.

    Detects anomalies like missing suites, unpaired files,
    and suspicious config changes.
    """
    findings: list[ValidationItem] = []

    # Rule 1: Unmatched old flows
    if result.unmatched_old:
        findings.append(
            ValidationItem(
                rule="unmatched_old_flows",
                severity="warning",
                message=f"旧版本中有 {len(result.unmatched_old)} 个 flow 文件未匹配，"
                "请确认是否被意外删除",
                affected_flows=result.unmatched_old,
            )
        )

    # Rule 2: Unmatched new flows
    if result.unmatched_new:
        findings.append(
            ValidationItem(
                rule="unmatched_new_flows",
                severity="warning",
                message=f"新版本中有 {len(result.unmatched_new)} 个 flow 文件未匹配，"
                "请确认是否为预期新增",
                affected_flows=result.unmatched_new,
            )
        )

    # Rule 3: Check for removed suites
    for summary in result.flow_summaries:
        if summary.removed_suites:
            findings.append(
                ValidationItem(
                    rule="suites_removed",
                    severity="error",
                    message=f"Flow '{summary.new_flow}' 中删除了 {len(summary.removed_suites)} 个 suite，"
                    "请确认是否有遗漏",
                    affected_suites=summary.removed_suites,
                    affected_flows=[summary.new_flow],
                )
            )

        # Rule 4: Check for timing changes without level changes (suspicious)
        timing_only_suites = [
            sc.suite_name
            for sc in summary.suite_summaries
            if sc.timing_changed and not sc.level_changed
        ]
        if timing_only_suites:
            findings.append(
                ValidationItem(
                    rule="timing_without_level",
                    severity="info",
                    message=f"以下 {len(timing_only_suites)} 个 suite 仅 timing 变更而 level 未变，"
                    "请确认是否同时需要调整 level",
                    affected_suites=timing_only_suites,
                    affected_flows=[summary.new_flow],
                )
            )

        # Rule 5: Check for testtable changes (USL/LSL should be reviewed carefully)
        testtable_changed_suites = [
            sc.suite_name
            for sc in summary.suite_summaries
            if sc.testtable_changed
        ]
        if testtable_changed_suites:
            findings.append(
                ValidationItem(
                    rule="testtable_changed",
                    severity="warning",
                    message=f"以下 {len(testtable_changed_suites)} 个 suite 的 testtable (USL/LSL) 发生变更，"
                    "请确认 limit 调整是否经过验证",
                    affected_suites=testtable_changed_suites,
                    affected_flows=[summary.new_flow],
                )
            )

        # Rule 6: Check for vector pattern changes
        vector_changed_suites = [
            sc.suite_name
            for sc in summary.suite_summaries
            if sc.vector_changed
        ]
        if vector_changed_suites:
            findings.append(
                ValidationItem(
                    rule="vector_changed",
                    severity="warning",
                    message=f"以下 {len(vector_changed_suites)} 个 suite 的 vector pattern 映射发生变更，"
                    "请确认 pattern 文件是否已更新到测试机",
                    affected_suites=vector_changed_suites,
                    affected_flows=[summary.new_flow],
                )
            )

    # Compute summary
    severity_counts: dict[str, int] = {}
    for finding in findings:
        severity_counts[finding.severity] = severity_counts.get(finding.severity, 0) + 1

    passed = not any(f.severity == "error" for f in findings)

    return ValidationResult(
        passed=passed,
        findings=findings,
        summary=severity_counts,
    )
