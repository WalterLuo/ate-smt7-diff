from __future__ import annotations

import json
import sys

from ate_smt7_diff.mcp.runtime import (
    RuntimeConfig,
    default_runtime_home,
    ensure_runtime,
    launcher_command,
    private_venv_python,
    server_command,
)


def test_default_runtime_home_prefers_environment(tmp_path, monkeypatch) -> None:
    custom_home = tmp_path / "custom-mcp-home"
    monkeypatch.setenv("ATE_SMT7_DIFF_MCP_HOME", str(custom_home))

    assert default_runtime_home() == custom_home


def test_launcher_command_points_at_repo_script(tmp_path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()

    command = launcher_command(repo, python="python3")

    assert command == [
        "python3",
        str(repo / "scripts" / "ate-smt7-diff-mcp-launcher"),
        "--repo",
        str(repo),
    ]


def test_server_command_runs_module_with_private_python(tmp_path) -> None:
    python = tmp_path / ".venv" / "bin" / "python"

    assert server_command(python) == [
        str(python),
        "-m",
        "ate_smt7_diff.mcp.server",
    ]


def test_private_venv_python_uses_cache_home(tmp_path) -> None:
    home = tmp_path / "runtime"

    assert private_venv_python(home) == home / ".venv" / "bin" / "python"


def test_ensure_runtime_creates_venv_and_uses_uv_when_available(tmp_path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "pyproject.toml").write_text('[project]\nname = "demo"\n', encoding="utf-8")
    home = tmp_path / "home"
    calls: list[list[str]] = []

    def runner(command: list[str]) -> None:
        calls.append(command)

    def which(command: str) -> str | None:
        if command == "uv":
            return "/opt/bin/uv"
        return None

    python = ensure_runtime(RuntimeConfig(repo=repo, home=home), runner=runner, which=which)

    assert python == private_venv_python(home)
    assert calls == [
        [sys.executable, "-m", "venv", str(home / ".venv")],
        ["/opt/bin/uv", "pip", "install", "--python", str(python), "-e", str(repo)],
    ]
    stamp = json.loads((home / "install-stamp.json").read_text(encoding="utf-8"))
    assert stamp["repo"] == str(repo)
    assert stamp["fingerprint"]


def test_ensure_runtime_skips_install_when_stamp_matches(tmp_path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "pyproject.toml").write_text('[project]\nname = "demo"\n', encoding="utf-8")
    home = tmp_path / "home"
    calls: list[list[str]] = []

    ensure_runtime(RuntimeConfig(repo=repo, home=home), runner=calls.append, which=lambda _: None)
    python = private_venv_python(home)
    python.parent.mkdir(parents=True, exist_ok=True)
    python.touch()
    calls.clear()

    ensure_runtime(RuntimeConfig(repo=repo, home=home), runner=calls.append, which=lambda _: None)

    assert calls == []
