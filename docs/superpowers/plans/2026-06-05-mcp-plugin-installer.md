# MCP Plugin Installer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a self-healing MCP launcher, multi-client installer, and Codex plugin bundle for `ate-smt7-diff`.

**Architecture:** Keep MCP server logic unchanged. Add a runtime layer that creates a private venv and delegates to the existing MCP server, plus an installer layer that writes or invokes each client's documented MCP configuration.

**Tech Stack:** Python standard library, existing `mcp` dependency, Codex plugin manifest JSON, stdio MCP client config files.

---

### Task 1: Runtime Launcher

**Files:**
- Create: `ate_smt7_diff/mcp/runtime.py`
- Modify: `pyproject.toml`
- Test: `tests/mcp/test_runtime.py`

- [ ] Add tests for cache root resolution, launcher command creation, and direct server command creation.
- [ ] Implement `RuntimeConfig`, `launcher_command()`, `server_command()`, and `run_launcher()`.
- [ ] Add console scripts `ate-smt7-diff-mcp` and `ate-smt7-diff-mcp-launcher`.
- [ ] Run `uv run pytest tests/mcp/test_runtime.py -v`.
- [ ] Commit runtime changes.

### Task 2: Client Installer Core

**Files:**
- Create: `ate_smt7_diff/mcp/install.py`
- Test: `tests/mcp/test_install.py`

- [ ] Add tests for Cursor, Gemini, OpenCode, and Copilot JSON merge behavior.
- [ ] Add tests for Codex, Claude, and Gemini CLI command planning.
- [ ] Implement dry-run install planning, JSON merge helpers, `--clients`, `--repo`, `--force`, and `doctor`.
- [ ] Add console script `ate-smt7-diff-mcp-install`.
- [ ] Run `uv run pytest tests/mcp/test_install.py -v`.
- [ ] Commit installer changes.

### Task 3: Codex Plugin Bundle and Skill

**Files:**
- Create: `plugins/ate-smt7-diff/.codex-plugin/plugin.json`
- Create: `plugins/ate-smt7-diff/.mcp.json`
- Create: `plugins/ate-smt7-diff/scripts/ate-smt7-diff-mcp`
- Create: `plugins/ate-smt7-diff/skills/ate-smt7-diff/SKILL.md`
- Test: `tests/mcp/test_plugin_bundle.py`

- [ ] Add tests that validate plugin manifest paths, MCP command shape, and skill frontmatter.
- [ ] Implement plugin metadata with `skills` and `mcpServers`.
- [ ] Implement a small script that delegates to `python -m ate_smt7_diff.mcp.runtime --repo <repo>`.
- [ ] Write a concise skill describing when to call `smart_diff_discover`, `diff_flows`, query, and export tools.
- [ ] Run plugin validator if available and run `uv run pytest tests/mcp/test_plugin_bundle.py -v`.
- [ ] Commit plugin changes.

### Task 4: Documentation and Full Verification

**Files:**
- Modify: `docs/mcp/README.md`
- Modify: `docs/mcp/clients.md`
- Modify: `README_CN.md`
- Modify: `README.md`
- Test: `tests/mcp/test_docs.py`

- [ ] Update docs with one-command install examples, dry-run, doctor, and plugin path.
- [ ] Update doc tests for the new commands and supported clients.
- [ ] Run `uv run pytest tests/mcp -v`.
- [ ] Run `uv run pytest -v`.
- [ ] Run `uv run ruff check ate_smt7_diff/mcp mcp_server.py tests/mcp`.
- [ ] Run `uv run ruff format --check ate_smt7_diff/mcp mcp_server.py tests/mcp`.
- [ ] Commit docs and verification fixes.
