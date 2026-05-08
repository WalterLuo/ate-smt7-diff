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


@dataclass(frozen=True)
class DpsPinConfig:
    """Parsed DPSPINS entry from an EQNSET block.

    Known fields are exposed as attributes; any unknown fields
    discovered during parsing are stored in ``extra``.
    """
    vout: str = ""
    ilimit: str = ""
    t_ms: str = ""
    vout_frc_rng: str = ""
    iout_clamp_rng: str = ""
    offcurr: str = ""
    extra: Dict[str, str] = field(default_factory=dict)

    def all_fields(self) -> Dict[str, str]:
        """Return all non-empty fields (known + extra) as a flat dict."""
        result: Dict[str, str] = {}
        for key in ("vout", "ilimit", "t_ms", "vout_frc_rng", "iout_clamp_rng", "offcurr"):
            val = getattr(self, key)
            if val:
                result[key] = val
        result.update(self.extra)
        return result


@dataclass(frozen=True)
class LevelSetPinConfig:
    """Parsed PINS entry within a LEVELSET block.

    Known fields are exposed as attributes; any unknown fields
    discovered during parsing are stored in ``extra``.
    """
    vih: str = ""
    vil: str = ""
    voh: str = ""
    vol: str = ""
    extra: Dict[str, str] = field(default_factory=dict)

    def all_fields(self) -> Dict[str, str]:
        """Return all non-empty fields (known + extra) as a flat dict."""
        result: Dict[str, str] = {}
        for key in ("vih", "vil", "voh", "vol"):
            val = getattr(self, key)
            if val:
                result[key] = val
        result.update(self.extra)
        return result


@dataclass(frozen=True)
class EqnSetBlock:
    """Parsed EQNSET block from the EQSP LEV,EQN region."""
    eqnset_index: int
    eqnset_name: str
    specs: Dict[str, LevelSpec] = field(default_factory=dict)
    dpspins: Dict[str, DpsPinConfig] = field(default_factory=dict)
    levelsets: Dict[int, Dict[str, LevelSetPinConfig]] = field(default_factory=dict)


@dataclass(frozen=True)
class EqnSetDiff:
    """Diff result for an EQNSET block comparison."""
    suite_name: str
    eqnset_index: int
    eqnset_name: str
    dpspins_added: Dict[str, DpsPinConfig] = field(default_factory=dict)
    dpspins_removed: Dict[str, DpsPinConfig] = field(default_factory=dict)
    dpspins_changed: Dict[str, Tuple[DpsPinConfig, DpsPinConfig]] = field(default_factory=dict)
    levelsets_added: Dict[int, Dict[str, LevelSetPinConfig]] = field(default_factory=dict)
    levelsets_removed: Dict[int, Dict[str, LevelSetPinConfig]] = field(default_factory=dict)
    levelsets_changed: Dict[int, Dict[str, Tuple[LevelSetPinConfig, LevelSetPinConfig]]] = field(default_factory=dict)

    @property
    def has_changes(self) -> bool:
        return bool(
            self.dpspins_added or self.dpspins_removed or self.dpspins_changed
            or self.levelsets_added or self.levelsets_removed or self.levelsets_changed
        )


@dataclass(frozen=True)
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

    def parse_dpspins(self, dpspins_idx: int) -> DpsPinConfig:
        """Parse a DPSPINS block into DpsPinConfig.

        Reads lines from dpspins_idx + 1 until the next DPSPINS,
        LEVELSET, EQNSET, '@', or blank line.
        """
        if dpspins_idx >= len(self.lines):
            return DpsPinConfig()

        fields: Dict[str, str] = {}
        for line in self.lines[dpspins_idx + 1:]:
            stripped = line.strip()
            if not stripped:
                continue
            if (
                stripped.startswith("DPSPINS ")
                or stripped.startswith("LEVELSET ")
                or stripped.startswith("EQNSET ")
                or stripped.startswith("SPECSET ")
                or stripped == "@"
            ):
                break
            if "=" not in stripped:
                continue
            key, val = stripped.split("=", 1)
            key = key.strip()
            val = val.strip()
            # Strip inline comments
            if "#" in val:
                val = val.split("#", 1)[0].strip()
            fields[key] = val

        known = {"vout", "ilimit", "t_ms", "vout_frc_rng", "iout_clamp_rng", "offcurr"}
        extra = {k: v for k, v in fields.items() if k not in known}
        return DpsPinConfig(
            vout=fields.get("vout", ""),
            ilimit=fields.get("ilimit", ""),
            t_ms=fields.get("t_ms", ""),
            vout_frc_rng=fields.get("vout_frc_rng", ""),
            iout_clamp_rng=fields.get("iout_clamp_rng", ""),
            offcurr=fields.get("offcurr", ""),
            extra=extra,
        )

    def parse_levelset(self, levelset_idx: int) -> Dict[str, LevelSetPinConfig]:
        """Parse a LEVELSET block into dict of PINS group -> LevelSetPinConfig.

        Reads lines from levelset_idx + 1 until the next LEVELSET,
        EQNSET, '@', or end.
        """
        if levelset_idx >= len(self.lines):
            return {}

        result: Dict[str, LevelSetPinConfig] = {}
        current_pins: Optional[str] = None
        current_fields: Dict[str, str] = {}

        def flush_pins() -> None:
            nonlocal current_pins, current_fields
            if current_pins is not None:
                known = {"vih", "vil", "voh", "vol"}
                extra = {k: v for k, v in current_fields.items() if k not in known}
                result[current_pins] = LevelSetPinConfig(
                    vih=current_fields.get("vih", ""),
                    vil=current_fields.get("vil", ""),
                    voh=current_fields.get("voh", ""),
                    vol=current_fields.get("vol", ""),
                    extra=extra,
                )
            current_pins = None
            current_fields = {}

        for line in self.lines[levelset_idx + 1:]:
            stripped = line.strip()
            if not stripped:
                continue
            if (
                stripped.startswith("LEVELSET ")
                or stripped.startswith("EQNSET ")
                or stripped.startswith("SPECSET ")
                or stripped == "@"
            ):
                break
            if stripped.startswith("PINS "):
                flush_pins()
                # Extract pin names after "PINS "
                pins_part = stripped[5:]
                # Strip inline comments
                if "#" in pins_part:
                    pins_part = pins_part.split("#", 1)[0]
                current_pins = pins_part.strip()
                continue
            if current_pins is None:
                continue
            if "=" not in stripped:
                continue
            key, val = stripped.split("=", 1)
            key = key.strip()
            val = val.strip()
            if "#" in val:
                val = val.split("#", 1)[0].strip()
            current_fields[key] = val

        flush_pins()
        return result

    def parse_eqnset_block(self, eqnset_idx: int) -> Optional[EqnSetBlock]:
        """Parse an EQNSET block from the EQSP LEV,EQN region.

        Parses SPECS, DPSPINS, and LEVELSET sub-blocks.
        Returns None if eqnset_idx is out of range or header is malformed.
        """
        if eqnset_idx >= len(self.lines):
            return None

        header = self.lines[eqnset_idx].strip()
        if not header.startswith("EQNSET "):
            return None

        parts = header.split(None, 2)
        if len(parts) < 2:
            return None
        try:
            eqnset_index = int(parts[1])
        except ValueError:
            return None

        eqnset_name = ""
        if len(parts) >= 3:
            eqnset_name = parts[2].strip().strip('"')

        specs: Dict[str, LevelSpec] = {}
        dpspins: Dict[str, DpsPinConfig] = {}
        levelsets: Dict[int, Dict[str, LevelSetPinConfig]] = {}

        i = eqnset_idx + 1
        while i < len(self.lines):
            line = self.lines[i]
            stripped = line.strip()
            if not stripped:
                i += 1
                continue
            if stripped.startswith("EQNSET ") or stripped == "@":
                break
            if stripped.startswith("SPECS"):
                # Parse specs list: Name  [UNIT]
                i += 1
                while i < len(self.lines):
                    spec_line = self.lines[i].strip()
                    if not spec_line:
                        i += 1
                        continue
                    if (
                        spec_line.startswith("EQNSET ")
                        or spec_line.startswith("DPSPINS ")
                        or spec_line.startswith("LEVELSET ")
                        or spec_line.startswith("SPECSET ")
                        or spec_line == "@"
                    ):
                        break
                    # Parse spec entry
                    units_match = re.search(r'\[([^]]*)\]', spec_line)
                    units = units_match.group(1).strip() if units_match else ""
                    if units_match:
                        line_without_units = spec_line[:units_match.start()]
                    else:
                        line_without_units = spec_line
                    spec_parts = line_without_units.split()
                    if len(spec_parts) >= 1:
                        spec_name = spec_parts[0]
                        specs[spec_name] = LevelSpec(units=units)
                    i += 1
                continue
            if stripped.startswith("DPSPINS "):
                pin_name = stripped.split(None, 1)[1].strip()
                dpspins[pin_name] = self.parse_dpspins(i)
                i += 1
                continue
            if stripped.startswith("LEVELSET "):
                levelset_parts = stripped.split(None, 2)
                if len(levelset_parts) >= 2:
                    try:
                        levelset_index = int(levelset_parts[1])
                    except ValueError:
                        levelset_index = 0
                else:
                    levelset_index = 0
                levelsets[levelset_index] = self.parse_levelset(i)
                i += 1
                continue
            i += 1

        return EqnSetBlock(
            eqnset_index=eqnset_index,
            eqnset_name=eqnset_name,
            specs=specs,
            dpspins=dpspins,
            levelsets=levelsets,
        )


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
    eqnset_block: Optional[EqnSetBlock] = None


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

        # Parse EQNSET block (DPSPINS + LEVELSET from EQSP LEV,EQN region)
        eqnset_block: Optional[EqnSetBlock] = None
        if level_loader and level_eqn is not None:
            eqn_idx = level_loader.lookup_eqnset(level_eqn)
            if eqn_idx is not None:
                eqnset_block = level_loader.parse_eqnset_block(eqn_idx)

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
            eqnset_block=eqnset_block,
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


def _diff_levelset_pins(
    old_pins: Dict[str, LevelSetPinConfig],
    new_pins: Dict[str, LevelSetPinConfig],
) -> Dict[str, Tuple[LevelSetPinConfig, LevelSetPinConfig]]:
    """Compare PINS groups within a single LEVELSET."""
    return {
        name: (old_pins[name], new_pins[name])
        for name in set(old_pins.keys()) & set(new_pins.keys())
        if old_pins[name] != new_pins[name]
    }


def diff_eqnset_blocks(
    suite_name: str,
    old_block: Optional[EqnSetBlock],
    new_block: Optional[EqnSetBlock],
) -> Optional[EqnSetDiff]:
    """Compute EQNSET block differences between two program versions."""
    if old_block is None and new_block is None:
        return None

    if old_block is None:
        return EqnSetDiff(
            suite_name=suite_name,
            eqnset_index=new_block.eqnset_index if new_block else 0,
            eqnset_name=new_block.eqnset_name if new_block else "",
            dpspins_added=new_block.dpspins if new_block else {},
            levelsets_added=new_block.levelsets if new_block else {},
        )

    if new_block is None:
        return EqnSetDiff(
            suite_name=suite_name,
            eqnset_index=old_block.eqnset_index,
            eqnset_name=old_block.eqnset_name,
            dpspins_removed=old_block.dpspins,
            levelsets_removed=old_block.levelsets,
        )

    # DPSPINS diff
    old_dps_keys = set(old_block.dpspins.keys())
    new_dps_keys = set(new_block.dpspins.keys())
    dpspins_added = {k: new_block.dpspins[k] for k in new_dps_keys - old_dps_keys}
    dpspins_removed = {k: old_block.dpspins[k] for k in old_dps_keys - new_dps_keys}
    dpspins_changed = {
        k: (old_block.dpspins[k], new_block.dpspins[k])
        for k in old_dps_keys & new_dps_keys
        if old_block.dpspins[k] != new_block.dpspins[k]
    }

    # LEVELSET diff
    old_ls_keys = set(old_block.levelsets.keys())
    new_ls_keys = set(new_block.levelsets.keys())
    levelsets_added = {k: new_block.levelsets[k] for k in new_ls_keys - old_ls_keys}
    levelsets_removed = {k: old_block.levelsets[k] for k in old_ls_keys - new_ls_keys}
    levelsets_changed: Dict[int, Dict[str, Tuple[LevelSetPinConfig, LevelSetPinConfig]]] = {}
    for k in old_ls_keys & new_ls_keys:
        old_pins = old_block.levelsets[k]
        new_pins = new_block.levelsets[k]
        pin_diff = _diff_levelset_pins(old_pins, new_pins)
        # Also include added/removed pins within the same levelset as changed
        old_pin_keys = set(old_pins.keys())
        new_pin_keys = set(new_pins.keys())
        for pk in new_pin_keys - old_pin_keys:
            pin_diff[pk] = (LevelSetPinConfig(), new_pins[pk])
        for pk in old_pin_keys - new_pin_keys:
            pin_diff[pk] = (old_pins[pk], LevelSetPinConfig())
        if pin_diff:
            levelsets_changed[k] = pin_diff

    return EqnSetDiff(
        suite_name=suite_name,
        eqnset_index=old_block.eqnset_index,
        eqnset_name=old_block.eqnset_name,
        dpspins_added=dpspins_added,
        dpspins_removed=dpspins_removed,
        dpspins_changed=dpspins_changed,
        levelsets_added=levelsets_added,
        levelsets_removed=levelsets_removed,
        levelsets_changed=levelsets_changed,
    )
