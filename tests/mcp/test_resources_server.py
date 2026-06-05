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
