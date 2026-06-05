#!/usr/bin/env python3
"""MCP tools for flow and package diff reports."""

from __future__ import annotations

from pathlib import Path

from mcp.server.fastmcp import FastMCP

from ate_smt7_diff.builder import diff_flow_files
from ate_smt7_diff.flow_matcher import FlowMatcher
from ate_smt7_diff.formatters.json import format_json
from ate_smt7_diff.formatters.markdown import format_markdown
from ate_smt7_diff.mcp.cache import McpCache, cache_key
from ate_smt7_diff.mcp.serializers import error_response, exception_response, json_response
from ate_smt7_diff.models import BatchDiffReport, DiffReport


def diff_flows(  # noqa: PLR0913 - MCP tool mirrors CLI flags.
    cache: McpCache,
    old_path: str,
    new_path: str,
    suite_diff: bool = False,
    load_configs: bool = False,
    testtable_diff: bool = False,
    testmethod_diff: bool = False,
) -> str:
    """Run diff between two .flow files or two program packages."""
    old_p = Path(old_path).expanduser().resolve()
    new_p = Path(new_path).expanduser().resolve()

    try:
        if old_p.is_dir() and new_p.is_dir():
            return _diff_packages(
                cache,
                old_p,
                new_p,
                suite_diff,
                load_configs,
                testtable_diff,
                testmethod_diff,
            )

        if not old_p.is_file() or old_p.suffix.lower() != ".flow":
            return error_response(f"Expected .flow file: {old_path}")
        if not new_p.is_file() or new_p.suffix.lower() != ".flow":
            return error_response(f"Expected .flow file: {new_path}")

        report = diff_flow_files(
            str(old_p),
            str(new_p),
            include_suite_diff=suite_diff,
            include_config_views=load_configs or testtable_diff or testmethod_diff,
            include_testtable_diff=load_configs or testtable_diff,
            include_testmethod_diff=load_configs or testmethod_diff,
        )
        cache.store_report(cache_key(str(old_p), str(new_p)), report)

        return format_json(report)
    except (FileNotFoundError, PermissionError, ValueError) as error:
        return exception_response(error)


def _diff_packages(  # noqa: PLR0913 - Mirrors diff_flows package-mode flags.
    cache: McpCache,
    old_pkg: Path,
    new_pkg: Path,
    suite_diff: bool,
    load_configs: bool,
    testtable_diff: bool,
    testmethod_diff: bool,
) -> str:
    old_flow_dir = old_pkg / "testflow"
    new_flow_dir = new_pkg / "testflow"

    if not old_flow_dir.is_dir():
        return error_response(f"testflow directory not found: {old_flow_dir}")
    if not new_flow_dir.is_dir():
        return error_response(f"testflow directory not found: {new_flow_dir}")

    matcher = FlowMatcher.from_config(None)
    pairs = matcher.match_directories(old_flow_dir, new_flow_dir)
    if not pairs:
        return error_response("No flow files matched between packages.")

    batch = BatchDiffReport(old_package=str(old_pkg), new_package=str(new_pkg))
    for old_flow, new_flow in pairs:
        report = diff_flow_files(
            str(old_flow),
            str(new_flow),
            include_suite_diff=suite_diff,
            include_config_views=load_configs or testtable_diff or testmethod_diff,
            include_testtable_diff=load_configs or testtable_diff,
            include_testmethod_diff=load_configs or testmethod_diff,
        )
        batch.pairs.append((str(old_flow), str(new_flow), report))

    cache.store_report(cache_key(str(old_pkg), str(new_pkg)), batch)

    return json_response(
        {
            "old_package": str(old_pkg),
            "new_package": str(new_pkg),
            "total_pairs": batch.total_pairs,
            "pairs_with_changes": len(batch.pairs_with_changes),
            "pairs": [
                {
                    "old": old,
                    "new": new,
                    "added": report.added,
                    "removed": report.removed,
                    "order_changed": report.order_changed,
                }
                for old, new, report in batch.pairs
            ],
        }
    )


def query_diff_report(
    cache: McpCache,
    old_path: str,
    new_path: str,
    category: str | None = None,
) -> str:
    """Query a cached diff report."""
    old_p = str(Path(old_path).expanduser().resolve())
    new_p = str(Path(new_path).expanduser().resolve())
    report = cache.get_report(cache_key(old_p, new_p))
    if report is None:
        return error_response("Report not found in cache. Run diff_flows first.")

    if isinstance(report, BatchDiffReport):
        return json_response(
            {
                "old_package": report.old_package,
                "new_package": report.new_package,
                "total_pairs": report.total_pairs,
                "pairs_with_changes": len(report.pairs_with_changes),
            }
        )

    if not isinstance(report, DiffReport):
        return error_response("Cached report has an unsupported type.")

    result: dict[str, object] = {
        "old_file": report.old_file,
        "new_file": report.new_file,
        "added": report.added,
        "removed": report.removed,
        "order_changed": report.order_changed,
    }

    if category == "suite_config" and report.suite_config_report:
        result["suite_config"] = format_json(
            DiffReport(
                old_file="",
                new_file="",
                old_tests=[],
                new_tests=[],
                diffs=[],
                suite_config_report=report.suite_config_report,
            )
        )
    elif category == "timing" and report.timing_spec_diffs:
        result["timing_spec_diffs"] = [str(diff) for diff in report.timing_spec_diffs]
    elif category == "level" and report.level_spec_diffs:
        result["level_spec_diffs"] = [str(diff) for diff in report.level_spec_diffs]
    elif category == "testtable" and report.testtable_diffs:
        result["testtable_diffs"] = [str(diff) for diff in report.testtable_diffs]
    elif category == "vector" and report.vector_diffs:
        result["vector_diffs"] = [str(diff) for diff in report.vector_diffs]
    elif category == "testmethod" and report.testmethod_diffs:
        result["testmethod_diffs"] = [str(diff) for diff in report.testmethod_diffs]

    return json_response(result)


def export_diff_report(
    cache: McpCache,
    old_path: str,
    new_path: str,
    format: str = "markdown",
) -> str:
    """Export a cached diff report to markdown or json."""
    old_p = str(Path(old_path).expanduser().resolve())
    new_p = str(Path(new_path).expanduser().resolve())
    report = cache.get_report(cache_key(old_p, new_p))
    if report is None:
        return error_response("Report not found in cache. Run diff_flows first.")

    if format == "json":
        if isinstance(report, BatchDiffReport):
            from ate_smt7_diff.formatters.batch_json import format_batch_json

            return format_batch_json(report)
        if isinstance(report, DiffReport):
            return format_json(report)

    if format == "markdown":
        if isinstance(report, BatchDiffReport):
            from ate_smt7_diff.formatters.batch_markdown import format_batch_markdown

            return format_batch_markdown(report)
        if isinstance(report, DiffReport):
            return format_markdown(report)

    return error_response(f"Unsupported format: {format}. Use 'markdown' or 'json'.")


def register_diff_tools(mcp: FastMCP, cache: McpCache) -> None:
    """Register diff tools on a FastMCP server."""

    @mcp.tool()
    def diff_flows(  # noqa: PLR0913 - MCP tool mirrors CLI flags.
        old_path: str,
        new_path: str,
        suite_diff: bool = False,
        load_configs: bool = False,
        testtable_diff: bool = False,
        testmethod_diff: bool = False,
    ) -> str:
        return globals()["diff_flows"](
            cache,
            old_path,
            new_path,
            suite_diff,
            load_configs,
            testtable_diff,
            testmethod_diff,
        )

    @mcp.tool()
    def query_diff_report(
        old_path: str,
        new_path: str,
        category: str | None = None,
    ) -> str:
        return globals()["query_diff_report"](cache, old_path, new_path, category)

    @mcp.tool()
    def export_diff_report(
        old_path: str,
        new_path: str,
        format: str = "markdown",
    ) -> str:
        return globals()["export_diff_report"](cache, old_path, new_path, format)
