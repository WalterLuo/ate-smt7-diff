---
name: ate-smt7-diff
description: Use when comparing Advantest 93K SMT7 flow files or program packages, investigating SMT7 diff reports, validating package changes, or exporting structured SMT7 diff results through the ate-smt7-diff MCP server.
---

# ATE SMT7 Diff

Use the `ate-smt7-diff` MCP server instead of shelling out to ad hoc diff commands when the task involves SMT7 `.flow` files, program packages, suite configuration, timing, levels, testtables, vectors, or testmethods.

## Workflow

1. For unknown package paths, call `list_program_packages` or `smart_diff_discover` first.
2. For known `.flow` file pairs, call `diff_flows`.
3. For package comparisons, prefer `smart_diff_discover`, then use `smart_diff_suggest`, `smart_diff_explain`, or `smart_diff_validate` as follow-up tools.
4. Before rerunning an expensive comparison, try `query_diff_report` with the same old/new paths to reuse the cached report.
5. When the user asks for a deliverable, call `export_diff_report` with `markdown` or `json`.

## Response Style

Summarize the highest-risk changes first: removed suites, changed timing or level configuration, testtable limit changes, vector mapping changes, then testmethod changes. Mention the exact suites or files surfaced by the MCP response.
