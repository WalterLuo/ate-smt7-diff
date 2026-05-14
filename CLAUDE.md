# ate-smt7-diff

SMT7 ATE test program diff engine. Compares two Advantest 93K SMT7 test program flows (`.flow` files) and their associated configuration files, producing structured diff reports in console, Markdown, or JSON format.

## Project Overview

- **Language**: Python 3.9+
- **Package**: `ate-smt7-diff`
- **CLI Entry**: `python -m ate_smt7_diff.cli`
- **Test Runner**: `pytest`

## Architecture

```
ate_smt7_diff/
  cli.py              # argparse CLI entry point (single + batch mode)
  flow_matcher.py     # Flow file matching logic for batch diff
  filesystem.py       # FileSystem abstraction for testability
  config_models.py    # Flow matcher configuration models
  models/             # Domain models (single source of truth)
    __init__.py         # Re-exports for backward compatibility
    context.py          # ProgramContext
    flow.py             # DiffReport, FlowDiff, TestItem, BatchDiffReport
    level.py            # LevelSpec, DpsPinConfig, LevelSetPinConfig, EqnSetBlock, EqnSetDiff, LevelSpecDiff
    suite.py            # SuiteConfigDiff, SuiteConfigReport, SuiteConfigView
    testmethod.py       # TestMethodDiff, TestMethodInfo
    testtable.py        # TestTableRow, TestTableRowDiff, TestTableSuiteDiff
    timing.py           # TimingSpec, TimingPinConfig, TimingSetConfig, TimingEqnSetBlock, TimingEqnSetDiff, TimingSpecDiff
    vector.py           # VectorPatternMapping, VectorSuiteDiff, VectorFileDateChange
    wavetable.py        # WaveTblBlock, WaveTblDiff, WaveTblPinsGroup, WaveTblPinsGroupDiff, WaveTblRow
  parsers/            # Text-parsing modules for each file type
    flow_parser.py
    suite_parser.py
    level_parser.py
    timing_parser.py
    testtable_parser.py
    vector_parser.py
    testmethod_parser.py
  diff/               # Pure diff-computation logic
    flow_diff.py
    suite_diff.py
    level_diff.py
    timing_diff.py
    testtable_diff.py
    vector_diff.py
    testmethod_diff.py
    utils.py
  formatters/         # Output formatters
    console.py
    markdown.py
    json.py
    shared.py           # Shared serialization helpers
    batch_console.py
    batch_markdown.py
    batch_json.py
  builder/            # Orchestrates parsing -> diff -> config views
    __init__.py         # Facade: diff_flow_files()
    context.py          # Program context helpers
    extractors.py       # Config extraction from suite views
    resolvers.py        # Path resolvers for timing/level/testtable/vector
    suite_views.py      # Build hydrated SuiteConfigView dicts
    timing_diff_dispatch.py  # Timing diff dispatch logic
  plugins/            # Plugin-based diff extensibility
    __init__.py
    registry.py         # Plugin registry
    builtin.py          # Built-in diff plugins
```

## Key Concepts

### Models (`models/`)
All domain models are frozen `@dataclass(frozen=True)` where possible.

- `DiffReport`: top-level report aggregating all diffs
- `BatchDiffReport`: batch diff across multiple flow file pairs
- `FlowDiff`: suite added/removed/moved/unchanged in the flow
- `SuiteConfigReport` / `SuiteConfigDiff`: suite-level configuration parameter changes
- `ProgramContext`: resolved paths to associated config files (levels, timing, vectors, testtable)
- `SuiteConfigView`: complete hydrated view for a single suite, parsed from flow + config files

### Level Models
- `LevelSpec`: a single spec parameter (actual, min, max, units)
- `DpsPinConfig` / `LevelSetPinConfig`: pin configurations with known fields + `extra` dict for unknown fields
- `EqnSetBlock`: parsed EQNSET block from `EQSP LEV,EQN`
- `EqnSetDiff` / `LevelSpecDiff`: diff results

### Timing Models
- `TimingSpec`: a single timing spec parameter
- `TimingPinConfig` / `TimingSetConfig`: timing pin/timingset configurations with known fields + `extra` dict
- `TimingEqnSetBlock`: parsed EQNSET block from `EQSP TIM,EQN`
- `TimingSpecDiff` / `TimingEqnSetDiff`: diff results. Both support `replaced_from` semantics to detect when one spec/EQNSET replaces another.
- `WaveTblBlock` / `WaveTblDiff`: WAVETBL block comparison with `replaced_from` support

### TestTable Models
- `TestTableRow`: a single row from testtable CSV
- `TestTableSuiteDiff`: per-suite testtable diff

### Vector Models
- `VectorPatternMapping`: pattern name to file mapping
- `VectorSuiteDiff`: per-suite vector pattern diff (added/removed/changed/file_date_changed)

### TestMethod Models
- `TestMethodInfo`: testmethod ID and class mapping
- `TestMethodDiff`: per-suite testmethod diff (tm_id_changed/class_changed/both_changed/file_changed/file_not_found)

## CLI Usage

```bash
# Basic flow diff
python -m ate_smt7_diff.cli old.flow new.flow

# Include suite config diff
python -m ate_smt7_diff.cli old.flow new.flow --suite-diff

# Load and diff all associated configs (timing, levels, testtable)
python -m ate_smt7_diff.cli old.flow new.flow --load-configs

# Also diff testtable CSV files
python -m ate_smt7_diff.cli old.flow new.flow --load-configs --testtable-diff

# Also diff testmethod source files
python -m ate_smt7_diff.cli old.flow new.flow --load-configs --testmethod-diff

# Output formats
python -m ate_smt7_diff.cli old.flow new.flow -f markdown
python -m ate_smt7_diff.cli old.flow new.flow -f json

# Batch diff: compare two program packages
python -m ate_smt7_diff.cli --packages old_pkg new_pkg
python -m ate_smt7_diff.cli --packages old_pkg new_pkg --load-configs -f markdown
```

## Testing

```bash
pytest                          # run all tests
pytest tests/test_timing_diff.py -v   # run specific test module
```

## Important Implementation Details

### Builder (`builder/`)
- `diff_flow_files()` in `builder/__init__.py` is the main orchestration function.
- `load_program_context()` derives the program root as `flow_file.parent.parent`.
- `resolvers.py` extracts override indices from suite flow config for timing/level/testtable/vector.
- `suite_views.py` hydrates each suite by loading timing/level/testtable/vector files and parsing relevant snippets.
- `timing_diff_dispatch.py` handles timing spec comparisons when `override_tim_equ_set` is absent.
- The builder uses a plugin system (`plugins/`) to run diff computations. Enabled plugins are determined from CLI flags.

### Parsers
All parsers are line-based text parsers operating on SMT7 ASCII config files. They extract sections by keyword matching and parse key-value or structured blocks.

- `flow_parser.py`: extracts `test_flow` section and parses suite occurrences with group paths.
- `suite_parser.py`: extracts `context` and `test_suites` sections; `parse_suite_config()` builds the per-suite parameter dict.
- `timing_parser.py` (`TimingLoader`): loads timing files, extracts `SPECSET`, `EQSP TIM,EQN`, and `WAVETBL` blocks.
- `level_parser.py` (`LevelLoader`): loads level files, extracts `SPECSET` and `EQSP LEV,EQN` blocks.
- `testtable_parser.py` (`TestTableLoader`): loads CSV testtable files.
- `vector_parser.py` (`VectorLoader`): loads vector pattern mapping files.
- `testmethod_parser.py`: extracts testmethod class and ID from flow config.

### Diff Logic
Diff modules are pure functions taking old/new model dicts/lists and returning diff objects (or `None` if no changes).

- `flow_diff.py`: computes added/removed/moved/unchanged suites; `detect_moves()` and `detect_swaps()` handle reordering.
- `suite_diff.py`: compares per-suite parameter dicts.
- `timing_diff.py`: diffs timing specs, EQNSET blocks, and WAVETBL blocks. WAVETBL diff uses pins-group key matching to detect replacements.
- `level_diff.py`: diffs level specs and EQNSET blocks.
- `testtable_diff.py`: diffs testtable rows by `(suite_name, test_name, test_number)` key.
- `vector_diff.py`: diffs vector pattern mappings and file dates.
- `testmethod_diff.py`: diffs testmethod IDs, classes, and source files.

### Formatters
- `console.py`: human-readable plain text with indentation.
- `markdown.py`: Markdown tables and headers.
- `json.py`: JSON serialization.
- `shared.py`: Shared serialization helpers used by all formatters (`_fmt_val`, `fields_str`, `field_changes`, model-to-dict helpers, `_arc` utilities).

All formatters handle the `replaced_from` pattern (when a block/spec/EQNSET replaces another rather than being a pure add/remove).

### Plugins
- `registry.py`: plugin registry with `register()` and `get()`.
- `builtin.py`: built-in diff plugins (suite_config, level_spec, eqnset, timing, timing_wavetbl, vector, testtable, testmethod).
- Each plugin implements `requires_views` and `run()` to contribute diff results to the final report.

## Development Conventions

- **Immutability**: prefer frozen dataclasses; create new objects rather than mutating.
- **Models**: all models live in `models/` package. Import from `models/__init__.py` for backward compatibility.
- **Unknown fields**: pin/timing configs use an `extra: Dict[str, str]` to capture fields not explicitly modeled.
- **Error handling**: parsers and builder log warnings for malformed values rather than crashing.
- **File size**: keep files under 800 lines; extract modules when they grow too large.
- **Tests**: add tests in `tests/` using `unittest` or `pytest` patterns.

## Local Test Data

`Test1/example1/` and `Test2/example2/` contain sample SMT7 program trees used for manual CLI testing. They include `testflow/`, `levels/`, `timing/`, `vectors/`, and `testtable/` subdirectories. These are NOT committed to git.
