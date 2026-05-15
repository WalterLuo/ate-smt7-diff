---
name: smt7-diff
description: Intelligent diff assistant for Advantest 93K SMT7 test programs. Compare program packages, analyze changes in timing/level/testtable/vector/testmethod, and generate release notes. Use when working with SMT7 ATE test program revisions.
origin: local
---

# SMT7 Test Program Diff Assistant

Intelligent diff and analysis for Advantest 93K SMT7 test programs.

## When to Activate

- Comparing two versions of a test program (e.g., B0102 vs A0106)
- Reviewing changes before releasing a new program revision
- Checking if timing, level, or testtable limits have changed
- Verifying no test suites were accidentally removed
- Generating release notes or change summaries
- Investigating why a test program behaves differently on the tester

## Core Workflows

### 1. Program Package Comparison

When the user wants to compare two program directories:

1. Use `list_program_packages` to discover available packages if paths are unclear
2. Use `suggest_flow_pairs` to see how flow files will be matched
3. Use `smart_diff_discover` to get a comprehensive change summary
4. Use `smart_diff_suggest` for prioritized review recommendations
5. Use `smart_diff_validate` to catch anomalies (missing suites, unmatched files)

**Example conversation:**
> User: "看看 Test1 和 Test2 有什么不一样"
> 
> Action: Run `smart_diff_discover`, then `smart_diff_suggest`, then summarize in Chinese.

### 2. Focused Category Inspection

When the user cares about a specific aspect:

1. Run `smart_diff_discover` with `load_configs=True`
2. Run `smart_diff_explain` with `focus_category`:
   - `timing` — timing specs, pins, timingsets
   - `level` — voltage/current levels
   - `testtable` — USL/LSL limits
   - `vector` — pattern mappings
   - `testmethod` — test class or ID changes
   - `suite_config` — flow override parameters

**Example conversation:**
> User: "确认 timing 改动"
> 
> Action: Run `smart_diff_explain` with `focus_category="timing"`, then summarize.

### 3. Anomaly Detection

When the user wants to ensure nothing was missed:

1. Run `smart_diff_validate`
2. Report any `error` or `warning` severity findings
3. Highlight unmatched files and removed suites

**Example conversation:**
> User: "检查有没有漏配"
> 
> Action: Run `smart_diff_validate`, report unmatched flows and removed suites.

### 4. Report Generation

When the user wants a formal report:

1. Run `diff_flows` with `load_configs=True` on the package pair
2. Run `export_diff_report` with `format="markdown"`
3. Present or save the markdown report

**Example conversation:**
> User: "生成 Release Note"
> 
> Action: Run `diff_flows` then `export_diff_report` in markdown format.

### 5. Per-Flow Deep Dive

When the user wants details on a specific flow file pair:

1. Run `diff_flows` on the two `.flow` files
2. Run `query_diff_report` with `category` to filter
3. Run `export_diff_report` to get full markdown/JSON

## Response Guidelines

- Always summarize findings in the user's language (Chinese if they ask in Chinese)
- Prioritize high-severity changes first
- Use tables when listing multiple changed suites
- For testtable changes, explicitly mention USL/LSL adjustments
- For timing changes, mention affected pins or spec names if available
- Never claim success if `smart_diff_validate` returns `passed: false`
- When suggesting next steps, reference specific suite names and flow files

## Severity Interpretation

| Severity | Meaning | Example |
|----------|---------|---------|
| critical | Program may fail on tester | Missing essential suite, wrong timing spec |
| high | Requires careful review | Removed suite, timing/level changed |
| medium | Routine check needed | Testtable limit adjusted, vector mapping changed |
| low | Informational | Suite order changed, config parameter tweaked |

## Common Pitfalls to Mention

- **Timing without Level**: If timing changed but level did not, confirm if level also needs adjustment
- **Unmatched flows**: Old flow files without a new counterpart may indicate accidental deletion
- **Removed suites**: Always double-check if removed suites were intentionally dropped
- **Vector mapping**: Changed pattern files must be loaded to the tester before running
