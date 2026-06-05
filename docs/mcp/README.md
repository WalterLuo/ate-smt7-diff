# ate-smt7-diff Local MCP

`ate-smt7-diff` exposes its SMT7 diff capabilities through a local stdio MCP server.

The server is intended for local agent clients that can launch a command and communicate over stdin/stdout.

## Launch Commands

From the repository root:

```bash
python mcp_server.py
```

After editable install:

```bash
python -m ate_smt7_diff.mcp.server
```

Direct MCP console script:

```bash
ate-smt7-diff-mcp
```

Self-healing launcher with a private Python runtime:

```bash
python3 scripts/ate-smt7-diff-mcp-launcher --repo .
```

The launcher creates or repairs a private virtual environment under
`~/.cache/ate-smt7-diff-mcp` by default. Override that location with
`ATE_SMT7_DIFF_MCP_HOME`.

## One-Command Client Install

Preview changes:

```bash
ate-smt7-diff-mcp-install --clients all --repo . --dry-run
```

Install into supported clients:

```bash
ate-smt7-diff-mcp-install --clients codex,claude,cursor,gemini,opencode,copilot --repo .
```

Check launcher paths:

```bash
ate-smt7-diff-mcp-install doctor --repo .
```

The installer configures local stdio MCP entries for Codex CLI, Claude Code,
Cursor, Gemini CLI, OpenCode, and GitHub Copilot CLI. It skips existing
`ate-smt7-diff` entries unless `--force` is passed.

## Codex Plugin

This repository is also a Codex plugin bundle:

- `.codex-plugin/plugin.json`
- `.mcp.json`
- `skills/ate-smt7-diff/SKILL.md`

The plugin MCP entry runs:

```bash
python3 ./scripts/ate-smt7-diff-mcp-launcher --repo .
```

This keeps the plugin self-contained when Codex caches the repository root.

## Capabilities

- List SMT7 program packages.
- Suggest matched `.flow` file pairs.
- Diff single `.flow` files.
- Diff full program packages.
- Query and export cached diff reports.
- Run smart discovery, suggestion, explanation, and validation workflows.

## Resources

- `ate-smt7-diff://manifest`
- `ate-smt7-diff://usage`
- `ate-smt7-diff://clients`
- `ate-smt7-diff://examples`

## Transport Scope

This integration supports local stdio MCP. It does not provide remote MCP over HTTP, SSE, or streamable HTTP.
