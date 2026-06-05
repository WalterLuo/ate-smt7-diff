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
