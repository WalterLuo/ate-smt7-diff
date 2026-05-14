#!/usr/bin/env python3
"""
Timing file parser.
Loads and indexes timing files for WAVETBL, SPST, SPECIFICATION,
and EQSP TIM,SPS region lookups.
"""

import re

from ate_smt7_diff.filesystem import FileSystem, RealFileSystem
from ate_smt7_diff.models import (
    TimingEqnSetBlock,
    TimingPinConfig,
    TimingSetConfig,
    TimingSpec,
    WaveTblBlock,
)
from ate_smt7_diff.parsers.timing_parser_eqnset import (
    extract_wavetbl_name_from_eqnset,
    parse_eqsp_eqnset_block,
)
from ate_smt7_diff.parsers.timing_parser_pins import parse_pins_group, parse_timingset
from ate_smt7_diff.parsers.timing_parser_spec import (
    extract_wavetbl_names_from_specification,
    parse_specification_all_eqnsets,
    parse_specification_eqnset_index,
    parse_specification_specs,
)
from ate_smt7_diff.parsers.timing_parser_wavetbl import parse_wavetbl


class TimingLoader:
    """Loads and indexes a timing file."""

    def __init__(self, path: str, fs: FileSystem | None = None) -> None:
        self.path = path
        self._fs = fs or RealFileSystem()
        self.lines: list[str] = []
        self.spec_sets: dict[str, int] = {}  # SPST TIM,,name -> line index
        self.wavetbls: dict[str, int] = {}  # WAVETBL name -> line index
        self.specifications: dict[str, int] = {}  # SPECIFICATION "name" -> line index
        self.eqsp_tim_eqnsets: dict[int, int] = {}  # EQNSET index -> line index (in EQSP TIM,SPS)
        self.eqsp_tim_specsets: dict[tuple[int, int], int] = {}  # (eqn, spec) -> line index
        self._load()

    def _load(self) -> None:
        if not self.lines:
            try:
                raw = self._fs.read_text(self.path, encoding="utf-8")
            except (FileNotFoundError, PermissionError, UnicodeDecodeError) as e:
                raise ValueError(f"Failed to read timing file {self.path}: {e}") from e
            self.lines = raw.splitlines()

        in_eqsp_tim = False
        in_eqsp_wvt = False
        current_eqn: int | None = None

        for i, line in enumerate(self.lines):
            stripped = line.strip()

            # SPST TIM,, entries
            if stripped.startswith("SPST TIM,,"):
                parts = stripped.split(",")
                if len(parts) >= 4:
                    name = parts[2].strip().strip('"')
                    if name:
                        self.spec_sets[name] = i

            # WAVETBL entries - index standalone definitions
            elif stripped.startswith("WAVETBL "):
                name = stripped[8:].split("#", 1)[0].strip().strip('"')
                if name and name not in self.wavetbls:
                    self.wavetbls[name] = i

            # WAVETBL entries inside EQSP TIM,WVT region (same-line format)
            elif in_eqsp_wvt and "WAVETBL " in stripped:
                match = re.search(r'WAVETBL\s+"([^"]*)"', stripped)
                if match:
                    name = match.group(1)
                    if name and name not in self.wavetbls:
                        self.wavetbls[name] = i

            # SPECIFICATION entries (Port Spec mode)
            elif stripped.startswith('SPECIFICATION "'):
                name = stripped[15:].strip().strip('"')
                if name:
                    self.specifications[name] = i

            # EQSP TIM,EQN / EQSP TIM,SPS region entry
            elif stripped.startswith("EQSP TIM,EQN") or stripped.startswith("EQSP TIM,SPS"):
                in_eqsp_tim = True
                in_eqsp_wvt = False
                current_eqn = None

            # EQSP TIM,WVT region entry
            elif stripped.startswith("EQSP TIM,WVT"):
                in_eqsp_wvt = True
                in_eqsp_tim = False
                current_eqn = None
                # Also extract WAVETBL if it's on the same line
                match = re.search(r'WAVETBL\s+"([^"]*)"', stripped)
                if match:
                    name = match.group(1)
                    if name and name not in self.wavetbls:
                        self.wavetbls[name] = i

            # EQSP region exit
            elif stripped.startswith("EQSP TIM,END") or stripped == "@":
                in_eqsp_tim = False
                in_eqsp_wvt = False
                current_eqn = None

            # EQNSET within EQSP TIM,EQN or EQSP TIM,SPS
            elif in_eqsp_tim and stripped.startswith("EQNSET "):
                parts = stripped.split(None, 2)
                if len(parts) >= 2:
                    try:
                        idx = int(parts[1])
                    except ValueError:
                        continue
                    current_eqn = idx
                    # Prefer EQSP TIM,EQN over EQSP TIM,SPS (don't overwrite)
                    if idx not in self.eqsp_tim_eqnsets:
                        self.eqsp_tim_eqnsets[idx] = i

            # SPECSET within EQSP TIM,SPS
            elif in_eqsp_tim and stripped.startswith("SPECSET ") and current_eqn is not None:
                parts = stripped.split(None, 2)
                if len(parts) >= 2:
                    try:
                        spec_idx = int(parts[1])
                    except ValueError:
                        continue
                    self.eqsp_tim_specsets[(current_eqn, spec_idx)] = i

    # --- Lookup methods ---

    def lookup_spec_set(self, name: str) -> int | None:
        """Return line index of SPST entry for spec set name."""
        return self.spec_sets.get(name)

    def lookup_wavetbl(self, name: str) -> int | None:
        """Return line index of WAVETBL entry for name."""
        return self.wavetbls.get(name)

    def lookup_specification(self, name: str) -> int | None:
        """Return line index of SPECIFICATION entry for name."""
        return self.specifications.get(name)

    def lookup_eqsp_eqnset(self, eqn_index: int) -> int | None:
        """Return line index of EQNSET in EQSP TIM,SPS region."""
        return self.eqsp_tim_eqnsets.get(eqn_index)

    def lookup_eqsp_specset(self, eqn_index: int, spec_index: int) -> int | None:
        """Return line index of SPECSET within EQNSET in EQSP TIM,SPS region."""
        return self.eqsp_tim_specsets.get((eqn_index, spec_index))

    # --- Extraction methods ---

    def extract_snippet(self, start_idx: int) -> str:
        """Extract lines from start_idx until next major block or end."""
        if start_idx >= len(self.lines):
            return ""
        result: list[str] = []

        # Detect braced blocks (e.g. SPECIFICATION "NAME" { ... })
        depth = 0
        if start_idx + 1 < len(self.lines) and self.lines[start_idx + 1].strip() == "{":
            depth = 1
            result.append(self.lines[start_idx])
            result.append(self.lines[start_idx + 1])
            loop_start = start_idx + 2
        else:
            result.append(self.lines[start_idx])
            loop_start = start_idx + 1

        for line in self.lines[loop_start:]:
            s = line.strip()
            if s == "{":
                depth += 1
                result.append(line)
                continue
            if s == "}":
                depth -= 1
                result.append(line)
                if depth <= 0:
                    break
                continue
            if depth <= 0 and (
                s.startswith("WAVETBL ")
                or s.startswith("SPST TIM,,")
                or s.startswith('SPECIFICATION "')
                or s.startswith("EQNSET ")
                or s.startswith("EQSP TIM,END")
                or s == "@"
            ):
                break
            result.append(line)
        return "\n".join(result)

    def extract_eqsp_snippet(self, start_idx: int) -> str:
        """Extract lines from start_idx until next EQNSET or EQSP end."""
        if start_idx >= len(self.lines):
            return ""
        result: list[str] = []
        for line in self.lines[start_idx:]:
            s = line.strip()
            if result and (s.startswith("EQNSET ") or s.startswith("EQSP TIM,END") or s == "@"):
                break
            result.append(line)
        return "\n".join(result)

    # --- Parsing delegators ---

    def parse_specification_specs(self, spec_idx: int) -> dict[str, TimingSpec]:
        """Parse a SPECIFICATION block into Dict[str, TimingSpec]."""
        return parse_specification_specs(self.lines, spec_idx)

    def parse_pins_group(self, pins_idx: int) -> TimingPinConfig:
        """Parse a PINS block into TimingPinConfig."""
        return parse_pins_group(self.lines, pins_idx)

    def parse_timingset(self, ts_idx: int) -> TimingSetConfig | None:
        """Parse a TIMINGSET block into TimingSetConfig."""
        return parse_timingset(self.lines, ts_idx)

    def parse_specification_eqnset_index(self, spec_idx: int) -> int | None:
        """Extract the first EQNSET index from a SPECIFICATION block."""
        return parse_specification_eqnset_index(self.lines, spec_idx)

    def parse_specification_all_eqnsets(self, spec_idx: int) -> list[tuple[int, str]]:
        """Extract all EQNSET (index, name) pairs from a SPECIFICATION block."""
        return parse_specification_all_eqnsets(self.lines, spec_idx)

    def parse_eqsp_eqnset_block(self, eqnset_idx: int) -> TimingEqnSetBlock | None:
        """Parse an EQNSET block from the EQSP TIM,SPS region."""
        return parse_eqsp_eqnset_block(self.lines, eqnset_idx)

    def parse_wavetbl(self, wavetbl_idx: int) -> WaveTblBlock | None:
        """Parse a WAVETBL block into WaveTblBlock."""
        return parse_wavetbl(self.lines, wavetbl_idx)

    def extract_wavetbl_name_from_eqnset(self, eqnset_idx: int) -> str | None:
        """Extract WAVETBL name from an EQNSET block."""
        return extract_wavetbl_name_from_eqnset(self.lines, eqnset_idx)

    def extract_wavetbl_names_from_specification(self, spec_idx: int) -> list[str]:
        """Extract all WAVETBL names from a SPECIFICATION block."""
        return extract_wavetbl_names_from_specification(self.lines, spec_idx)
