# ate-smt7-diff

[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

A structured diff engine for Advantest 93K SMT7 ATE test programs. Compares test program flows (`.flow` files) and their associated configuration files, producing detailed diff reports in console, Markdown, or JSON format.

## Overview

`ate-smt7-diff` is designed for semiconductor test engineers who need to track changes between revisions of SMT7 test programs. It goes beyond simple text diffing by understanding the semantic structure of SMT7 files, detecting suite moves, configuration changes, spec replacements, and more.

**Key capabilities:**
- Compare two `.flow` files or entire program packages
- Detect suite additions, removals, moves, and swaps in the test flow
- Diff timing specs, level specs, EQNSET blocks, and wavetable configurations
- Compare testtable CSV data (including USL/LSL limits)
- Detect vector pattern mapping changes and file modifications
- Identify testmethod reference changes
- Output results as plain text, Markdown tables, or structured JSON

## Installation

### From Source

```bash
git clone <repository-url>
cd ate-smt7-diff
pip install -e .
```

### Development Install

```bash
pip install -e ".[dev]"
```

This installs the package along with development dependencies: `pytest`, `ruff`, `mypy`, and `bandit`.

## Quick Start

```bash
# Basic flow diff
python -m ate_smt7_diff.cli old.flow new.flow

# Or use the installed command
ate-smt7-diff old.flow new.flow
```

## Usage

### Single Flow Diff

Compare two individual `.flow` files:

```bash
# Basic flow sequence diff
python -m ate_smt7_diff.cli old.flow new.flow

# Include suite-level configuration changes
python -m ate_smt7_diff.cli old.flow new.flow --suite-diff

# Load and diff all associated configs (timing, levels, testtable)
python -m ate_smt7_diff.cli old.flow new.flow --load-configs

# Also diff testtable CSV files (USL/LSL limits, etc.)
python -m ate_smt7_diff.cli old.flow new.flow --load-configs --testtable-diff

# Also diff testmethod source files
python -m ate_smt7_diff.cli old.flow new.flow --load-configs --testmethod-diff
```

### Output Formats

```bash
# Console output (default)
python -m ate_smt7_diff.cli old.flow new.flow

# Markdown tables
python -m ate_smt7_diff.cli old.flow new.flow -f markdown

# JSON (machine-readable)
python -m ate_smt7_diff.cli old.flow new.flow -f json
```

### Batch Diff (Program Packages)

Compare two complete SMT7 program packages:

```bash
# Compare all flow files across two packages
python -m ate_smt7_diff.cli --packages old_pkg/ new_pkg/

# With full config diff and markdown output
python -m ate_smt7_diff.cli --packages old_pkg/ new_pkg/ --load-configs -f markdown
```

### CLI Options

| Option | Description |
|--------|-------------|
| `--suite-diff` | Include suite configuration parameter diff |
| `--load-configs` | Load and diff timing, level, and testtable configs |
| `--testtable-diff` | Diff testtable CSV files (requires `--load-configs`) |
| `--testmethod-diff` | Diff testmethod source files (requires `--load-configs`) |
| `-f, --format` | Output format: `console`, `markdown`, or `json` |
| `--packages` | Batch mode: compare two program packages |

## Architecture

```
ate_smt7_diff/
  cli.py              # argparse CLI entry point (single + batch mode)
  flow_matcher.py     # Flow file matching logic for batch diff
  filesystem.py       # FileSystem abstraction for testability
  config_models.py    # Flow matcher configuration models
  models/             # Domain models (frozen dataclasses)
    context.py          # ProgramContext
    flow.py             # DiffReport, FlowDiff, BatchDiffReport
    level.py            # LevelSpec, EqnSetBlock, LevelSpecDiff
    suite.py            # SuiteConfigDiff, SuiteConfigView
    testmethod.py       # TestMethodDiff, TestMethodInfo
    testtable.py        # TestTableRow, TestTableSuiteDiff
    timing.py           # TimingSpec, TimingEqnSetDiff, TimingSpecDiff
    vector.py           # VectorPatternMapping, VectorSuiteDiff
    wavetable.py        # WaveTblBlock, WaveTblDiff
  parsers/            # Line-based text parsers for SMT7 ASCII files
    flow_parser.py
    suite_parser.py
    level_parser.py
    timing_parser.py
    testtable_parser.py
    vector_parser.py
    testmethod_parser.py
  diff/               # Pure diff-computation logic
    flow_diff.py        # Suite add/remove/move/swap detection
    suite_diff.py       # Suite parameter comparison
    level_diff.py       # Level spec and EQNSET diff
    timing_diff.py      # Timing spec, EQNSET, and WAVETBL diff
    testtable_diff.py   # Testtable row comparison
    vector_diff.py      # Vector pattern mapping diff
    testmethod_diff.py  # Testmethod reference diff
    utils.py            # Shared diff utilities
  formatters/         # Output formatters
    console.py          # Human-readable plain text
    markdown.py         # Markdown tables and headers
    json.py             # JSON serialization
    shared.py           # Shared serialization helpers
    batch_console.py    # Batch console output
    batch_markdown.py   # Batch markdown output
    batch_json.py       # Batch JSON output
  builder/            # Orchestration layer
    __init__.py         # Facade: diff_flow_files()
    context.py          # Program context helpers
    extractors.py       # Config extraction from suite views
    resolvers.py        # Path resolvers for timing/level/testtable/vector
    suite_views.py      # Build hydrated SuiteConfigView dicts
    timing_diff_dispatch.py  # Timing diff dispatch logic
  plugins/            # Plugin-based diff extensibility
    registry.py         # Plugin registry
    builtin.py          # Built-in diff plugins
```

### Design Principles

- **Immutability**: Domain models use frozen `@dataclass(frozen=True)` to prevent accidental mutation
- **Pure Functions**: Diff modules are stateless pure functions that return diff objects or `None` when no changes are detected
- **Plugin Architecture**: Diff computations are plugin-based, allowing easy extension
- **Graceful Degradation**: Parsers log warnings for malformed values rather than crashing
- **Testability**: FileSystem abstraction enables easy mocking in tests

### Key Concepts

| Model | Purpose |
|-------|---------|
| `DiffReport` | Top-level report aggregating all diffs for a single flow comparison |
| `BatchDiffReport` | Aggregated report for batch package comparisons |
| `FlowDiff` | Suite added/removed/moved/unchanged in the test flow |
| `SuiteConfigView` | Complete hydrated view for a single suite (flow + config files) |
| `ProgramContext` | Resolved paths to associated config files (levels, timing, vectors, testtable) |
| `EqnSetDiff` | Diff result for EQNSET blocks with `replaced_from` semantics |
| `WaveTblDiff` | WAVETBL block comparison with replacement detection |

## Development

### Setup

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install in development mode
pip install -e ".[dev]"
```

### Running Tests

```bash
# Run all tests
pytest

# Run specific test module with verbose output
pytest tests/test_timing_diff.py -v

# Run with coverage report
pytest --cov=ate_smt7_diff --cov-report=term-missing
```

### Code Quality

```bash
# Linting
ruff check ate_smt7_diff/

# Formatting
ruff format ate_smt7_diff/

# Type checking
mypy ate_smt7_diff/

# Security scanning
bandit -r ate_smt7_diff/
```

### Project Conventions

- **File Size**: Keep modules under 800 lines; extract utilities when files grow too large
- **Naming**: Use descriptive names; boolean variables should use `is_`, `has_`, `should_`, or `can_` prefixes
- **Error Handling**: Handle errors explicitly; never silently swallow exceptions
- **Input Validation**: Validate at system boundaries (file parsing, CLI args)
- **Models**: All domain models live in `models/`; import from `models/__init__.py` for backward compatibility
- **Unknown Fields**: Pin/timing configs use an `extra: Dict[str, str]` to capture fields not explicitly modeled

## Testing

The test suite covers:

- **Parser Tests**: Verify correct extraction of sections from SMT7 ASCII files
- **Diff Tests**: Verify diff computation logic for each domain (flow, timing, levels, testtable, vectors, testmethod)
- **EQNSET Tests**: Verify EQNSET block parsing and diffing
- **WAVETBL Tests**: Verify wavetable block parsing and diffing
- **Filesystem Tests**: Verify FileSystem abstraction behavior

Test data is located in `tests/` and uses `pytest` patterns.

## License

MIT License. See [LICENSE](LICENSE) for details.

## Contributing

Contributions are welcome. Please ensure:

1. Tests pass (`pytest`)
2. Code is formatted (`ruff format`)
3. Linting passes (`ruff check`)
4. Type checking passes (`mypy`)
5. New features include tests (minimum 80% coverage)

## Support

For issues, questions, or feature requests, please open an issue on the project repository.
