#!/usr/bin/env python3
"""MCP tools for smart diff agent-helper workflows."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from ate_smt7_diff.agent import discover, explain, suggest, validate
from ate_smt7_diff.agent.discover import DiscoveryResult
from ate_smt7_diff.mcp.cache import McpCache, cache_key
from ate_smt7_diff.mcp.serializers import error_response, exception_response, json_response


def smart_diff_discover(
    cache: McpCache,
    old_package: str,
    new_package: str,
    load_configs: bool = True,
) -> str:
    """Run intelligent discovery between two program packages."""
    try:
        result = discover(old_package, new_package, load_configs=load_configs)
        cache.store_agent(cache_key(old_package, new_package), result)

        return json_response(
            {
                "old_package": result.old_package,
                "new_package": result.new_package,
                "total_pairs": result.total_pairs,
                "pairs_with_changes": result.pairs_with_changes,
                "overall_severity": result.overall_severity,
                "unmatched_old": result.unmatched_old,
                "unmatched_new": result.unmatched_new,
                "flow_summaries": [
                    {
                        "old_flow": summary.old_flow,
                        "new_flow": summary.new_flow,
                        "added_suites": summary.added_suites,
                        "removed_suites": summary.removed_suites,
                        "order_changed_suites": summary.order_changed_suites,
                        "has_config_changes": summary.has_config_changes,
                        "suite_change_count": len(summary.suite_summaries),
                    }
                    for summary in result.flow_summaries
                ],
            }
        )
    except (FileNotFoundError, PermissionError, ValueError) as error:
        return exception_response(error)


def _get_discovery_result(
    cache: McpCache, old_package: str, new_package: str
) -> DiscoveryResult | None:
    result = cache.get_agent(cache_key(old_package, new_package))
    if isinstance(result, DiscoveryResult):
        return result
    return None


def smart_diff_suggest(cache: McpCache, old_package: str, new_package: str) -> str:
    """Generate actionable suggestions from a discovery result."""
    result = _get_discovery_result(cache, old_package, new_package)
    if result is None:
        return error_response("Discovery result not found. Run smart_diff_discover first.")

    suggestions = suggest(result)
    return json_response(
        {
            "suggestions": [
                {
                    "category": item.category,
                    "severity": item.severity,
                    "message": item.message,
                    "affected_suites": item.affected_suites,
                    "affected_flows": item.affected_flows,
                }
                for item in suggestions
            ]
        }
    )


def smart_diff_explain(
    cache: McpCache,
    old_package: str,
    new_package: str,
    focus_category: str | None = None,
    focus_suite: str | None = None,
) -> str:
    """Generate structured explanations for discovered changes."""
    result = _get_discovery_result(cache, old_package, new_package)
    if result is None:
        return error_response("Discovery result not found. Run smart_diff_discover first.")

    explanations = explain(result, focus_category, focus_suite)
    return json_response(
        {
            "explanations": [
                {
                    "suite_name": item.suite_name,
                    "category": item.category,
                    "change_type": item.change_type,
                    "description": item.description,
                }
                for item in explanations
            ]
        }
    )


def smart_diff_validate(cache: McpCache, old_package: str, new_package: str) -> str:
    """Run validation rules against a discovery result."""
    result = _get_discovery_result(cache, old_package, new_package)
    if result is None:
        return error_response("Discovery result not found. Run smart_diff_discover first.")

    validation = validate(result)
    return json_response(
        {
            "passed": validation.passed,
            "summary": validation.summary,
            "findings": [
                {
                    "rule": item.rule,
                    "severity": item.severity,
                    "message": item.message,
                    "affected_suites": item.affected_suites,
                    "affected_flows": item.affected_flows,
                }
                for item in validation.findings
            ],
        }
    )


def register_agent_tools(mcp: FastMCP, cache: McpCache) -> None:
    """Register agent-helper tools on a FastMCP server."""

    @mcp.tool()
    def smart_diff_discover(
        old_package: str,
        new_package: str,
        load_configs: bool = True,
    ) -> str:
        return globals()["smart_diff_discover"](cache, old_package, new_package, load_configs)

    @mcp.tool()
    def smart_diff_suggest(old_package: str, new_package: str) -> str:
        return globals()["smart_diff_suggest"](cache, old_package, new_package)

    @mcp.tool()
    def smart_diff_explain(
        old_package: str,
        new_package: str,
        focus_category: str | None = None,
        focus_suite: str | None = None,
    ) -> str:
        return globals()["smart_diff_explain"](
            cache,
            old_package,
            new_package,
            focus_category,
            focus_suite,
        )

    @mcp.tool()
    def smart_diff_validate(old_package: str, new_package: str) -> str:
        return globals()["smart_diff_validate"](cache, old_package, new_package)
