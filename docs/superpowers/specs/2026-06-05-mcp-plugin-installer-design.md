# MCP Plugin Installer Design

## Goal

Package `ate-smt7-diff` as a reusable local MCP capability that can be installed once and used from Codex CLI, Claude Code, Cursor, Gemini CLI, OpenCode, and GitHub Copilot CLI.

## Current State

The project already exposes a local stdio MCP server through `mcp_server.py` and `python -m ate_smt7_diff.mcp.server`. The MCP tools are modular and tested, but users still need to manually choose a Python interpreter and hand-write client configuration.

## Chosen Approach

Use a repository-owned installer with a private Python runtime plus a Codex plugin wrapper.

- A launcher module creates or repairs a private virtual environment under a user cache directory.
- The launcher installs the package from the source checkout into that environment.
- All MCP clients call the launcher with the source checkout path; the launcher then delegates to the private environment's Python module entrypoint.
- A client installer writes or invokes each supported client's MCP configuration format.
- A Codex plugin bundle lives in the repository so Codex can install the same capability through a marketplace-like plugin shape.

This is the "self-healing runtime" style: client configs stay stable while the launcher handles Python dependencies.

## Components

### Runtime Launcher

`ate_smt7_diff/mcp/runtime.py` owns deterministic runtime setup.

- Resolve a cache root from `ATE_SMT7_DIFF_MCP_HOME` or `~/.cache/ate-smt7-diff-mcp`.
- Create `.venv` with Python `>=3.10`.
- Prefer `uv pip install -e <repo>` when `uv` exists.
- Fall back to `<venv>/bin/python -m pip install -e <repo>`.
- Use a small stamp file to avoid reinstalling when `pyproject.toml` and core MCP files have not changed.
- Execute `python -m ate_smt7_diff.mcp.server` from the private environment.

### CLI Entrypoints

Add console scripts:

- `ate-smt7-diff-mcp`: run the MCP server directly from the active environment.
- `ate-smt7-diff-mcp-launcher`: ensure the private runtime, then run the MCP server.
- `ate-smt7-diff-mcp-install`: configure one or more clients.

### Client Installer

`ate_smt7_diff/mcp/install.py` owns client configuration.

Supported client behaviors:

- Codex CLI: use `codex mcp add ate-smt7-diff -- <launcher> --repo <repo>`.
- Claude Code: use `claude mcp add --transport stdio --scope user ate-smt7-diff -- <launcher> --repo <repo>`.
- Gemini CLI: use `gemini mcp add ate-smt7-diff <launcher> --repo <repo>` when available, otherwise update `~/.gemini/settings.json`.
- Cursor: update `~/.cursor/mcp.json`.
- OpenCode: update `~/.config/opencode/opencode.json`.
- GitHub Copilot CLI: update `~/.copilot/mcp-config.json`.

The installer supports:

- `--clients` with comma-separated names or `all`.
- `--repo` to point at a specific checkout.
- `--dry-run` to preview changes.
- `--force` to overwrite an existing `ate-smt7-diff` server block.
- `doctor` to validate launcher command shape and runtime setup without requiring every client to be installed.

### Codex Plugin Bundle

Create `plugins/ate-smt7-diff/` containing:

- `.codex-plugin/plugin.json`
- `.mcp.json`
- `skills/ate-smt7-diff/SKILL.md`
- `scripts/ate-smt7-diff-mcp`

The plugin's `.mcp.json` starts the script inside the plugin bundle. The script locates the source checkout from `ATE_SMT7_DIFF_REPO` first, then from the repository layout used by this project. It delegates to the same runtime launcher.

### Skill Behavior

The skill teaches agents when and how to use the MCP tools:

- Discover program packages before diffing unknown paths.
- Use `smart_diff_discover` for package comparisons.
- Use `diff_flows` for known `.flow` pairs.
- Query cached reports before re-running expensive diffs.
- Export Markdown or JSON when the user asks for a report artifact.

The skill remains concise; detailed client setup stays in normal docs and scripts.

## Error Handling

- Missing Python `>=3.10`: report a clear installation error.
- Missing `uv`: fall back to `venv + pip`.
- Client command missing: write config directly when a stable config file is documented; otherwise report skipped with a reason.
- Existing client server config: skip by default unless `--force` is set.
- Invalid JSON config: abort that client with the file path and parsing error.

## Testing

Add focused tests for:

- Launcher command construction and cache path selection.
- Installer config merging for Cursor, Gemini, OpenCode, and Copilot CLI.
- CLI command generation for Codex and Claude.
- Plugin manifest shape and plugin `.mcp.json` command.
- Skill frontmatter and core workflow instructions.

Run:

- `uv run pytest tests/mcp -v`
- `uv run ruff check ate_smt7_diff/mcp mcp_server.py tests/mcp`
- `uv run ruff format --check ate_smt7_diff/mcp mcp_server.py tests/mcp`

## Non-Goals

- Do not publish to a public plugin marketplace.
- Do not install system Python, Homebrew, or OS packages.
- Do not implement remote HTTP MCP.
- Do not silently mutate every client without an explicit installer command.
