from __future__ import annotations

import json

from ate_smt7_diff.mcp.install import (
    SERVER_NAME,
    client_config_path,
    install_clients,
    normalize_clients,
    planned_cli_command,
)


def test_normalize_clients_expands_all() -> None:
    clients = normalize_clients("codex,claude,cursor,gemini,opencode,copilot")

    assert clients == ["codex", "claude", "cursor", "gemini", "opencode", "copilot"]


def test_normalize_clients_accepts_all_alias() -> None:
    clients = normalize_clients("all")

    assert clients == ["codex", "claude", "cursor", "gemini", "opencode", "copilot"]


def test_planned_codex_cli_command(tmp_path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()

    command = planned_cli_command("codex", repo, python="python3")

    assert command == [
        "codex",
        "mcp",
        "add",
        SERVER_NAME,
        "--",
        "python3",
        str(repo / "scripts" / "ate-smt7-diff-mcp-launcher"),
        "--repo",
        str(repo),
    ]


def test_planned_claude_cli_command_uses_user_scope(tmp_path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()

    command = planned_cli_command("claude", repo, python="python3")

    assert command[:8] == [
        "claude",
        "mcp",
        "add",
        "--transport",
        "stdio",
        "--scope",
        "user",
        SERVER_NAME,
    ]
    assert command[8:] == [
        "--",
        "python3",
        str(repo / "scripts" / "ate-smt7-diff-mcp-launcher"),
        "--repo",
        str(repo),
    ]


def test_cursor_config_merge_preserves_existing_servers(tmp_path) -> None:
    home = tmp_path / "home"
    repo = tmp_path / "repo"
    repo.mkdir()
    path = client_config_path("cursor", home)
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps({"mcpServers": {"other": {"command": "node", "args": ["server.js"]}}}),
        encoding="utf-8",
    )

    results = install_clients(["cursor"], repo=repo, home=home, dry_run=False)

    assert results[0].changed is True
    data = json.loads(path.read_text(encoding="utf-8"))
    assert sorted(data["mcpServers"]) == [SERVER_NAME, "other"]
    assert data["mcpServers"][SERVER_NAME]["command"] == "python3"
    assert data["mcpServers"][SERVER_NAME]["args"] == [
        str(repo / "scripts" / "ate-smt7-diff-mcp-launcher"),
        "--repo",
        str(repo),
    ]


def test_existing_config_skips_without_force(tmp_path) -> None:
    home = tmp_path / "home"
    repo = tmp_path / "repo"
    repo.mkdir()
    path = client_config_path("cursor", home)
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps({"mcpServers": {SERVER_NAME: {"command": "old", "args": []}}}),
        encoding="utf-8",
    )

    results = install_clients(["cursor"], repo=repo, home=home, dry_run=False, force=False)

    assert results[0].changed is False
    assert results[0].skipped_reason == "existing server config; pass --force to replace"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["mcpServers"][SERVER_NAME]["command"] == "old"


def test_force_replaces_existing_config(tmp_path) -> None:
    home = tmp_path / "home"
    repo = tmp_path / "repo"
    repo.mkdir()
    path = client_config_path("cursor", home)
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps({"mcpServers": {SERVER_NAME: {"command": "old", "args": []}}}),
        encoding="utf-8",
    )

    results = install_clients(["cursor"], repo=repo, home=home, dry_run=False, force=True)

    assert results[0].changed is True
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["mcpServers"][SERVER_NAME]["command"] == "python3"


def test_gemini_falls_back_to_settings_json_when_cli_missing(tmp_path) -> None:
    home = tmp_path / "home"
    repo = tmp_path / "repo"
    repo.mkdir()

    results = install_clients(
        ["gemini"],
        repo=repo,
        home=home,
        dry_run=False,
        which=lambda _: None,
    )

    assert results[0].client == "gemini"
    assert results[0].path == home / ".gemini" / "settings.json"
    data = json.loads(results[0].path.read_text(encoding="utf-8"))
    assert data["mcpServers"][SERVER_NAME]["command"] == "python3"


def test_gemini_uses_cli_when_available(tmp_path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    calls: list[list[str]] = []

    results = install_clients(
        ["gemini"],
        repo=repo,
        dry_run=False,
        runner=calls.append,
        which=lambda command: f"/bin/{command}" if command == "gemini" else None,
    )

    assert results[0].kind == "cli"
    assert calls == [planned_cli_command("gemini", repo)]


def test_opencode_config_shape(tmp_path) -> None:
    home = tmp_path / "home"
    repo = tmp_path / "repo"
    repo.mkdir()

    results = install_clients(["opencode"], repo=repo, home=home, dry_run=False)

    data = json.loads(results[0].path.read_text(encoding="utf-8"))
    assert data["$schema"] == "https://opencode.ai/config.json"
    assert data["mcp"][SERVER_NAME]["type"] == "local"
    assert data["mcp"][SERVER_NAME]["enabled"] is True
    assert data["mcp"][SERVER_NAME]["command"][0] == "python3"


def test_copilot_config_shape(tmp_path) -> None:
    home = tmp_path / "home"
    repo = tmp_path / "repo"
    repo.mkdir()

    results = install_clients(["copilot"], repo=repo, home=home, dry_run=False)

    data = json.loads(results[0].path.read_text(encoding="utf-8"))
    assert data["mcpServers"][SERVER_NAME]["type"] == "local"
    assert data["mcpServers"][SERVER_NAME]["tools"] == ["*"]


def test_dry_run_does_not_write_config(tmp_path) -> None:
    home = tmp_path / "home"
    repo = tmp_path / "repo"
    repo.mkdir()

    results = install_clients(["cursor"], repo=repo, home=home, dry_run=True)

    assert results[0].changed is True
    assert results[0].path == home / ".cursor" / "mcp.json"
    assert not results[0].path.exists()
