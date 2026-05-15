#!/usr/bin/env python3
"""MCP Server for ate-smt7-diff: exposes diff capabilities via MCP stdio protocol."""

from __future__ import annotations

import json
import logging
from collections import OrderedDict
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from ate_smt7_diff.agent import discover, explain, suggest, validate
from ate_smt7_diff.builder import diff_flow_files
from ate_smt7_diff.flow_matcher import FlowMatcher
from ate_smt7_diff.formatters.json import format_json
from ate_smt7_diff.formatters.markdown import format_markdown
from ate_smt7_diff.models import BatchDiffReport, DiffReport

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

mcp = FastMCP("ate-smt7-diff")

# ---------------------------------------------------------------------------
# In-memory LRU cache for recent reports (max 10)
# ---------------------------------------------------------------------------

_report_cache: OrderedDict[str, DiffReport | BatchDiffReport] = OrderedDict()
_agent_cache: OrderedDict[str, object] = OrderedDict()
_MAX_CACHE = 10


def _cache_key(old: str, new: str) -> str:
    return f"{old}::{new}"


def _store_report(key: str, report: DiffReport | BatchDiffReport) -> None:
    if key in _report_cache:
        _report_cache.move_to_end(key)
    else:
        if len(_report_cache) >= _MAX_CACHE:
            _report_cache.popitem(last=False)
        _report_cache[key] = report


def _get_report(key: str) -> DiffReport | BatchDiffReport | None:
    if key in _report_cache:
        _report_cache.move_to_end(key)
        return _report_cache[key]
    return None


def _store_agent(key: str, result: object) -> None:
    if key in _agent_cache:
        _agent_cache.move_to_end(key)
    else:
        if len(_agent_cache) >= _MAX_CACHE:
            _agent_cache.popitem(last=False)
        _agent_cache[key] = result


def _get_agent(key: str) -> object | None:
    if key in _agent_cache:
        _agent_cache.move_to_end(key)
        return _agent_cache[key]
    return None


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@mcp.tool()
def list_program_packages(directory: str) -> str:
    """List subdirectories under a path that look like SMT7 program packages.

    A package is identified by having a ``testflow/`` subdirectory.
    """
    root = Path(directory).expanduser().resolve()
    if not root.is_dir():
        return json.dumps(
            {"error": f"Not a directory: {directory}"}, indent=2, ensure_ascii=False
        )

    packages: list[dict[str, str]] = []
    for child in sorted(root.iterdir()):
        if child.is_dir() and (child / "testflow").is_dir():
            flow_files = sorted(f.name for f in (child / "testflow").glob("*.flow"))
            packages.append(
                {
                    "name": child.name,
                    "path": str(child),
                    "flow_files": json.dumps(flow_files),
                }
            )

    return json.dumps(
        {"directory": str(root), "packages": packages},
        indent=2,
        ensure_ascii=False,
    )


@mcp.tool()
def suggest_flow_pairs(
    old_package: str, new_package: str, match_config: str | None = None
) -> str:
    """Suggest paired flow files between two program packages.

    Returns the matched pairs and any unmatched files.
    """
    old_dir = Path(old_package).expanduser().resolve() / "testflow"
    new_dir = Path(new_package).expanduser().resolve() / "testflow"

    if not old_dir.is_dir():
        return json.dumps(
            {"error": f"testflow directory not found: {old_dir}"},
            indent=2,
            ensure_ascii=False,
        )
    if not new_dir.is_dir():
        return json.dumps(
            {"error": f"testflow directory not found: {new_dir}"},
            indent=2,
            ensure_ascii=False,
        )

    matcher = FlowMatcher.from_config(match_config)
    pairs = matcher.match_directories(old_dir, new_dir)

    matched = [{"old": str(o), "new": str(n)} for o, n in pairs]
    old_names = {f.name for f in old_dir.glob("*.flow")}
    new_names = {f.name for f in new_dir.glob("*.flow")}
    matched_old = {o.name for o, _ in pairs}
    matched_new = {n.name for _, n in pairs}

    return json.dumps(
        {
            "old_package": old_package,
            "new_package": new_package,
            "matched_pairs": matched,
            "unmatched_old": sorted(old_names - matched_old),
            "unmatched_new": sorted(new_names - matched_new),
        },
        indent=2,
        ensure_ascii=False,
    )


@mcp.tool()
def diff_flows(
    old_path: str,
    new_path: str,
    suite_diff: bool = False,
    load_configs: bool = False,
    testtable_diff: bool = False,
    testmethod_diff: bool = False,
) -> str:
    """Run diff between two .flow files or two program packages.

    If the paths point to directories, treat them as program packages
    and diff all matched flow file pairs.

    Args:
        old_path: Path to old .flow file or program package directory.
        new_path: Path to new .flow file or program package directory.
        suite_diff: Also diff test suite configurations.
        load_configs: Load timing/level/vector/testtable configs.
        testtable_diff: Also diff testtable CSV files.
        testmethod_diff: Also diff testmethod source files.
    """
    old_p = Path(old_path).expanduser().resolve()
    new_p = Path(new_path).expanduser().resolve()

    try:
        if old_p.is_dir() and new_p.is_dir():
            return _diff_packages(
                old_p, new_p, suite_diff, load_configs, testtable_diff, testmethod_diff
            )

        if not old_p.is_file() or old_p.suffix.lower() != ".flow":
            return json.dumps(
                {"error": f"Expected .flow file: {old_path}"},
                indent=2,
                ensure_ascii=False,
            )
        if not new_p.is_file() or new_p.suffix.lower() != ".flow":
            return json.dumps(
                {"error": f"Expected .flow file: {new_path}"},
                indent=2,
                ensure_ascii=False,
            )

        report = diff_flow_files(
            str(old_p),
            str(new_p),
            include_suite_diff=suite_diff,
            include_config_views=load_configs or testtable_diff or testmethod_diff,
            include_testtable_diff=load_configs or testtable_diff,
            include_testmethod_diff=load_configs or testmethod_diff,
        )
        key = _cache_key(str(old_p), str(new_p))
        _store_report(key, report)

        return format_json(report)
    except (FileNotFoundError, PermissionError, ValueError) as e:
        return json.dumps(
            {"error_type": type(e).__name__, "message": str(e)},
            indent=2,
            ensure_ascii=False,
        )


def _diff_packages(
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
        return json.dumps(
            {"error": f"testflow directory not found: {old_flow_dir}"},
            indent=2,
            ensure_ascii=False,
        )
    if not new_flow_dir.is_dir():
        return json.dumps(
            {"error": f"testflow directory not found: {new_flow_dir}"},
            indent=2,
            ensure_ascii=False,
        )

    matcher = FlowMatcher.from_config(None)
    pairs = matcher.match_directories(old_flow_dir, new_flow_dir)
    if not pairs:
        return json.dumps(
            {"error": "No flow files matched between packages."},
            indent=2,
            ensure_ascii=False,
        )

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

    key = _cache_key(str(old_pkg), str(new_pkg))
    _store_report(key, batch)

    # Return a lightweight JSON summary (full per-pair JSON can be huge)
    result = {
        "old_package": str(old_pkg),
        "new_package": str(new_pkg),
        "total_pairs": batch.total_pairs,
        "pairs_with_changes": len(batch.pairs_with_changes),
        "pairs": [
            {
                "old": o,
                "new": n,
                "added": r.added,
                "removed": r.removed,
                "order_changed": r.order_changed,
            }
            for o, n, r in batch.pairs
        ],
    }
    return json.dumps(result, indent=2, ensure_ascii=False)


@mcp.tool()
def query_diff_report(
    old_path: str,
    new_path: str,
    category: str | None = None,
) -> str:
    """Query a cached diff report.

    Args:
        old_path: Old file or package path (must match prior diff_flows call).
        new_path: New file or package path (must match prior diff_flows call).
        category: Optional filter — one of added, removed, order_changed,
                  suite_config, timing, level, testtable, vector, testmethod.
    """
    old_p = str(Path(old_path).expanduser().resolve())
    new_p = str(Path(new_path).expanduser().resolve())
    key = _cache_key(old_p, new_p)
    report = _get_report(key)
    if report is None:
        return json.dumps(
            {"error": "Report not found in cache. Run diff_flows first."},
            indent=2,
            ensure_ascii=False,
        )

    # If batch report, return summary
    if isinstance(report, BatchDiffReport):
        return json.dumps(
            {
                "old_package": report.old_package,
                "new_package": report.new_package,
                "total_pairs": report.total_pairs,
                "pairs_with_changes": len(report.pairs_with_changes),
            },
            indent=2,
            ensure_ascii=False,
        )

    # Single report filtering
    result: dict[str, object] = {
        "old_file": report.old_file,
        "new_file": report.new_file,
        "added": report.added,
        "removed": report.removed,
        "order_changed": report.order_changed,
    }

    if category == "suite_config" and report.suite_config_report:
        result["suite_config"] = format_json(
            DiffReport(old_file="", new_file="", old_tests=[], new_tests=[], diffs=[], suite_config_report=report.suite_config_report)
        )
    elif category == "timing" and report.timing_spec_diffs:
        result["timing_spec_diffs"] = [str(d) for d in report.timing_spec_diffs]
    elif category == "level" and report.level_spec_diffs:
        result["level_spec_diffs"] = [str(d) for d in report.level_spec_diffs]
    elif category == "testtable" and report.testtable_diffs:
        result["testtable_diffs"] = [str(d) for d in report.testtable_diffs]
    elif category == "vector" and report.vector_diffs:
        result["vector_diffs"] = [str(d) for d in report.vector_diffs]
    elif category == "testmethod" and report.testmethod_diffs:
        result["testmethod_diffs"] = [str(d) for d in report.testmethod_diffs]

    return json.dumps(result, indent=2, ensure_ascii=False)


@mcp.tool()
def export_diff_report(
    old_path: str,
    new_path: str,
    format: str = "markdown",
) -> str:
    """Export a cached diff report to markdown or json.

    Args:
        old_path: Old file or package path (must match prior diff_flows call).
        new_path: New file or package path (must match prior diff_flows call).
        format: "markdown" or "json".
    """
    old_p = str(Path(old_path).expanduser().resolve())
    new_p = str(Path(new_path).expanduser().resolve())
    key = _cache_key(old_p, new_p)
    report = _get_report(key)
    if report is None:
        return json.dumps(
            {"error": "Report not found in cache. Run diff_flows first."},
            indent=2,
            ensure_ascii=False,
        )

    if format == "json":
        if isinstance(report, BatchDiffReport):
            from ate_smt7_diff.formatters.batch_json import format_batch_json
            return format_batch_json(report)
        return format_json(report)

    if format == "markdown":
        if isinstance(report, BatchDiffReport):
            from ate_smt7_diff.formatters.batch_markdown import format_batch_markdown
            return format_batch_markdown(report)
        return format_markdown(report)

    return json.dumps(
        {"error": f"Unsupported format: {format}. Use 'markdown' or 'json'."},
        indent=2,
        ensure_ascii=False,
    )


@mcp.tool()
def smart_diff_discover(
    old_package: str,
    new_package: str,
    load_configs: bool = True,
) -> str:
    """Run intelligent discovery between two program packages.

    Returns a structured summary of all changes with severity levels.
    """
    try:
        result = discover(old_package, new_package, load_configs=load_configs)
        key = _cache_key(old_package, new_package)
        _store_agent(key, result)

        return json.dumps(
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
                        "old_flow": s.old_flow,
                        "new_flow": s.new_flow,
                        "added_suites": s.added_suites,
                        "removed_suites": s.removed_suites,
                        "order_changed_suites": s.order_changed_suites,
                        "has_config_changes": s.has_config_changes,
                        "suite_change_count": len(s.suite_summaries),
                    }
                    for s in result.flow_summaries
                ],
            },
            indent=2,
            ensure_ascii=False,
        )
    except (FileNotFoundError, PermissionError, ValueError) as e:
        return json.dumps(
            {"error_type": type(e).__name__, "message": str(e)},
            indent=2,
            ensure_ascii=False,
        )


@mcp.tool()
def smart_diff_suggest(
    old_package: str,
    new_package: str,
) -> str:
    """Generate actionable suggestions from a discovery result.

    Returns prioritized suggestions for what the user should review.
    """
    key = _cache_key(old_package, new_package)
    result = _get_agent(key)
    if result is None:
        return json.dumps(
            {"error": "Discovery result not found. Run smart_diff_discover first."},
            indent=2,
            ensure_ascii=False,
        )

    suggestions = suggest(result)
    return json.dumps(
        {
            "suggestions": [
                {
                    "category": s.category,
                    "severity": s.severity,
                    "message": s.message,
                    "affected_suites": s.affected_suites,
                    "affected_flows": s.affected_flows,
                }
                for s in suggestions
            ]
        },
        indent=2,
        ensure_ascii=False,
    )


@mcp.tool()
def smart_diff_explain(
    old_package: str,
    new_package: str,
    focus_category: str | None = None,
    focus_suite: str | None = None,
) -> str:
    """Generate structured explanations for discovered changes.

    Args:
        focus_category: Optional filter by category (timing, level, etc.).
        focus_suite: Optional filter by suite name.
    """
    key = _cache_key(old_package, new_package)
    result = _get_agent(key)
    if result is None:
        return json.dumps(
            {"error": "Discovery result not found. Run smart_diff_discover first."},
            indent=2,
            ensure_ascii=False,
        )

    explanations = explain(result, focus_category, focus_suite)
    return json.dumps(
        {
            "explanations": [
                {
                    "suite_name": e.suite_name,
                    "category": e.category,
                    "change_type": e.change_type,
                    "description": e.description,
                }
                for e in explanations
            ]
        },
        indent=2,
        ensure_ascii=False,
    )


@mcp.tool()
def smart_diff_validate(
    old_package: str,
    new_package: str,
) -> str:
    """Run validation rules against a discovery result.

    Detects anomalies and returns pass/fail with detailed findings.
    """
    key = _cache_key(old_package, new_package)
    result = _get_agent(key)
    if result is None:
        return json.dumps(
            {"error": "Discovery result not found. Run smart_diff_discover first."},
            indent=2,
            ensure_ascii=False,
        )

    validation = validate(result)
    return json.dumps(
        {
            "passed": validation.passed,
            "summary": validation.summary,
            "findings": [
                {
                    "rule": f.rule,
                    "severity": f.severity,
                    "message": f.message,
                    "affected_suites": f.affected_suites,
                    "affected_flows": f.affected_flows,
                }
                for f in validation.findings
            ],
        },
        indent=2,
        ensure_ascii=False,
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run(transport="stdio")
