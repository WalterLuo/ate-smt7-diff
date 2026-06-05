#!/usr/bin/env python3
"""Tests for local MCP documentation."""

from __future__ import annotations

from pathlib import Path


def test_mcp_readme_mentions_local_stdio_and_commands() -> None:
    text = Path("docs/mcp/README.md").read_text(encoding="utf-8")

    assert "local stdio" in text
    assert "python mcp_server.py" in text
    assert "python -m ate_smt7_diff.mcp.server" in text
    assert "ate-smt7-diff-mcp-install" in text
    assert ".codex-plugin/plugin.json" in text
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

    assert '"command": "python3"' in text
    assert '"args"' in text
    assert "ate-smt7-diff-mcp-install --clients all" in text
    assert "~/.cursor/mcp.json" in text
    assert "~/.copilot/mcp-config.json" in text
