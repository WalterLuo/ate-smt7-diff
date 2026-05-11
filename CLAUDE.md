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
  cli.py           # argparse CLI entry point
  models.py        # ALL dataclasses and domain models (single source of truth)
  builder.py       # Orchestrates parsing -> diff -> config views
  parsers/         # Text-parsing modules for each file type
    flow_parser.py
    suite_parser.py
    level_parser.py
    timing_parser.py
    testtable_parser.py
  diff/            # Pure diff-computation logic
    flow_diff.py
    suite_diff.py
    level_diff.py
    timing_diff.py
    testtable_diff.py
  formatters/      # Output formatters
    console.py
    markdown.py
    json.py
tests/             # Unit tests (pytest)
```

## Key Concepts

### Models (models.py)
All domain models are frozen `@dataclass(frozen=True)` where possible.

- `DiffReport`: top-level report aggregating all diffs
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

# Output formats
python -m ate_smt7_diff.cli old.flow new.flow -f markdown
python -m ate_smt7_diff.cli old.flow new.flow -f json
```

## Testing

```bash
pytest                          # run all tests
pytest tests/test_timing_diff.py -v   # run specific test module
```

## Important Implementation Details

### Builder (builder.py)
- `diff_flow_files()` is the main orchestration function.
- `load_program_context()` derives the program root as `flow_file.parent.parent` (e.g., `test1/example1/testflow/example1.flow` -> `test1/example1`).
- `_resolve_timing_config()` and `_resolve_level_config()` extract override indices from suite flow config.
- `_build_suite_config_views()` hydrates each suite by loading timing/level/testtable files and parsing relevant snippets.
- `_diff_port_timing()` handles timing spec comparisons when `override_tim_equ_set` is absent.

### Parsers
All parsers are line-based text parsers operating on SMT7 ASCII config files. They extract sections by keyword matching and parse key-value or structured blocks.

- `flow_parser.py`: extracts `test_flow` section and parses suite occurrences with group paths.
- `suite_parser.py`: extracts `context` and `test_suites` sections; `parse_suite_config()` builds the per-suite parameter dict.
- `timing_parser.py` (`TimingLoader`): loads timing files, extracts `SPECSET`, `EQSP TIM,EQN`, and `WAVETBL` blocks.
- `level_parser.py` (`LevelLoader`): loads level files, extracts `SPECSET` and `EQSP LEV,EQN` blocks.
- `testtable_parser.py` (`TestTableLoader`): loads CSV testtable files.

### Diff Logic
Diff modules are pure functions taking old/new model dicts/lists and returning diff objects (or `None` if no changes).

- `flow_diff.py`: computes added/removed/moved/unchanged suites; `detect_moves()` and `detect_swaps()` handle reordering.
- `suite_diff.py`: compares per-suite parameter dicts.
- `timing_diff.py`: diffs timing specs, EQNSET blocks, and WAVETBL blocks. WAVETBL diff uses pins-group key matching to detect replacements.
- `level_diff.py`: diffs level specs and EQNSET blocks.
- `testtable_diff.py`: diffs testtable rows by `(suite_name, test_name, test_number)` key.

### Formatters
- `console.py`: human-readable plain text with indentation.
- `markdown.py`: Markdown tables and headers.
- `json.py`: JSON serialization.

All formatters handle the `replaced_from` pattern (when a block/spec/EQNSET replaces another rather than being a pure add/remove).

## Development Conventions

- **Immutability**: prefer frozen dataclasses; create new objects rather than mutating.
- **Models**: all models live in `models.py` to avoid circular imports.
- **Unknown fields**: pin/timing configs use an `extra: Dict[str, str]` to capture fields not explicitly modeled.
- **Error handling**: parsers and builder log warnings for malformed values rather than crashing.
- **Tests**: add tests in `tests/` using `unittest` or `pytest` patterns.

## Local Test Data

`Test1/example1/` and `Test2/example2/` contain sample SMT7 program trees used for manual CLI testing. They include `testflow/`, `levels/`, `timing/`, and `testtable/` subdirectories. These are NOT committed to git.
