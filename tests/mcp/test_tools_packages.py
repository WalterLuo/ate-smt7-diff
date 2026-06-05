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
            "flow_files": '["main.flow"]',
        }
    ]


def test_list_program_packages_non_directory_returns_error(tmp_path) -> None:
    missing = tmp_path / "missing"

    payload = json.loads(list_program_packages(str(missing)))

    assert payload == {"error": f"Not a directory: {missing}"}


def test_suggest_flow_pairs_returns_matches_and_unmatched_old(tmp_path) -> None:
    old_pkg = tmp_path / "old"
    new_pkg = tmp_path / "new"
    old_flow_dir = old_pkg / "testflow"
    new_flow_dir = new_pkg / "testflow"
    old_flow_dir.mkdir(parents=True)
    new_flow_dir.mkdir(parents=True)
    (old_flow_dir / "main.flow").write_text("test_flow\nrun(S1);\nend\n", encoding="utf-8")
    (old_flow_dir / "old_only.flow").write_text("test_flow\nrun(S2);\nend\n", encoding="utf-8")
    (new_flow_dir / "main.flow").write_text("test_flow\nrun(S1);\nend\n", encoding="utf-8")

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
    assert payload["unmatched_new"] == []


def test_register_package_tools_adds_expected_tool_names() -> None:
    mcp = FastMCP("test")

    register_package_tools(mcp)

    async def names() -> list[str]:
        return sorted(tool.name for tool in await mcp.list_tools())

    assert asyncio.run(names()) == ["list_program_packages", "suggest_flow_pairs"]
