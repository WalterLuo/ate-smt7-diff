# Local Stdio MCP Architecture Design

## Goal

Refactor `ate-smt7-diff` from a single-file MCP server into a modular local stdio MCP architecture that can be used by multiple agent clients: Codex CLI, Claude Code, Cursor, Gemini CLI, OpenCode, and GitHub Copilot CLI.

The change focuses on local MCP usage only. Remote HTTP/SSE MCP is out of scope for this iteration.

## Current State

The project already includes a working MCP entry point at `mcp_server.py`.

It uses `FastMCP("ate-smt7-diff")`, registers all tools directly in one file, and starts with:

```python
mcp.run(transport="stdio")
```

The existing server exposes useful capabilities, but the implementation is hard to extend because the entry point, cache, tool registration, JSON responses, and agent-helper workflows all live in one file.

## Scope

This design covers:

- A modular package under `ate_smt7_diff/mcp/`.
- A backward-compatible `mcp_server.py` wrapper.
- Stable MCP tool names compatible with the current server.
- MCP resources for agent-readable usage, manifest, client setup, and examples.
- Documentation for local stdio configuration in the requested agent clients.
- Tests for the MCP architecture layer.

This design does not cover:

- Remote MCP over HTTP, SSE, or streamable HTTP.
- Authentication, authorization, tenancy, uploads, or shared network storage.
- A full Superpowers-style skill framework or multi-role workflow runtime.
- Changes to existing diff, parser, formatter, or agent business logic unless needed to call it cleanly from MCP modules.

## Architecture

The MCP server will be split into focused modules:

```text
ate_smt7_diff/
  mcp/
    __init__.py
    server.py
    cache.py
    serializers.py
    resources.py
    tools/
      __init__.py
      packages.py
      diff.py
      agent.py

mcp_server.py
docs/
  mcp/
    README.md
    clients.md
```

### Module Responsibilities

`ate_smt7_diff/mcp/server.py`

Creates the `FastMCP("ate-smt7-diff")` instance, registers all tools and resources, and exposes:

- `create_server()`
- `run_stdio()`
- a `__main__` entry point for `python -m ate_smt7_diff.mcp.server`

`ate_smt7_diff/mcp/cache.py`

Owns the recent report and discovery-result LRU caches. The cache behavior remains intentionally small and local: at most 10 report entries and 10 agent-result entries per server process.

`ate_smt7_diff/mcp/serializers.py`

Provides helpers for consistent JSON responses and errors. This prevents each tool from duplicating `json.dumps(..., indent=2, ensure_ascii=False)` and keeps error payloads stable.

`ate_smt7_diff/mcp/tools/packages.py`

Registers package discovery tools:

- `list_program_packages(directory)`
- `suggest_flow_pairs(old_package, new_package, match_config=None)`

`ate_smt7_diff/mcp/tools/diff.py`

Registers flow diff tools:

- `diff_flows(old_path, new_path, suite_diff=False, load_configs=False, testtable_diff=False, testmethod_diff=False)`
- `query_diff_report(old_path, new_path, category=None)`
- `export_diff_report(old_path, new_path, format="markdown")`

`ate_smt7_diff/mcp/tools/agent.py`

Registers agent-helper tools:

- `smart_diff_discover(old_package, new_package, load_configs=True)`
- `smart_diff_suggest(old_package, new_package)`
- `smart_diff_explain(old_package, new_package, focus_category=None, focus_suite=None)`
- `smart_diff_validate(old_package, new_package)`

`ate_smt7_diff/mcp/resources.py`

Registers resources that help MCP clients and agents understand the server without relying on external docs:

- `ate-smt7-diff://manifest`
- `ate-smt7-diff://usage`
- `ate-smt7-diff://clients`
- `ate-smt7-diff://examples`

`mcp_server.py`

Remains as a compatibility wrapper. Existing configurations that run `python mcp_server.py` continue to work. The wrapper delegates to `ate_smt7_diff.mcp.server.run_stdio()`.

## Tool Compatibility

Existing MCP tool names will remain unchanged. This protects any client prompt, MCP config, or agent workflow already using the current server.

The tools will still return JSON strings, matching the current server behavior.

## Resource Content

### `ate-smt7-diff://manifest`

Returns a JSON manifest containing:

- server name
- package version when available
- transport: `stdio`
- supported client category: local MCP clients
- tool groups and tool names
- resource URIs
- recommended workflows

### `ate-smt7-diff://usage`

Returns Markdown usage guidance for:

- comparing two `.flow` files
- comparing two SMT7 program packages
- running discovery, suggestion, explanation, and validation workflows
- exporting cached reports

### `ate-smt7-diff://clients`

Returns Markdown that summarizes local stdio setup for:

- Codex CLI
- Claude Code
- Cursor
- Gemini CLI
- OpenCode
- GitHub Copilot CLI

The resource should point users to `docs/mcp/clients.md` for fuller setup examples.

### `ate-smt7-diff://examples`

Returns Markdown examples showing typical argument shapes:

- single flow diff
- package diff
- cached report query
- markdown export
- smart discovery plus suggest/explain/validate

## Client Setup Documentation

`docs/mcp/README.md` will explain the local MCP architecture and recommended launch commands:

```bash
python /Users/walter_luo/Project/skills/ate_skill/ate-smt7-diff/mcp_server.py
```

and:

```bash
python -m ate_smt7_diff.mcp.server
```

`docs/mcp/clients.md` will provide client-specific stdio examples for the requested clients. Where a client's MCP config schema varies by version, the documentation will give both:

- the stable command and args
- a clearly labeled example JSON block

The docs will avoid claiming remote MCP support.

## Error Handling

Input validation errors may continue to return:

```json
{
  "error": "..."
}
```

Runtime exceptions that are already handled by the current server should continue to return:

```json
{
  "error_type": "FileNotFoundError",
  "message": "..."
}
```

The implementation should preserve the current graceful behavior for `FileNotFoundError`, `PermissionError`, and `ValueError`.

## Testing Strategy

Tests should cover the new MCP layer without retesting all existing diff internals.

Add focused tests:

- `tests/mcp/test_server.py`
  - verifies `create_server()` returns a configured server
  - verifies expected tool and resource registration functions can be called without import errors

- `tests/mcp/test_tools_packages.py`
  - verifies `list_program_packages` returns JSON
  - verifies non-directory input returns a structured error

- `tests/mcp/test_tools_diff.py`
  - verifies `diff_flows` can run against sample flows or controlled fixtures
  - verifies `query_diff_report` returns a cache miss before diff and data after diff
  - verifies `export_diff_report` returns markdown or JSON for cached reports

- `tests/mcp/test_tools_agent.py`
  - verifies `smart_diff_discover` populates the agent cache
  - verifies suggest, explain, and validate agent cache-miss errors before discovery
  - verifies suggest, explain, and validate return structured JSON after discovery

- `tests/mcp/test_resources.py`
  - verifies manifest, usage, clients, and examples resources include stable identifiers and requested client names

Run the existing test suite after the refactor to confirm no behavior regressions.

## Completion Criteria

The refactor is complete when:

- `python mcp_server.py` still starts the local stdio MCP server.
- `python -m ate_smt7_diff.mcp.server` starts the same local stdio MCP server.
- Tool names remain compatible with the current server.
- MCP resources expose manifest, usage, client setup, and examples.
- Documentation covers Codex CLI, Claude Code, Cursor, Gemini CLI, OpenCode, and GitHub Copilot CLI.
- New MCP tests pass.
- Existing tests pass.
- No remote MCP behavior is implied or introduced.

## Implementation Notes

Use TDD for the refactor. Start with tests for the new module boundaries, then move code out of `mcp_server.py` into the package modules while keeping behavior stable.

Keep files small and focused. Do not refactor diff logic, parser logic, formatter logic, or existing agent business logic unless the MCP extraction requires a narrow import or wrapper adjustment.
