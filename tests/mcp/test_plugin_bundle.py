from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_codex_plugin_manifest_points_at_skill_and_mcp_files() -> None:
    manifest_path = ROOT / ".codex-plugin" / "plugin.json"

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert manifest["name"] == "ate-smt7-diff"
    assert manifest["skills"] == "./skills/"
    assert manifest["mcpServers"] == "./.mcp.json"
    assert manifest["interface"]["displayName"] == "ATE SMT7 Diff"
    assert manifest["interface"]["category"] == "Developer Tools"


def test_plugin_mcp_uses_repo_local_launcher() -> None:
    mcp_path = ROOT / ".mcp.json"

    config = json.loads(mcp_path.read_text(encoding="utf-8"))
    server = config["mcpServers"]["ate-smt7-diff"]

    assert server["command"] == "python3"
    assert server["cwd"] == "."
    assert server["args"] == ["./scripts/ate-smt7-diff-mcp-launcher", "--repo", "."]


def test_plugin_skill_frontmatter_and_workflow() -> None:
    skill_path = ROOT / "skills" / "ate-smt7-diff" / "SKILL.md"

    content = skill_path.read_text(encoding="utf-8")

    assert "name: ate-smt7-diff" in content
    assert "smart_diff_discover" in content
    assert "diff_flows" in content
    assert "query_diff_report" in content
    assert "export_diff_report" in content
