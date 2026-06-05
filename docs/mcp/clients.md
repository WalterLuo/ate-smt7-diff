# Local MCP Client Configuration

Use the same local stdio command for each MCP client:

```json
{
  "command": "python",
  "args": [
    "/Users/walter_luo/Project/skills/ate_skill/ate-smt7-diff/mcp_server.py"
  ]
}
```

After installing the package in editable mode, this command is also available:

```json
{
  "command": "python",
  "args": ["-m", "ate_smt7_diff.mcp.server"]
}
```

Client MCP schemas can vary by version. Use the command and args above inside the client's MCP server configuration block.

## Codex CLI

Configure a local stdio MCP server named `ate-smt7-diff` using the shared command and args.

## Claude Code

Configure a local stdio MCP server named `ate-smt7-diff` using the shared command and args.

## Cursor

Configure a local stdio MCP server named `ate-smt7-diff` using the shared command and args in Cursor's MCP settings.

## Gemini CLI

Configure a local stdio MCP server named `ate-smt7-diff` using the shared command and args.

## OpenCode

Configure a local stdio MCP server named `ate-smt7-diff` using the shared command and args.

## GitHub Copilot CLI

Configure a local stdio MCP server named `ate-smt7-diff` using the shared command and args when the CLI environment supports MCP stdio servers.
