#!/usr/bin/env python3
"""
SMT7 Program configuration loader.
Derives program root from flow file path, parses context section,
and resolves associated config file paths (timing, level, pattern, testtable, pin).
"""

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from suite_config import (
    extract_context_section,
    extract_test_suites_section,
    parse_context,
    parse_suite_config,
)


@dataclass(frozen=True)
class LevelSpec:
    """Parsed level spec entry from a SPECSET block."""
    actual: str = ""
    min: str = ""
    max: str = ""
    units: str = ""
    comment: str = ""


@dataclass
class LevelSpecDiff:
    """Level spec differences for a single test suite."""
    suite_name: str
    added: Dict[str, LevelSpec] = field(default_factory=dict)
    removed: Dict[str, LevelSpec] = field(default_factory=dict)
    changed: Dict[str, Tuple[LevelSpec, LevelSpec]] = field(default_factory=dict)

    @property
    def has_changes(self) -> bool:
        return bool(self.added or self.removed or self.changed)


@dataclass(frozen=True)
class ProgramContext:
    """Parsed context section from a flow file with resolved file paths."""
    program_root: Path
    config_file: Optional[str]      # pin config file (no subdir)
    levels_file: Optional[str]      # level file in levels/
    timing_file: Optional[str]      # timing file in timing/
    vector_file: Optional[str]      # pattern file in vectors/
    testtable_file: Optional[str]   # testtable file in testtable/

    @property
    def levels_path(self) -> Optional[Path]:
        if self.levels_file:
            return self.program_root / "levels" / self.levels_file
        return None

    @property
    def timing_path(self) -> Optional[Path]:
        if self.timing_file:
            return self.program_root / "timing" / self.timing_file
        return None

    @property
    def vector_path(self) -> Optional[Path]:
        if self.vector_file:
            return self.program_root / "vectors" / self.vector_file
        return None

    @property
    def testtable_path(self) -> Optional[Path]:
        if self.testtable_file:
            return self.program_root / "testtable" / self.testtable_file
        return None

    @property
    def config_path(self) -> Optional[Path]:
        if self.config_file:
            return self.program_root / self.config_file
        return None

    def all_paths(self) -> Dict[str, Optional[Path]]:
        """Return all resolved paths as a dict."""
        return {
            "levels": self.levels_path,
            "timing": self.timing_path,
            "vectors": self.vector_path,
            "testtable": self.testtable_path,
            "config": self.config_path,
        }


def load_program_context(flow_path: str) -> ProgramContext:
    """
    Load program context from a flow file.

    Derives program root as flow_file.parent.parent (e.g.,
    test1/example1/testflow/example1.flow -> test1/example1).
    """
    flow = Path(flow_path)
    if not flow.exists():
        raise FileNotFoundError(f"Flow file not found: {flow_path}")

    program_root = flow.parent.parent

    lines = flow.read_text(encoding="utf-8").splitlines()
    ctx_lines = extract_context_section(lines)
    ctx = parse_context(ctx_lines)

    return ProgramContext(
        program_root=program_root,
        config_file=ctx.get("context_config_file"),
        levels_file=ctx.get("context_levels_file"),
        timing_file=ctx.get("context_timing_file"),
        vector_file=ctx.get("context_vector_file"),
        testtable_file=ctx.get("context_testtable_file"),
    )


class TimingLoader:
    """Loads and indexes a timing file."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.lines: List[str] = []
        self.spec_sets: Dict[str, int] = {}  # name -> line index
        self.wavetbls: Dict[str, int] = {}   # name -> line index
        self._load()

    def _load(self) -> None:
        try:
            raw = self.path.read_text(encoding="utf-8")
        except (FileNotFoundError, PermissionError, UnicodeDecodeError) as e:
            raise ValueError(f"Failed to read timing file {self.path}: {e}") from e

        self.lines = raw.splitlines()
        for i, line in enumerate(self.lines):
            stripped = line.strip()
            # SPST TIM,,"Name",0
            if stripped.startswith("SPST TIM,,"):
                parts = stripped.split(",")
                if len(parts) >= 4:
                    name = parts[2].strip().strip('"')
                    if name:
                        self.spec_sets[name] = i
            # WAVETBL "Name"
            elif stripped.startswith("WAVETBL "):
                name = stripped[8:].strip().strip('"')
                if name:
                    self.wavetbls[name] = i

    def lookup_spec_set(self, name: str) -> Optional[int]:
        """Return line index of SPST entry for spec set name."""
        return self.spec_sets.get(name)

    def lookup_wavetbl(self, name: str) -> Optional[int]:
        """Return line index of WAVETBL entry for name."""
        return self.wavetbls.get(name)

    def extract_snippet(self, start_idx: int) -> str:
        """Extract lines from start_idx until next WAVETBL block or end."""
        if start_idx >= len(self.lines):
            return ""
        result: List[str] = []
        for line in self.lines[start_idx:]:
            if line.strip().startswith("WAVETBL ") and result:
                break
            result.append(line)
        return "\n".join(result)


class LevelLoader:
    """Loads and indexes a level file."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.lines: List[str] = []
        self.eqnsets: Dict[int, int] = {}          # eqn_index -> line index (first occurrence)
        self.eqnset_specs: Dict[Tuple[int, int], int] = {}  # (eqn_index, spec_index) -> line index
        self._load()

    def _load(self) -> None:
        try:
            raw = self.path.read_text(encoding="utf-8")
        except (FileNotFoundError, PermissionError, UnicodeDecodeError) as e:
            raise ValueError(f"Failed to read level file {self.path}: {e}") from e

        self.lines = raw.splitlines()
        current_eqn: Optional[int] = None
        for i, line in enumerate(self.lines):
            stripped = line.strip()
            # EQNSET N "Name"
            if stripped.startswith("EQNSET "):
                parts = stripped.split(None, 2)
                if len(parts) >= 2:
                    try:
                        idx = int(parts[1])
                    except ValueError:
                        continue
                    current_eqn = idx
                    if idx not in self.eqnsets:
                        self.eqnsets[idx] = i
            # SPECSET M "Name"
            elif stripped.startswith("SPECSET ") and current_eqn is not None:
                parts = stripped.split(None, 2)
                if len(parts) >= 2:
                    try:
                        spec_idx = int(parts[1])
                    except ValueError:
                        continue
                    self.eqnset_specs[(current_eqn, spec_idx)] = i

    def lookup_eqnset(self, eqn_index: int) -> Optional[int]:
        """Return line index of EQNSET entry."""
        return self.eqnsets.get(eqn_index)

    def lookup_specset(self, eqn_index: int, spec_index: int) -> Optional[int]:
        """Return line index of SPECSET entry within EQNSET."""
        return self.eqnset_specs.get((eqn_index, spec_index))

    def extract_snippet(self, start_idx: int) -> str:
        """Extract lines from start_idx until next EQNSET or end of file."""
        if start_idx >= len(self.lines):
            return ""
        result: List[str] = []
        for line in self.lines[start_idx:]:
            if line.strip().startswith("EQNSET ") and result:
                break
            result.append(line)
        return "\n".join(result)

    def parse_specs(self, specset_idx: int) -> Dict[str, LevelSpec]:
        """Parse spec lines from a SPECSET block into structured dict.

        Skips the SPECSET header and column header lines, then parses
        each spec line until the next SPECSET, EQNSET, @, or blank line.
        """
        if specset_idx >= len(self.lines):
            return {}

        result: Dict[str, LevelSpec] = {}
        in_specs = False
        units_re = re.compile(r'\[([^]]*)\]')

        for line in self.lines[specset_idx + 1:]:
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("SPECSET ") or stripped.startswith("EQNSET ") or stripped == "@":
                break
            if stripped.startswith("# SPECNAME"):
                in_specs = True
                continue
            if not in_specs:
                continue

            # Extract units from [...]
            units_match = units_re.search(line)
            units = units_match.group(1).strip() if units_match else ""
            if units_match:
                line_without_units = line[:units_match.start()]
                comment = line[units_match.end():].strip()
            else:
                line_without_units = line
                comment = ""

            parts = line_without_units.split()
            if len(parts) < 2:
                continue

            spec_name = parts[0]
            actual = parts[1] if len(parts) > 1 else ""
            min_val = parts[2] if len(parts) > 2 else ""
            max_val = parts[3] if len(parts) > 3 else ""

            result[spec_name] = LevelSpec(
                actual=actual,
                min=min_val,
                max=max_val,
                units=units,
                comment=comment,
            )

        return result


@dataclass
class SuiteConfigView:
    """Complete configuration view for a single test suite."""
    suite_name: str
    flow_config: Dict[str, str]
    timing_spec_set: Optional[str]
    level_eqn_set: Optional[int]
    level_spec_set: Optional[int]
    level_levset: Optional[int]
    timing_snippet: Optional[str]
    level_snippet: Optional[str]
    level_specs: Optional[Dict[str, LevelSpec]]


def build_suite_views(
    flow_path: str,
    common_suites: Set[str],
) -> Dict[str, SuiteConfigView]:
    """
    Build SuiteConfigView for each common suite.

    Loads program context, parses test_suites, and extracts relevant
    timing/level snippets based on override indices.
    """
    ctx = load_program_context(flow_path)

    # Load timing/level files if declared
    timing_loader: Optional[TimingLoader] = None
    if ctx.timing_path and ctx.timing_path.exists():
        timing_loader = TimingLoader(ctx.timing_path)

    level_loader: Optional[LevelLoader] = None
    if ctx.levels_path and ctx.levels_path.exists():
        level_loader = LevelLoader(ctx.levels_path)

    # Parse test_suites from flow file
    flow_lines = Path(flow_path).read_text(encoding="utf-8").splitlines()
    ts_lines = extract_test_suites_section(flow_lines)
    suite_configs = parse_suite_config(ts_lines)

    views: Dict[str, SuiteConfigView] = {}
    for suite_name in sorted(common_suites):
        cfg = suite_configs.get(suite_name, {})

        # Resolve timing spec set
        timing_spec: Optional[str] = None
        tim_raw = cfg.get("override_tim_spec_set")
        if tim_raw:
            # Strip quotes if present
            timing_spec = tim_raw.strip('"')

        # Resolve level indices
        level_eqn: Optional[int] = None
        lev_eqn_raw = cfg.get("override_lev_equ_set")
        if lev_eqn_raw:
            try:
                level_eqn = int(lev_eqn_raw)
            except ValueError:
                logging.warning(
                    "Invalid override_lev_equ_set '%s' for suite %s",
                    lev_eqn_raw, suite_name,
                )

        level_spec: Optional[int] = None
        lev_spec_raw = cfg.get("override_lev_spec_set")
        if lev_spec_raw:
            try:
                level_spec = int(lev_spec_raw)
            except ValueError:
                logging.warning(
                    "Invalid override_lev_spec_set '%s' for suite %s",
                    lev_spec_raw, suite_name,
                )

        level_levset: Optional[int] = None
        levset_raw = cfg.get("override_levset")
        if levset_raw:
            try:
                level_levset = int(levset_raw)
            except ValueError:
                logging.warning(
                    "Invalid override_levset '%s' for suite %s",
                    levset_raw, suite_name,
                )

        # Extract timing snippet
        timing_snippet: Optional[str] = None
        if timing_loader and timing_spec:
            wavetbl_idx = timing_loader.lookup_wavetbl(timing_spec)
            if wavetbl_idx is not None:
                timing_snippet = timing_loader.extract_snippet(wavetbl_idx)

        # Extract level snippet
        level_snippet: Optional[str] = None
        if level_loader and level_eqn is not None and level_spec is not None:
            spec_idx = level_loader.lookup_specset(level_eqn, level_spec)
            if spec_idx is not None:
                level_snippet = level_loader.extract_snippet(spec_idx)
            else:
                # Fallback to EQNSET block
                eqn_idx = level_loader.lookup_eqnset(level_eqn)
                if eqn_idx is not None:
                    level_snippet = level_loader.extract_snippet(eqn_idx)

        # Parse level specs from SPECSET block
        # NOTE: override_levset maps to LEVELSET (front section of level file),
        #       not EQNSET. SPECSET lookup must use override_lev_equ_set (level_eqn).
        level_specs: Optional[Dict[str, LevelSpec]] = None
        if level_loader and level_eqn is not None and level_spec is not None:
            spec_idx = level_loader.lookup_specset(level_eqn, level_spec)
            if spec_idx is not None:
                level_specs = level_loader.parse_specs(spec_idx)

        views[suite_name] = SuiteConfigView(
            suite_name=suite_name,
            flow_config=cfg,
            timing_spec_set=timing_spec,
            level_eqn_set=level_eqn,
            level_spec_set=level_spec,
            level_levset=level_levset,
            timing_snippet=timing_snippet,
            level_snippet=level_snippet,
            level_specs=level_specs,
        )

    return views


def diff_level_specs(
    suite_name: str,
    old_specs: Optional[Dict[str, LevelSpec]],
    new_specs: Optional[Dict[str, LevelSpec]],
) -> Optional[LevelSpecDiff]:
    """Compute level spec differences between two spec dictionaries."""
    if old_specs is None and new_specs is None:
        return None

    if old_specs is None:
        return LevelSpecDiff(suite_name=suite_name, added=new_specs or {})

    if new_specs is None:
        return LevelSpecDiff(suite_name=suite_name, removed=old_specs)

    old_keys = set(old_specs.keys())
    new_keys = set(new_specs.keys())

    added = {k: new_specs[k] for k in new_keys - old_keys}
    removed = {k: old_specs[k] for k in old_keys - new_keys}
    changed = {}
    for k in old_keys & new_keys:
        old_s = old_specs[k]
        new_s = new_specs[k]
        if (
            old_s.actual != new_s.actual
            or old_s.min != new_s.min
            or old_s.max != new_s.max
            or old_s.units != new_s.units
            or old_s.comment != new_s.comment
        ):
            changed[k] = (old_s, new_s)

    return LevelSpecDiff(
        suite_name=suite_name,
        added=added,
        removed=removed,
        changed=changed,
    )
