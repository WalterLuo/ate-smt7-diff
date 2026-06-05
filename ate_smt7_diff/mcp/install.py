#!/usr/bin/env python3
"""Install the ate-smt7-diff MCP launcher into local MCP clients."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from ate_smt7_diff.mcp.runtime import launcher_command

SERVER_NAME = "ate-smt7-diff"
SUPPORTED_CLIENTS = ("codex", "claude", "cursor", "gemini", "opencode", "copilot")
CLI_CLIENTS = frozenset({"codex", "claude", "gemini"})

Runner = Callable[[list[str]], None]
Which = Callable[[str], str | None]


@dataclass(frozen=True)
class InstallResult:
    """Outcome for a single client installation attempt."""

    client: str
    kind: str
    changed: bool
    path: Path | None = None
    command: list[str] | None = None
    skipped_reason: str | None = None


def normalize_clients(value: str) -> list[str]:
    """Parse a comma-separated client list."""
    requested = [part.strip().lower() for part in value.split(",") if part.strip()]
    if requested == ["all"]:
        return list(SUPPORTED_CLIENTS)
    unknown = sorted(set(requested) - set(SUPPORTED_CLIENTS))
    if unknown:
        joined = ", ".join(unknown)
        raise ValueError(f"Unsupported client(s): {joined}")
    return requested


def planned_cli_command(client: str, repo: Path, *, python: str = "python3") -> list[str]:
    """Return the CLI command used to register a command-capable MCP client."""
    launch = launcher_command(repo, python=python)
    if client == "codex":
        return ["codex", "mcp", "add", SERVER_NAME, "--", *launch]
    if client == "claude":
        return [
            "claude",
            "mcp",
            "add",
            "--transport",
            "stdio",
            "--scope",
            "user",
            SERVER_NAME,
            "--",
            *launch,
        ]
    if client == "gemini":
        return ["gemini", "mcp", "add", SERVER_NAME, *launch]
    raise ValueError(f"Client does not support CLI planning: {client}")


def client_config_path(client: str, home: Path | None = None) -> Path:
    """Return the documented global config file path for a JSON-configured client."""
    root = (home or Path.home()).expanduser()
    if client == "cursor":
        return root / ".cursor" / "mcp.json"
    if client == "gemini":
        return root / ".gemini" / "settings.json"
    if client == "opencode":
        return root / ".config" / "opencode" / "opencode.json"
    if client == "copilot":
        return root / ".copilot" / "mcp-config.json"
    raise ValueError(f"Client does not have a JSON config path: {client}")


def install_clients(  # noqa: PLR0913
    clients: Sequence[str],
    *,
    repo: Path,
    home: Path | None = None,
    dry_run: bool = False,
    force: bool = False,
    python: str = "python3",
    runner: Runner | None = None,
    which: Which | None = None,
) -> list[InstallResult]:
    """Install MCP launcher configuration for the requested clients."""
    run = runner or _subprocess_runner
    resolve_command = which or shutil.which
    results: list[InstallResult] = []
    resolved_repo = repo.resolve()

    for client in clients:
        if client in CLI_CLIENTS and resolve_command(client):
            command = planned_cli_command(client, resolved_repo, python=python)
            if not dry_run:
                run(command)
            results.append(InstallResult(client=client, kind="cli", changed=True, command=command))
            continue

        if client in {"cursor", "gemini", "opencode", "copilot"}:
            results.append(
                _install_json_client(
                    client,
                    repo=resolved_repo,
                    home=home,
                    dry_run=dry_run,
                    force=force,
                    python=python,
                )
            )
            continue

        results.append(
            InstallResult(
                client=client,
                kind="skip",
                changed=False,
                skipped_reason="client command not found and no JSON fallback is defined",
            )
        )

    return results


def doctor(repo: Path, *, python: str = "python3") -> list[str]:
    """Return human-readable diagnostics for the launcher setup."""
    resolved_repo = repo.resolve()
    script = resolved_repo / "scripts" / "ate-smt7-diff-mcp-launcher"
    messages = [f"repo: {resolved_repo}"]
    messages.append(f"pyproject: {'ok' if (resolved_repo / 'pyproject.toml').exists() else 'missing'}")
    messages.append(f"launcher: {'ok' if script.exists() else 'missing'}")
    messages.append(f"command: {' '.join(launcher_command(resolved_repo, python=python))}")
    return messages


def main(argv: Sequence[str] | None = None) -> None:
    """Console entrypoint for installing MCP client configuration."""
    args = list(argv if argv is not None else sys.argv[1:])
    if args and args[0] == "doctor":
        parsed = _doctor_parser().parse_args(args[1:])
        for message in doctor(Path(parsed.repo), python=parsed.python):
            print(message)
        return

    parsed = _install_parser().parse_args(args)
    clients = normalize_clients(parsed.clients)
    results = install_clients(
        clients,
        repo=Path(parsed.repo),
        dry_run=parsed.dry_run,
        force=parsed.force,
        python=parsed.python,
    )
    for result in results:
        print(_format_result(result, dry_run=parsed.dry_run))


def _install_json_client(  # noqa: PLR0913
    client: str,
    *,
    repo: Path,
    home: Path | None,
    dry_run: bool,
    force: bool,
    python: str,
) -> InstallResult:
    path = client_config_path(client, home)
    data = _read_json_config(path)
    updated, changed, skipped_reason = _merge_client_config(
        client,
        data,
        launcher=launcher_command(repo, python=python),
        force=force,
    )

    if changed and not dry_run:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(updated, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return InstallResult(
        client=client,
        kind="json",
        changed=changed,
        path=path,
        skipped_reason=skipped_reason,
    )


def _merge_client_config(
    client: str,
    data: dict[str, object],
    *,
    launcher: list[str],
    force: bool,
) -> tuple[dict[str, object], bool, str | None]:
    updated = dict(data)
    server = _server_config(client, launcher)
    key = "mcp" if client == "opencode" else "mcpServers"
    existing_servers = updated.get(key)
    servers = {} if not isinstance(existing_servers, dict) else dict(existing_servers)

    if SERVER_NAME in servers and not force:
        return updated, False, "existing server config; pass --force to replace"

    servers[SERVER_NAME] = server
    updated[key] = servers
    if client == "opencode":
        updated.setdefault("$schema", "https://opencode.ai/config.json")
    return updated, True, None


def _server_config(client: str, launcher: list[str]) -> dict[str, object]:
    if client in {"cursor", "gemini"}:
        return {"command": launcher[0], "args": launcher[1:]}
    if client == "opencode":
        return {"type": "local", "command": launcher, "enabled": True}
    if client == "copilot":
        return {
            "type": "local",
            "command": launcher[0],
            "args": launcher[1:],
            "env": {},
            "tools": ["*"],
        }
    raise ValueError(f"Unsupported JSON client: {client}")


def _read_json_config(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"JSON config must be an object: {path}")
    return data


def _install_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Install ate-smt7-diff MCP into local clients")
    parser.add_argument(
        "--clients",
        default="all",
        help="Comma-separated clients: codex,claude,cursor,gemini,opencode,copilot, or all.",
    )
    parser.add_argument("--repo", default=str(Path.cwd()), help="ate-smt7-diff source checkout path.")
    parser.add_argument("--python", default="python3", help="Python command for the first-hop launcher.")
    parser.add_argument("--dry-run", action="store_true", help="Preview actions without writing files.")
    parser.add_argument("--force", action="store_true", help="Replace existing ate-smt7-diff entries.")
    return parser


def _doctor_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Check ate-smt7-diff MCP launcher setup")
    parser.add_argument("--repo", default=str(Path.cwd()), help="ate-smt7-diff source checkout path.")
    parser.add_argument("--python", default="python3", help="Python command for the first-hop launcher.")
    return parser


def _format_result(result: InstallResult, *, dry_run: bool) -> str:
    prefix = "would update" if dry_run and result.changed else "updated"
    if result.skipped_reason:
        return f"{result.client}: skipped - {result.skipped_reason}"
    if result.kind == "cli":
        action = "would run" if dry_run else "ran"
        return f"{result.client}: {action} {' '.join(result.command or [])}"
    if result.path:
        return f"{result.client}: {prefix} {result.path}"
    return f"{result.client}: no action"


def _subprocess_runner(command: list[str]) -> None:
    import subprocess

    subprocess.run(command, check=True)


if __name__ == "__main__":
    main()
