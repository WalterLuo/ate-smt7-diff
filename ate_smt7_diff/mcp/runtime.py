#!/usr/bin/env python3
"""Self-healing runtime launcher for the local ate-smt7-diff MCP server."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

SERVER_MODULE = "ate_smt7_diff.mcp.server"
ENV_HOME = "ATE_SMT7_DIFF_MCP_HOME"
LAUNCHER_SCRIPT = "ate-smt7-diff-mcp-launcher"
STAMP_FILE = "install-stamp.json"

Runner = Callable[[list[str]], None]
Which = Callable[[str], str | None]


@dataclass(frozen=True)
class RuntimeConfig:
    """Configuration for the private MCP runtime."""

    repo: Path
    home: Path

    @classmethod
    def from_repo(
        cls,
        repo: Path,
        *,
        env: Mapping[str, str] | None = None,
    ) -> RuntimeConfig:
        return cls(repo=repo.resolve(), home=default_runtime_home(env=env))


def default_runtime_home(env: Mapping[str, str] | None = None) -> Path:
    """Return the cache directory used for the private MCP runtime."""
    source = env if env is not None else os.environ
    configured = source.get(ENV_HOME)
    if configured:
        return Path(configured).expanduser()
    return Path.home() / ".cache" / "ate-smt7-diff-mcp"


def private_venv_python(home: Path) -> Path:
    """Return the private virtualenv Python path for this platform."""
    scripts_dir = "Scripts" if os.name == "nt" else "bin"
    executable = "python.exe" if os.name == "nt" else "python"
    return home / ".venv" / scripts_dir / executable


def launcher_command(repo: Path, *, python: str = "python3") -> list[str]:
    """Return a stable command that clients can use to start the MCP launcher."""
    resolved_repo = repo.resolve()
    return [
        python,
        str(resolved_repo / "scripts" / LAUNCHER_SCRIPT),
        "--repo",
        str(resolved_repo),
    ]


def server_command(python: Path | str) -> list[str]:
    """Return the command that runs the MCP server from an installed environment."""
    return [str(python), "-m", SERVER_MODULE]


def runtime_fingerprint(repo: Path) -> str:
    """Hash files that affect installation and entrypoint behavior."""
    digest = hashlib.sha256()
    candidates = [repo / "pyproject.toml"]
    mcp_dir = repo / "ate_smt7_diff" / "mcp"
    if mcp_dir.exists():
        candidates.extend(sorted(mcp_dir.rglob("*.py")))

    for path in candidates:
        if not path.exists() or not path.is_file():
            continue
        digest.update(str(path.relative_to(repo)).encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def ensure_runtime(
    config: RuntimeConfig,
    *,
    runner: Runner | None = None,
    which: Which | None = None,
) -> Path:
    """Create or repair the private runtime, returning its Python executable."""
    run = runner or _subprocess_runner
    resolve_command = which or shutil.which
    repo = config.repo.resolve()
    home = config.home.expanduser().resolve()
    venv_dir = home / ".venv"
    python = private_venv_python(home)
    stamp_path = home / STAMP_FILE
    fingerprint = runtime_fingerprint(repo)

    home.mkdir(parents=True, exist_ok=True)
    if not python.exists():
        run([sys.executable, "-m", "venv", str(venv_dir)])

    expected_stamp = {"repo": str(repo), "fingerprint": fingerprint}
    if _read_stamp(stamp_path) == expected_stamp:
        return python

    uv = resolve_command("uv")
    if uv:
        run([uv, "pip", "install", "--python", str(python), "-e", str(repo)])
    else:
        run([str(python), "-m", "pip", "install", "-e", str(repo)])

    stamp_path.write_text(
        json.dumps(expected_stamp, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return python


def run_launcher(argv: Sequence[str] | None = None) -> None:
    """Ensure the private runtime and replace this process with the MCP server."""
    args = _parser().parse_args(argv)
    config = RuntimeConfig.from_repo(Path(args.repo))
    python = ensure_runtime(config)
    command = server_command(python)
    os.execv(command[0], command)


def main(argv: Sequence[str] | None = None) -> None:
    """Console entrypoint for the runtime launcher."""
    run_launcher(argv)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run ate-smt7-diff MCP in a private runtime")
    parser.add_argument(
        "--repo",
        required=True,
        help="Path to the ate-smt7-diff source checkout to install into the private runtime.",
    )
    return parser


def _read_stamp(path: Path) -> dict[str, str] | None:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    repo = data.get("repo")
    fingerprint = data.get("fingerprint")
    if not isinstance(repo, str) or not isinstance(fingerprint, str):
        return None
    return {"repo": repo, "fingerprint": fingerprint}


def _subprocess_runner(command: list[str]) -> None:
    subprocess.run(command, check=True)


if __name__ == "__main__":
    main()
