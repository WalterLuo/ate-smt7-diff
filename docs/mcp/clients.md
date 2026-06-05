# Local MCP Client Configuration

## Recommended Installer

Run from the repository root after installing the package or through `uv run`:

```bash
uv run ate-smt7-diff-mcp-install --clients all --repo . --dry-run
uv run ate-smt7-diff-mcp-install --clients all --repo .
```

The installer configures a stable first-hop launcher:

```json
{
  "command": "python3",
  "args": [
    "/Users/walter_luo/Project/skills/ate_skill/ate-smt7-diff/scripts/ate-smt7-diff-mcp-launcher",
    "--repo",
    "/Users/walter_luo/Project/skills/ate_skill/ate-smt7-diff"
  ]
}
```

That launcher creates or repairs the private MCP Python environment and then starts `python -m ate_smt7_diff.mcp.server`.

## Direct Commands

For manual configuration, direct stdio commands still work:

```json
{
  "command": "python",
  "args": ["-m", "ate_smt7_diff.mcp.server"]
}
```

Client MCP schemas vary by version. Prefer the installer unless you need to hand-edit a specific client config.

## Codex CLI

The installer uses:

```bash
codex mcp add ate-smt7-diff -- python3 scripts/ate-smt7-diff-mcp-launcher --repo .
```

Codex CLI and the Codex IDE extension share `~/.codex/config.toml`.

## Claude Code

The installer uses user scope:

```bash
claude mcp add --transport stdio --scope user ate-smt7-diff -- python3 scripts/ate-smt7-diff-mcp-launcher --repo .
```

## Cursor

The installer updates `~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "ate-smt7-diff": {
      "command": "python3",
      "args": ["scripts/ate-smt7-diff-mcp-launcher", "--repo", "/absolute/path/to/ate-smt7-diff"]
    }
  }
}
```

## Gemini CLI

When `gemini` is available, the installer uses:

```bash
gemini mcp add ate-smt7-diff python3 scripts/ate-smt7-diff-mcp-launcher --repo .
```

If the CLI command is unavailable, it updates `~/.gemini/settings.json` under `mcpServers`.

## OpenCode

The installer updates `~/.config/opencode/opencode.json`:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "ate-smt7-diff": {
      "type": "local",
      "command": ["python3", "scripts/ate-smt7-diff-mcp-launcher", "--repo", "/absolute/path/to/ate-smt7-diff"],
      "enabled": true
    }
  }
}
```

## GitHub Copilot CLI

The installer updates `~/.copilot/mcp-config.json`:

```json
{
  "mcpServers": {
    "ate-smt7-diff": {
      "type": "local",
      "command": "python3",
      "args": ["scripts/ate-smt7-diff-mcp-launcher", "--repo", "/absolute/path/to/ate-smt7-diff"],
      "env": {},
      "tools": ["*"]
    }
  }
}
```

In Copilot CLI interactive mode, `/mcp show` can verify the server after installation.

## Codex Plugin Bundle

Codex can also consume this repository as a plugin because it contains:

```text
.codex-plugin/plugin.json
.mcp.json
skills/ate-smt7-diff/SKILL.md
```

The plugin path is repository-root based so the cached plugin includes the Python package, MCP server, launcher, and skill together.
