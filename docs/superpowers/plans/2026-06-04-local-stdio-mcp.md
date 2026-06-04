# Local Stdio MCP Architecture Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor `ate-smt7-diff` into a modular local stdio MCP server usable from Codex CLI, Claude Code, Cursor, Gemini CLI, OpenCode, and GitHub Copilot CLI.

**Architecture:** Keep `mcp_server.py` as a compatibility wrapper and move the real MCP implementation into `ate_smt7_diff/mcp/`. Tools are grouped by package discovery, flow diff, and agent-helper workflows; resources expose manifest, usage, client setup, and examples for MCP clients.

**Tech Stack:** Python 3.10, FastMCP from `mcp`, pytest, uv.

---

## File Structure

- Create `ate_smt7_diff/mcp/__init__.py`: package exports for MCP server helpers.
- Create `ate_smt7_diff/mcp/cache.py`: local LRU state for cached diff reports and discovery results.
- Create `ate_smt7_diff/mcp/serializers.py`: JSON response helpers.
- Create `ate_smt7_diff/mcp/tools/__init__.py`: tool registration package marker.
- Create `ate_smt7_diff/mcp/tools/packages.py`: package discovery tools and registration.
- Create `ate_smt7_diff/mcp/tools/diff.py`: flow diff tools and registration.
- Create `ate_smt7_diff/mcp/tools/agent.py`: smart discovery, suggest, explain, and validate tools and registration.
- Create `ate_smt7_diff/mcp/resources.py`: MCP resources and registration.
- Create `ate_smt7_diff/mcp/server.py`: `create_server()` and `run_stdio()` entry points.
- Modify `mcp_server.py`: reduce to backward-compatible wrapper.
- Create `docs/mcp/README.md`: local MCP overview and launch commands.
- Create `docs/mcp/clients.md`: client setup notes for the requested clients.
- Create `tests/mcp/test_cache_serializers.py`: cache and JSON helper tests.
- Create `tests/mcp/test_tools_packages.py`: package tool tests.
- Create `tests/mcp/test_tools_diff.py`: diff tool tests.
- Create `tests/mcp/test_tools_agent.py`: agent-helper tool tests.
- Create `tests/mcp/test_resources_server.py`: resource and server registration tests.

---

### Task 1: Cache And JSON Serializer Primitives

**Files:**
- Create: `tests/mcp/test_cache_serializers.py`
- Create: `ate_smt7_diff/mcp/__init__.py`
- Create: `ate_smt7_diff/mcp/cache.py`
- Create: `ate_smt7_diff/mcp/serializers.py`

- [ ] **Step 1: Write the failing tests**

```python
#!/usr/bin/env python3
"""Tests for MCP cache and serializer primitives."""

from __future__ import annotations

import json

from ate_smt7_diff.mcp.cache import McpCache, cache_key
from ate_smt7_diff.mcp.serializers import error_response, exception_response, json_response


def test_cache_key_joins_old_and_new_paths() -> None:
    assert cache_key("/old.flow", "/new.flow") == "/old.flow::/new.flow"


def test_report_cache_uses_lru_eviction() -> None:
    cache = McpCache(max_entries=2)
    cache.store_report("a", "report-a")
    cache.store_report("b", "report-b")
    assert cache.get_report("a") == "report-a"

    cache.store_report("c", "report-c")

    assert cache.get_report("a") == "report-a"
    assert cache.get_report("b") is None
    assert cache.get_report("c") == "report-c"


def test_agent_cache_uses_lru_eviction() -> None:
    cache = McpCache(max_entries=2)
    cache.store_agent("a", {"id": "a"})
    cache.store_agent("b", {"id": "b"})
    assert cache.get_agent("a") == {"id": "a"}

    cache.store_agent("c", {"id": "c"})

    assert cache.get_agent("a") == {"id": "a"}
    assert cache.get_agent("b") is None
    assert cache.get_agent("c") == {"id": "c"}


def test_json_response_preserves_unicode_and_indentation() -> None:
    payload = json.loads(json_response({"message": "删除", "count": 1}))

    assert payload == {"message": "删除", "count": 1}


def test_error_response_shape() -> None:
    assert json.loads(error_response("bad input")) == {"error": "bad input"}


def test_exception_response_shape() -> None:
    assert json.loads(exception_response(ValueError("bad value"))) == {
        "error_type": "ValueError",
        "message": "bad value",
    }
```

- [ ] **Step 2: Run the test and verify it fails**

Run:

```bash
uv run pytest tests/mcp/test_cache_serializers.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'ate_smt7_diff.mcp'`.

- [ ] **Step 3: Add the MCP package marker**

Create `ate_smt7_diff/mcp/__init__.py`:

```python
#!/usr/bin/env python3
"""MCP integration package for ate-smt7-diff."""

from ate_smt7_diff.mcp.cache import McpCache, cache_key

__all__ = ["McpCache", "cache_key"]
```

- [ ] **Step 4: Implement the cache**

Create `ate_smt7_diff/mcp/cache.py`:

```python
#!/usr/bin/env python3
"""Local in-process cache for MCP tool results."""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass, field
from typing import TypeVar

from ate_smt7_diff.models import BatchDiffReport, DiffReport

ReportValue = DiffReport | BatchDiffReport | object
AgentValue = object
T = TypeVar("T")


def cache_key(old: str, new: str) -> str:
    """Build the stable cache key shared by diff and agent tools."""
    return f"{old}::{new}"


@dataclass
class McpCache:
    """Bounded LRU cache used by one MCP server process."""

    max_entries: int = 10
    report_cache: OrderedDict[str, ReportValue] = field(default_factory=OrderedDict)
    agent_cache: OrderedDict[str, AgentValue] = field(default_factory=OrderedDict)

    def store_report(self, key: str, report: ReportValue) -> None:
        self._store(self.report_cache, key, report)

    def get_report(self, key: str) -> ReportValue | None:
        return self._get(self.report_cache, key)

    def store_agent(self, key: str, result: AgentValue) -> None:
        self._store(self.agent_cache, key, result)

    def get_agent(self, key: str) -> AgentValue | None:
        return self._get(self.agent_cache, key)

    def _store(self, cache: OrderedDict[str, T], key: str, value: T) -> None:
        if key in cache:
            cache.move_to_end(key)
        elif len(cache) >= self.max_entries:
            cache.popitem(last=False)
        cache[key] = value

    def _get(self, cache: OrderedDict[str, T], key: str) -> T | None:
        if key not in cache:
            return None
        cache.move_to_end(key)
        return cache[key]
```

- [ ] **Step 5: Implement JSON serializers**

Create `ate_smt7_diff/mcp/serializers.py`:

```python
#!/usr/bin/env python3
"""JSON serialization helpers for MCP tools."""

from __future__ import annotations

import json
from typing import Any


def json_response(payload: Any) -> str:
    """Return a stable JSON string for MCP tool responses."""
    return json.dumps(payload, indent=2, ensure_ascii=False)


def error_response(message: str) -> str:
    """Return the existing simple MCP input-error shape."""
    return json_response({"error": message})


def exception_response(error: Exception) -> str:
    """Return the existing handled-exception response shape."""
    return json_response({"error_type": type(error).__name__, "message": str(error)})
```

- [ ] **Step 6: Run tests and verify green**

Run:

```bash
uv run pytest tests/mcp/test_cache_serializers.py -v
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add tests/mcp/test_cache_serializers.py ate_smt7_diff/mcp/__init__.py ate_smt7_diff/mcp/cache.py ate_smt7_diff/mcp/serializers.py
git commit -m "feat: add MCP cache and serializers"
```

---

### Task 2: Package Discovery Tools

**Files:**
- Create: `tests/mcp/test_tools_packages.py`
- Create: `ate_smt7_diff/mcp/tools/__init__.py`
- Create: `ate_smt7_diff/mcp/tools/packages.py`

- [ ] **Step 1: Write the failing tests**

```python
#!/usr/bin/env python3
"""Tests for MCP package discovery tools."""

from __future__ import annotations

import asyncio
import json

from mcp.server.fastmcp import FastMCP

from ate_smt7_diff.mcp.tools.packages import (
    list_program_packages,
    register_package_tools,
    suggest_flow_pairs,
)


def test_list_program_packages_reports_packages_with_testflow(tmp_path) -> None:
    pkg = tmp_path / "pkg_a"
    flow_dir = pkg / "testflow"
    flow_dir.mkdir(parents=True)
    (flow_dir / "main.flow").write_text("test_flow\nrun(S1);\nend\n", encoding="utf-8")
    (tmp_path / "not_a_package").mkdir()

    payload = json.loads(list_program_packages(str(tmp_path)))

    assert payload["directory"] == str(tmp_path.resolve())
    assert payload["packages"] == [
        {
            "name": "pkg_a",
            "path": str(pkg.resolve()),
            "flow_files": "[\"main.flow\"]",
        }
    ]


def test_list_program_packages_non_directory_returns_error(tmp_path) -> None:
    missing = tmp_path / "missing"

    payload = json.loads(list_program_packages(str(missing)))

    assert payload == {"error": f"Not a directory: {missing}"}


def test_suggest_flow_pairs_returns_matches_and_unmatched(tmp_path) -> None:
    old_pkg = tmp_path / "old"
    new_pkg = tmp_path / "new"
    old_flow_dir = old_pkg / "testflow"
    new_flow_dir = new_pkg / "testflow"
    old_flow_dir.mkdir(parents=True)
    new_flow_dir.mkdir(parents=True)
    (old_flow_dir / "main.flow").write_text("test_flow\nrun(S1);\nend\n", encoding="utf-8")
    (old_flow_dir / "old_only.flow").write_text("test_flow\nrun(S2);\nend\n", encoding="utf-8")
    (new_flow_dir / "main.flow").write_text("test_flow\nrun(S1);\nend\n", encoding="utf-8")
    (new_flow_dir / "new_only.flow").write_text("test_flow\nrun(S3);\nend\n", encoding="utf-8")

    payload = json.loads(suggest_flow_pairs(str(old_pkg), str(new_pkg)))

    assert payload["old_package"] == str(old_pkg)
    assert payload["new_package"] == str(new_pkg)
    assert payload["matched_pairs"] == [
        {
            "old": str((old_flow_dir / "main.flow").resolve()),
            "new": str((new_flow_dir / "main.flow").resolve()),
        }
    ]
    assert payload["unmatched_old"] == ["old_only.flow"]
    assert payload["unmatched_new"] == ["new_only.flow"]


def test_register_package_tools_adds_expected_tool_names() -> None:
    mcp = FastMCP("test")

    register_package_tools(mcp)

    async def names() -> list[str]:
        return sorted(tool.name for tool in await mcp.list_tools())

    assert asyncio.run(names()) == ["list_program_packages", "suggest_flow_pairs"]
```

- [ ] **Step 2: Run the test and verify it fails**

Run:

```bash
uv run pytest tests/mcp/test_tools_packages.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'ate_smt7_diff.mcp.tools'`.

- [ ] **Step 3: Add the tools package marker**

Create `ate_smt7_diff/mcp/tools/__init__.py`:

```python
#!/usr/bin/env python3
"""MCP tool registration modules."""
```

- [ ] **Step 4: Implement package tools**

Create `ate_smt7_diff/mcp/tools/packages.py`:

```python
#!/usr/bin/env python3
"""MCP tools for SMT7 program package discovery."""

from __future__ import annotations

import json
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from ate_smt7_diff.flow_matcher import FlowMatcher
from ate_smt7_diff.mcp.serializers import error_response, json_response


def list_program_packages(directory: str) -> str:
    """List subdirectories under a path that look like SMT7 program packages."""
    root = Path(directory).expanduser().resolve()
    if not root.is_dir():
        return error_response(f"Not a directory: {directory}")

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

    return json_response({"directory": str(root), "packages": packages})


def suggest_flow_pairs(
    old_package: str, new_package: str, match_config: str | None = None
) -> str:
    """Suggest paired flow files between two program packages."""
    old_dir = Path(old_package).expanduser().resolve() / "testflow"
    new_dir = Path(new_package).expanduser().resolve() / "testflow"

    if not old_dir.is_dir():
        return error_response(f"testflow directory not found: {old_dir}")
    if not new_dir.is_dir():
        return error_response(f"testflow directory not found: {new_dir}")

    matcher = FlowMatcher.from_config(match_config)
    pairs = matcher.match_directories(old_dir, new_dir)

    matched = [{"old": str(old), "new": str(new)} for old, new in pairs]
    old_names = {f.name for f in old_dir.glob("*.flow")}
    new_names = {f.name for f in new_dir.glob("*.flow")}
    matched_old = {old.name for old, _ in pairs}
    matched_new = {new.name for _, new in pairs}

    return json_response(
        {
            "old_package": old_package,
            "new_package": new_package,
            "matched_pairs": matched,
            "unmatched_old": sorted(old_names - matched_old),
            "unmatched_new": sorted(new_names - matched_new),
        }
    )


def register_package_tools(mcp: FastMCP) -> None:
    """Register package discovery tools on a FastMCP server."""
    mcp.tool()(list_program_packages)
    mcp.tool()(suggest_flow_pairs)
```

- [ ] **Step 5: Run tests and verify green**

Run:

```bash
uv run pytest tests/mcp/test_tools_packages.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add tests/mcp/test_tools_packages.py ate_smt7_diff/mcp/tools/__init__.py ate_smt7_diff/mcp/tools/packages.py
git commit -m "feat: extract MCP package tools"
```

---

### Task 3: Flow Diff MCP Tools

**Files:**
- Create: `tests/mcp/test_tools_diff.py`
- Create: `ate_smt7_diff/mcp/tools/diff.py`

- [ ] **Step 1: Write the failing tests**

```python
#!/usr/bin/env python3
"""Tests for MCP flow diff tools."""

from __future__ import annotations

import asyncio
import json

from mcp.server.fastmcp import FastMCP

from ate_smt7_diff.mcp.cache import McpCache
from ate_smt7_diff.mcp.tools.diff import (
    diff_flows,
    export_diff_report,
    query_diff_report,
    register_diff_tools,
)


def _write_flow(path, suites: list[str]) -> None:
    body = "\n".join(f"run({suite});" for suite in suites)
    path.write_text(f"test_flow\n{body}\nend\n", encoding="utf-8")


def test_query_diff_report_cache_miss(tmp_path) -> None:
    cache = McpCache()
    old_flow = tmp_path / "old.flow"
    new_flow = tmp_path / "new.flow"
    _write_flow(old_flow, ["S1"])
    _write_flow(new_flow, ["S1"])

    payload = json.loads(query_diff_report(cache, str(old_flow), str(new_flow)))

    assert payload == {"error": "Report not found in cache. Run diff_flows first."}


def test_diff_flows_caches_single_report_and_query_returns_summary(tmp_path) -> None:
    cache = McpCache()
    old_flow = tmp_path / "old.flow"
    new_flow = tmp_path / "new.flow"
    _write_flow(old_flow, ["S1"])
    _write_flow(new_flow, ["S1", "S2"])

    diff_payload = json.loads(diff_flows(cache, str(old_flow), str(new_flow)))
    query_payload = json.loads(query_diff_report(cache, str(old_flow), str(new_flow)))

    assert diff_payload["added_tests"] == ["S2"]
    assert query_payload["added"] == ["S2"]
    assert query_payload["removed"] == []
    assert query_payload["order_changed"] == []


def test_diff_flows_rejects_non_flow_file(tmp_path) -> None:
    cache = McpCache()
    old_flow = tmp_path / "old.txt"
    new_flow = tmp_path / "new.flow"
    old_flow.write_text("not a flow", encoding="utf-8")
    _write_flow(new_flow, ["S1"])

    payload = json.loads(diff_flows(cache, str(old_flow), str(new_flow)))

    assert payload == {"error": f"Expected .flow file: {old_flow}"}


def test_export_diff_report_supports_markdown_after_diff(tmp_path) -> None:
    cache = McpCache()
    old_flow = tmp_path / "old.flow"
    new_flow = tmp_path / "new.flow"
    _write_flow(old_flow, ["S1"])
    _write_flow(new_flow, ["S1", "S2"])

    diff_flows(cache, str(old_flow), str(new_flow))
    markdown = export_diff_report(cache, str(old_flow), str(new_flow), format="markdown")

    assert "S2" in markdown


def test_register_diff_tools_adds_expected_tool_names() -> None:
    mcp = FastMCP("test")
    cache = McpCache()

    register_diff_tools(mcp, cache)

    async def names() -> list[str]:
        return sorted(tool.name for tool in await mcp.list_tools())

    assert asyncio.run(names()) == [
        "diff_flows",
        "export_diff_report",
        "query_diff_report",
    ]
```

- [ ] **Step 2: Run the test and verify it fails**

Run:

```bash
uv run pytest tests/mcp/test_tools_diff.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'ate_smt7_diff.mcp.tools.diff'`.

- [ ] **Step 3: Implement diff tools**

Create `ate_smt7_diff/mcp/tools/diff.py`:

```python
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


def diff_flows(
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


def _diff_packages(
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
    def diff_flows(
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
```

- [ ] **Step 4: Run tests and verify green**

Run:

```bash
uv run pytest tests/mcp/test_tools_diff.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/mcp/test_tools_diff.py ate_smt7_diff/mcp/tools/diff.py
git commit -m "feat: extract MCP diff tools"
```

---

### Task 4: Agent Helper MCP Tools

**Files:**
- Create: `tests/mcp/test_tools_agent.py`
- Create: `ate_smt7_diff/mcp/tools/agent.py`

- [ ] **Step 1: Write the failing tests**

```python
#!/usr/bin/env python3
"""Tests for MCP agent-helper tools."""

from __future__ import annotations

import asyncio
import json

from mcp.server.fastmcp import FastMCP

from ate_smt7_diff.mcp.cache import McpCache
from ate_smt7_diff.mcp.tools.agent import (
    register_agent_tools,
    smart_diff_discover,
    smart_diff_explain,
    smart_diff_suggest,
    smart_diff_validate,
)


def test_agent_tools_return_cache_miss_before_discovery() -> None:
    cache = McpCache()

    assert json.loads(smart_diff_suggest(cache, "old", "new")) == {
        "error": "Discovery result not found. Run smart_diff_discover first."
    }
    assert json.loads(smart_diff_explain(cache, "old", "new")) == {
        "error": "Discovery result not found. Run smart_diff_discover first."
    }
    assert json.loads(smart_diff_validate(cache, "old", "new")) == {
        "error": "Discovery result not found. Run smart_diff_discover first."
    }


def test_discover_populates_cache_and_follow_up_tools_return_json() -> None:
    cache = McpCache()
    old_package = "Test1/example1"
    new_package = "Test2/example2"

    discover_payload = json.loads(
        smart_diff_discover(cache, old_package, new_package, load_configs=False)
    )
    suggest_payload = json.loads(smart_diff_suggest(cache, old_package, new_package))
    explain_payload = json.loads(smart_diff_explain(cache, old_package, new_package))
    validate_payload = json.loads(smart_diff_validate(cache, old_package, new_package))

    assert discover_payload["old_package"].endswith("Test1/example1")
    assert discover_payload["new_package"].endswith("Test2/example2")
    assert "suggestions" in suggest_payload
    assert "explanations" in explain_payload
    assert "passed" in validate_payload
    assert "findings" in validate_payload


def test_register_agent_tools_adds_expected_tool_names() -> None:
    mcp = FastMCP("test")
    cache = McpCache()

    register_agent_tools(mcp, cache)

    async def names() -> list[str]:
        return sorted(tool.name for tool in await mcp.list_tools())

    assert asyncio.run(names()) == [
        "smart_diff_discover",
        "smart_diff_explain",
        "smart_diff_suggest",
        "smart_diff_validate",
    ]
```

- [ ] **Step 2: Run the test and verify it fails**

Run:

```bash
uv run pytest tests/mcp/test_tools_agent.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'ate_smt7_diff.mcp.tools.agent'`.

- [ ] **Step 3: Implement agent tools**

Create `ate_smt7_diff/mcp/tools/agent.py`:

```python
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


def _get_discovery_result(cache: McpCache, old_package: str, new_package: str) -> DiscoveryResult | None:
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
```

- [ ] **Step 4: Run tests and verify green**

Run:

```bash
uv run pytest tests/mcp/test_tools_agent.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/mcp/test_tools_agent.py ate_smt7_diff/mcp/tools/agent.py
git commit -m "feat: extract MCP agent tools"
```

---

### Task 5: MCP Resources And Server Assembly

**Files:**
- Create: `tests/mcp/test_resources_server.py`
- Create: `ate_smt7_diff/mcp/resources.py`
- Create: `ate_smt7_diff/mcp/server.py`
- Modify: `ate_smt7_diff/mcp/__init__.py`

- [ ] **Step 1: Write the failing tests**

```python
#!/usr/bin/env python3
"""Tests for MCP resources and server assembly."""

from __future__ import annotations

import asyncio
import json

from ate_smt7_diff.mcp.resources import clients, examples, manifest, usage
from ate_smt7_diff.mcp.server import create_server


def test_manifest_resource_has_tool_groups_and_stdio_transport() -> None:
    payload = json.loads(manifest())

    assert payload["name"] == "ate-smt7-diff"
    assert payload["transport"] == "stdio"
    assert "diff" in payload["tool_groups"]
    assert "diff_flows" in payload["tool_groups"]["diff"]
    assert "ate-smt7-diff://usage" in payload["resources"]


def test_usage_resource_mentions_core_workflows() -> None:
    text = usage()

    assert "diff_flows" in text
    assert "smart_diff_discover" in text
    assert ".flow" in text


def test_clients_resource_mentions_requested_clients() -> None:
    text = clients()

    for name in [
        "Codex CLI",
        "Claude Code",
        "Cursor",
        "Gemini CLI",
        "OpenCode",
        "GitHub Copilot CLI",
    ]:
        assert name in text


def test_examples_resource_mentions_cached_report_workflow() -> None:
    text = examples()

    assert "query_diff_report" in text
    assert "export_diff_report" in text


def test_create_server_registers_all_tools_and_resources() -> None:
    server = create_server()

    async def names() -> tuple[list[str], list[str]]:
        tool_names = sorted(tool.name for tool in await server.list_tools())
        resource_uris = sorted(str(resource.uri) for resource in await server.list_resources())
        return tool_names, resource_uris

    tool_names, resource_uris = asyncio.run(names())

    assert tool_names == [
        "diff_flows",
        "export_diff_report",
        "list_program_packages",
        "query_diff_report",
        "smart_diff_discover",
        "smart_diff_explain",
        "smart_diff_suggest",
        "smart_diff_validate",
        "suggest_flow_pairs",
    ]
    assert resource_uris == [
        "ate-smt7-diff://clients",
        "ate-smt7-diff://examples",
        "ate-smt7-diff://manifest",
        "ate-smt7-diff://usage",
    ]
```

- [ ] **Step 2: Run the test and verify it fails**

Run:

```bash
uv run pytest tests/mcp/test_resources_server.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'ate_smt7_diff.mcp.resources'`.

- [ ] **Step 3: Implement resources**

Create `ate_smt7_diff/mcp/resources.py`:

```python
#!/usr/bin/env python3
"""Agent-readable MCP resources for ate-smt7-diff."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

from mcp.server.fastmcp import FastMCP

from ate_smt7_diff.mcp.serializers import json_response

RESOURCE_URIS = [
    "ate-smt7-diff://manifest",
    "ate-smt7-diff://usage",
    "ate-smt7-diff://clients",
    "ate-smt7-diff://examples",
]


def _package_version() -> str:
    try:
        return version("ate-smt7-diff")
    except PackageNotFoundError:
        return "unknown"


def manifest() -> str:
    """Return the machine-readable MCP capability manifest."""
    return json_response(
        {
            "name": "ate-smt7-diff",
            "version": _package_version(),
            "transport": "stdio",
            "client_category": "local MCP clients",
            "tool_groups": {
                "package": ["list_program_packages", "suggest_flow_pairs"],
                "diff": ["diff_flows", "query_diff_report", "export_diff_report"],
                "agent": [
                    "smart_diff_discover",
                    "smart_diff_suggest",
                    "smart_diff_explain",
                    "smart_diff_validate",
                ],
            },
            "resources": RESOURCE_URIS,
            "recommended_workflows": [
                ["list_program_packages", "suggest_flow_pairs", "diff_flows"],
                [
                    "smart_diff_discover",
                    "smart_diff_suggest",
                    "smart_diff_explain",
                    "smart_diff_validate",
                ],
                ["diff_flows", "query_diff_report", "export_diff_report"],
            ],
        }
    )


def usage() -> str:
    """Return concise Markdown usage guidance for MCP agents."""
    return """# ate-smt7-diff MCP Usage

This local stdio MCP server compares Advantest 93K SMT7 test program flows and related configuration files.

## Single Flow Diff

Use `diff_flows(old_path, new_path)` with two `.flow` files.

## Program Package Diff

Use `diff_flows(old_path, new_path)` with two package directories that contain `testflow/`.

## Smart Review Workflow

Run `smart_diff_discover(old_package, new_package)` first, then call `smart_diff_suggest`, `smart_diff_explain`, and `smart_diff_validate` with the same package strings.

## Cached Report Workflow

Run `diff_flows` first, then call `query_diff_report` or `export_diff_report` with the same paths.
"""


def clients() -> str:
    """Return local client setup summary."""
    return """# Local MCP Client Setup

Use this server as a local stdio MCP command.

Recommended command from the repository:

```bash
python /Users/walter_luo/Project/skills/ate_skill/ate-smt7-diff/mcp_server.py
```

Recommended command after editable install:

```bash
python -m ate_smt7_diff.mcp.server
```

Requested clients covered by `docs/mcp/clients.md`:

- Codex CLI
- Claude Code
- Cursor
- Gemini CLI
- OpenCode
- GitHub Copilot CLI
"""


def examples() -> str:
    """Return common MCP tool call examples."""
    return """# MCP Tool Examples

## Single Flow Diff

`diff_flows("/path/old/testflow/main.flow", "/path/new/testflow/main.flow")`

## Package Diff

`diff_flows("/path/old_pkg", "/path/new_pkg", load_configs=true)`

## Cached Report Query

`query_diff_report("/path/old_pkg", "/path/new_pkg")`

## Markdown Export

`export_diff_report("/path/old_pkg", "/path/new_pkg", format="markdown")`

## Smart Workflow

1. `smart_diff_discover("/path/old_pkg", "/path/new_pkg")`
2. `smart_diff_suggest("/path/old_pkg", "/path/new_pkg")`
3. `smart_diff_explain("/path/old_pkg", "/path/new_pkg")`
4. `smart_diff_validate("/path/old_pkg", "/path/new_pkg")`
"""


def register_resources(mcp: FastMCP) -> None:
    """Register MCP resources on a FastMCP server."""
    mcp.resource("ate-smt7-diff://manifest", mime_type="application/json")(manifest)
    mcp.resource("ate-smt7-diff://usage", mime_type="text/markdown")(usage)
    mcp.resource("ate-smt7-diff://clients", mime_type="text/markdown")(clients)
    mcp.resource("ate-smt7-diff://examples", mime_type="text/markdown")(examples)
```

- [ ] **Step 4: Implement server assembly**

Create `ate_smt7_diff/mcp/server.py`:

```python
#!/usr/bin/env python3
"""FastMCP server assembly for ate-smt7-diff."""

from __future__ import annotations

import logging

from mcp.server.fastmcp import FastMCP

from ate_smt7_diff.mcp.cache import McpCache
from ate_smt7_diff.mcp.resources import register_resources
from ate_smt7_diff.mcp.tools.agent import register_agent_tools
from ate_smt7_diff.mcp.tools.diff import register_diff_tools
from ate_smt7_diff.mcp.tools.packages import register_package_tools

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def create_server(cache: McpCache | None = None) -> FastMCP:
    """Create and configure the ate-smt7-diff MCP server."""
    state = cache or McpCache()
    mcp = FastMCP("ate-smt7-diff")
    register_package_tools(mcp)
    register_diff_tools(mcp, state)
    register_agent_tools(mcp, state)
    register_resources(mcp)
    return mcp


def run_stdio() -> None:
    """Run the MCP server using the local stdio transport."""
    create_server().run(transport="stdio")


if __name__ == "__main__":
    run_stdio()
```

Replace `ate_smt7_diff/mcp/__init__.py` with:

```python
#!/usr/bin/env python3
"""MCP integration package for ate-smt7-diff."""

from ate_smt7_diff.mcp.cache import McpCache, cache_key
from ate_smt7_diff.mcp.server import create_server, run_stdio

__all__ = ["McpCache", "cache_key", "create_server", "run_stdio"]
```

- [ ] **Step 5: Run tests and verify green**

Run:

```bash
uv run pytest tests/mcp/test_resources_server.py -v
```

Expected: PASS.

- [ ] **Step 6: Run all MCP tests created so far**

Run:

```bash
uv run pytest tests/mcp -v
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add tests/mcp/test_resources_server.py ate_smt7_diff/mcp/resources.py ate_smt7_diff/mcp/server.py ate_smt7_diff/mcp/__init__.py
git commit -m "feat: assemble modular MCP server"
```

---

### Task 6: Compatibility Wrapper

**Files:**
- Create: `tests/mcp/test_entrypoints.py`
- Modify: `mcp_server.py`

- [ ] **Step 1: Write the failing test**

```python
#!/usr/bin/env python3
"""Tests for MCP compatibility entry points."""

from __future__ import annotations

import ast
from pathlib import Path


def test_root_mcp_server_is_thin_compatibility_wrapper() -> None:
    source = Path("mcp_server.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    function_defs = [node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]

    assert function_defs == []
    assert "from ate_smt7_diff.mcp.server import run_stdio" in source
    assert "run_stdio()" in source
```

- [ ] **Step 2: Run the test and verify it fails**

Run:

```bash
uv run pytest tests/mcp/test_entrypoints.py -v
```

Expected: FAIL because the current `mcp_server.py` still defines tool functions.

- [ ] **Step 3: Replace the root wrapper**

Replace `mcp_server.py` with:

```python
#!/usr/bin/env python3
"""Compatibility wrapper for the modular ate-smt7-diff MCP server."""

from __future__ import annotations

from ate_smt7_diff.mcp.server import run_stdio


if __name__ == "__main__":
    run_stdio()
```

- [ ] **Step 4: Run the entrypoint test**

Run:

```bash
uv run pytest tests/mcp/test_entrypoints.py -v
```

Expected: PASS.

- [ ] **Step 5: Verify the module entry point can be imported**

Run:

```bash
uv run python -c "from ate_smt7_diff.mcp.server import create_server; print(create_server().name)"
```

Expected output includes:

```text
ate-smt7-diff
```

- [ ] **Step 6: Commit**

```bash
git add tests/mcp/test_entrypoints.py mcp_server.py
git commit -m "refactor: make MCP root entrypoint a wrapper"
```

---

### Task 7: Local MCP Documentation

**Files:**
- Create: `docs/mcp/README.md`
- Create: `docs/mcp/clients.md`

- [ ] **Step 1: Write documentation checks**

Create `tests/mcp/test_docs.py`:

```python
#!/usr/bin/env python3
"""Tests for local MCP documentation."""

from __future__ import annotations

from pathlib import Path


def test_mcp_readme_mentions_local_stdio_and_commands() -> None:
    text = Path("docs/mcp/README.md").read_text(encoding="utf-8")

    assert "local stdio" in text
    assert "python mcp_server.py" in text
    assert "python -m ate_smt7_diff.mcp.server" in text
    assert "remote MCP" in text


def test_clients_doc_mentions_requested_clients() -> None:
    text = Path("docs/mcp/clients.md").read_text(encoding="utf-8")

    for client in [
        "Codex CLI",
        "Claude Code",
        "Cursor",
        "Gemini CLI",
        "OpenCode",
        "GitHub Copilot CLI",
    ]:
        assert client in text

    assert '"command": "python"' in text
    assert '"args"' in text
```

- [ ] **Step 2: Run the test and verify it fails**

Run:

```bash
uv run pytest tests/mcp/test_docs.py -v
```

Expected: FAIL with `FileNotFoundError` for `docs/mcp/README.md`.

- [ ] **Step 3: Create the MCP README**

Create `docs/mcp/README.md`:

```markdown
# ate-smt7-diff Local MCP

`ate-smt7-diff` exposes its SMT7 diff capabilities through a local stdio MCP server.

The server is intended for local agent clients that can launch a command and communicate over stdin/stdout.

## Launch Commands

From the repository root:

```bash
python mcp_server.py
```

After editable install:

```bash
python -m ate_smt7_diff.mcp.server
```

## Capabilities

- List SMT7 program packages.
- Suggest matched `.flow` file pairs.
- Diff single `.flow` files.
- Diff full program packages.
- Query and export cached diff reports.
- Run smart discovery, suggestion, explanation, and validation workflows.

## Resources

- `ate-smt7-diff://manifest`
- `ate-smt7-diff://usage`
- `ate-smt7-diff://clients`
- `ate-smt7-diff://examples`

## Transport Scope

This integration supports local stdio MCP. It does not provide remote MCP over HTTP, SSE, or streamable HTTP.
```

- [ ] **Step 4: Create client setup notes**

Create `docs/mcp/clients.md`:

```markdown
# Local MCP Client Configuration

Use the same local stdio command for each MCP client:

```json
{
  "command": "python",
  "args": [
    "/Users/walter_luo/Project/skills/ate_skill/ate-smt7-diff/mcp_server.py"
  ]
}
```

After installing the package in editable mode, this command is also available:

```json
{
  "command": "python",
  "args": ["-m", "ate_smt7_diff.mcp.server"]
}
```

Client MCP schemas can vary by version. Use the command and args above inside the client's MCP server configuration block.

## Codex CLI

Configure a local stdio MCP server named `ate-smt7-diff` using the shared command and args.

## Claude Code

Configure a local stdio MCP server named `ate-smt7-diff` using the shared command and args.

## Cursor

Configure a local stdio MCP server named `ate-smt7-diff` using the shared command and args in Cursor's MCP settings.

## Gemini CLI

Configure a local stdio MCP server named `ate-smt7-diff` using the shared command and args.

## OpenCode

Configure a local stdio MCP server named `ate-smt7-diff` using the shared command and args.

## GitHub Copilot CLI

Configure a local stdio MCP server named `ate-smt7-diff` using the shared command and args when the CLI environment supports MCP stdio servers.
```

- [ ] **Step 5: Run documentation tests**

Run:

```bash
uv run pytest tests/mcp/test_docs.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add tests/mcp/test_docs.py docs/mcp/README.md docs/mcp/clients.md
git commit -m "docs: add local MCP client setup"
```

---

### Task 8: Integration Verification

**Files:**
- Modify only files required to fix verification failures from earlier tasks.

- [ ] **Step 1: Run all MCP tests**

Run:

```bash
uv run pytest tests/mcp -v
```

Expected: PASS.

- [ ] **Step 2: Run existing agent tests**

Run:

```bash
uv run pytest tests/agent -v
```

Expected: PASS.

- [ ] **Step 3: Run the full test suite**

Run:

```bash
uv run pytest -v
```

Expected: PASS.

- [ ] **Step 4: Run lint on touched source files**

Run:

```bash
uv run ruff check ate_smt7_diff/mcp mcp_server.py tests/mcp
```

Expected: PASS.

- [ ] **Step 5: Run formatting check on touched source files**

Run:

```bash
uv run ruff format --check ate_smt7_diff/mcp mcp_server.py tests/mcp
```

Expected: PASS.

- [ ] **Step 6: Verify the MCP server object exposes expected tools**

Run:

```bash
uv run python -c "import asyncio; from ate_smt7_diff.mcp.server import create_server; server=create_server(); print(sorted(tool.name for tool in asyncio.run(server.list_tools())))"
```

Expected output includes:

```text
diff_flows
list_program_packages
smart_diff_discover
suggest_flow_pairs
```

- [ ] **Step 7: Verify the MCP server object exposes expected resources**

Run:

```bash
uv run python -c "import asyncio; from ate_smt7_diff.mcp.server import create_server; server=create_server(); print(sorted(str(resource.uri) for resource in asyncio.run(server.list_resources())))"
```

Expected output includes:

```text
ate-smt7-diff://clients
ate-smt7-diff://examples
ate-smt7-diff://manifest
ate-smt7-diff://usage
```

- [ ] **Step 8: Commit verification fixes if any were needed**

If verification required source changes, commit them:

```bash
git add ate_smt7_diff/mcp mcp_server.py tests/mcp docs/mcp
git commit -m "fix: stabilize modular MCP verification"
```

If no changes were needed after Task 7, do not create an empty commit.

---

## Self-Review Checklist

- Every spec requirement maps to at least one task.
- The root `mcp_server.py` compatibility entry point remains available.
- `python -m ate_smt7_diff.mcp.server` is added.
- Existing MCP tool names are preserved.
- Resources cover manifest, usage, clients, and examples.
- Requested clients are named in docs and resource content.
- Tests cover cache, serializers, tools, resources, server assembly, wrapper, and docs.
- Verification commands include MCP tests, agent tests, full tests, lint, format, and server object inspection.
