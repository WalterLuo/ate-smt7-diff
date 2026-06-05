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
