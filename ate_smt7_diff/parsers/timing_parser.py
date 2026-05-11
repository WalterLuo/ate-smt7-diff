#!/usr/bin/env python3
"""
Timing file parser.
Loads and indexes timing files for WAVETBL, SPST, SPECIFICATION,
and EQSP TIM,SPS region lookups.
"""

import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from ate_smt7_diff.models import (
    TimingEqnSetBlock,
    TimingPinConfig,
    TimingSetConfig,
    TimingSpec,
    WaveTblBlock,
    WaveTblPinsGroup,
    WaveTblRow,
)


class TimingLoader:
    """Loads and indexes a timing file."""

    def __init__(self, path: str) -> None:
        self.path = path
        self.lines: List[str] = []
        self.spec_sets: Dict[str, int] = {}      # SPST TIM,,name -> line index
        self.wavetbls: Dict[str, int] = {}       # WAVETBL name -> line index
        self.specifications: Dict[str, int] = {}  # SPECIFICATION "name" -> line index
        self.eqsp_tim_eqnsets: Dict[int, int] = {}  # EQNSET index -> line index (in EQSP TIM,SPS)
        self.eqsp_tim_specsets: Dict[Tuple[int, int], int] = {}  # (eqn, spec) -> line index
        self._load()

    def _load(self) -> None:
        if not self.lines:
            try:
                raw = Path(self.path).read_text(encoding="utf-8")
            except (FileNotFoundError, PermissionError, UnicodeDecodeError) as e:
                raise ValueError(f"Failed to read timing file {self.path}: {e}") from e
            self.lines = raw.splitlines()

        in_eqsp_tim = False
        in_eqsp_wvt = False
        current_eqn: Optional[int] = None

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

    def lookup_spec_set(self, name: str) -> Optional[int]:
        """Return line index of SPST entry for spec set name."""
        return self.spec_sets.get(name)

    def lookup_wavetbl(self, name: str) -> Optional[int]:
        """Return line index of WAVETBL entry for name."""
        return self.wavetbls.get(name)

    def lookup_specification(self, name: str) -> Optional[int]:
        """Return line index of SPECIFICATION entry for name."""
        return self.specifications.get(name)

    def lookup_eqsp_eqnset(self, eqn_index: int) -> Optional[int]:
        """Return line index of EQNSET in EQSP TIM,SPS region."""
        return self.eqsp_tim_eqnsets.get(eqn_index)

    def lookup_eqsp_specset(self, eqn_index: int, spec_index: int) -> Optional[int]:
        """Return line index of SPECSET within EQNSET in EQSP TIM,SPS region."""
        return self.eqsp_tim_specsets.get((eqn_index, spec_index))

    # --- Extraction methods ---

    def extract_snippet(self, start_idx: int) -> str:
        """Extract lines from start_idx until next major block or end."""
        if start_idx >= len(self.lines):
            return ""
        result: List[str] = []

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
        result: List[str] = []
        for line in self.lines[start_idx:]:
            s = line.strip()
            if result and (
                s.startswith("EQNSET ")
                or s.startswith("EQSP TIM,END")
                or s == "@"
            ):
                break
            result.append(line)
        return "\n".join(result)

    # --- Parsing methods ---

    def parse_specification_specs(self, spec_idx: int) -> Dict[str, TimingSpec]:
        """Parse a SPECIFICATION block into Dict[str, TimingSpec]."""
        if spec_idx >= len(self.lines):
            return {}

        result: Dict[str, TimingSpec] = {}
        units_re = re.compile(r'\[([^]]*)\]')

        depth = 0
        start = spec_idx + 1
        if start < len(self.lines) and self.lines[start].strip() == "{":
            depth = 1
            start += 1

        context = ""

        for line in self.lines[start:]:
            stripped = line.strip()
            if not stripped:
                continue

            if stripped == "{":
                depth += 1
                continue
            if stripped == "}":
                depth -= 1
                if depth <= 0:
                    break
                continue

            if depth <= 0 and (
                stripped.startswith('SPECIFICATION "')
                or stripped.startswith("EQSP TIM,END")
                or stripped == "@"
            ):
                break

            # Update context from structural lines
            if stripped.startswith("EQNSET "):
                parts = stripped.split(None, 2)
                if len(parts) >= 3:
                    context = parts[2].strip().strip('"')
                continue
            if stripped.startswith("WAVETBL "):
                context = stripped[8:].strip().strip('"')
                continue
            if stripped.startswith("PORT "):
                parts = stripped.split(None, 1)
                if len(parts) >= 2:
                    context = parts[1].strip().strip('"')
                continue

            # Skip other structural / comment lines
            if stripped.startswith((
                "SYNC", "CHECK ", "SPST TIM,,", 'SPECIFICATION "',
                "EQSP TIM,END", "@", "#",
            )):
                continue

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
            value = parts[1] if len(parts) > 1 else ""

            if context:
                key = f"{context}/{spec_name}"
            else:
                key = spec_name

            result[key] = TimingSpec(
                value=value,
                units=units,
                comment=comment,
            )

        return result

    def parse_pins_group(self, pins_idx: int) -> TimingPinConfig:
        """Parse a PINS block into TimingPinConfig."""
        if pins_idx >= len(self.lines):
            return TimingPinConfig()

        fields: Dict[str, str] = {}
        for line in self.lines[pins_idx + 1:]:
            stripped = line.strip()
            if not stripped:
                continue
            if (
                stripped.startswith("PINS ")
                or stripped.startswith("TIMINGSET ")
                or stripped.startswith("SPECSET ")
                or stripped.startswith("EQNSET ")
                or stripped.startswith("EQSP TIM,END")
                or stripped == "@"
            ):
                break
            if "=" not in stripped:
                continue
            key, val = stripped.split("=", 1)
            key = key.strip()
            val = val.strip()
            if "#" in val:
                val = val.split("#", 1)[0].strip()
            fields[key] = val

        known = {"d1", "d2", "d3", "r1", "r2", "r3"}
        extra = {k: v for k, v in fields.items() if k not in known}
        return TimingPinConfig(
            d1=fields.get("d1", ""),
            d2=fields.get("d2", ""),
            d3=fields.get("d3", ""),
            r1=fields.get("r1", ""),
            r2=fields.get("r2", ""),
            r3=fields.get("r3", ""),
            extra=extra,
        )

    def parse_timingset(self, ts_idx: int) -> Optional[TimingSetConfig]:
        """Parse a TIMINGSET block into TimingSetConfig."""
        if ts_idx >= len(self.lines):
            return None

        header = self.lines[ts_idx].strip()
        if not header.startswith("TIMINGSET "):
            return None

        parts = header.split(None, 2)
        if len(parts) < 2:
            return None
        try:
            index = int(parts[1])
        except ValueError:
            return None

        name = ""
        if len(parts) >= 3:
            name = parts[2].strip().strip('"')

        period = ""
        extra: Dict[str, str] = {}
        for line in self.lines[ts_idx + 1:]:
            stripped = line.strip()
            if not stripped:
                continue
            if (
                stripped.startswith("PINS ")
                or stripped.startswith("TIMINGSET ")
                or stripped.startswith("SPECSET ")
                or stripped.startswith("EQNSET ")
                or stripped.startswith("EQSP TIM,END")
                or stripped == "@"
            ):
                break
            if "=" not in stripped:
                continue
            key, val = stripped.split("=", 1)
            key = key.strip()
            val = val.strip()
            if "#" in val:
                val = val.split("#", 1)[0].strip()
            if key == "period":
                period = val
            else:
                extra[key] = val

        return TimingSetConfig(
            index=index,
            name=name,
            period=period,
            extra=extra,
        )

    def parse_specification_eqnset_index(self, spec_idx: int) -> Optional[int]:
        """Extract the first EQNSET index from a SPECIFICATION block."""
        eqnsets = self.parse_specification_all_eqnsets(spec_idx)
        return eqnsets[0][0] if eqnsets else None

    def parse_specification_all_eqnsets(self, spec_idx: int) -> List[Tuple[int, str]]:
        """Extract all EQNSET (index, name) pairs from a SPECIFICATION block."""
        if spec_idx >= len(self.lines):
            return []

        result: List[Tuple[int, str]] = []
        depth = 0
        start = spec_idx + 1
        if start < len(self.lines) and self.lines[start].strip() == "{":
            depth = 1
            start += 1

        for line in self.lines[start:]:
            stripped = line.strip()
            if not stripped:
                continue
            if stripped == "{":
                depth += 1
                continue
            if stripped == "}":
                depth -= 1
                if depth <= 0:
                    break
                continue
            if depth <= 0 and (
                stripped.startswith('SPECIFICATION "')
                or stripped.startswith("EQSP TIM,END")
                or stripped == "@"
            ):
                break
            if stripped.startswith("EQNSET "):
                parts = stripped.split(None, 2)
                if len(parts) >= 2:
                    try:
                        idx = int(parts[1])
                    except ValueError:
                        continue
                    name = ""
                    if len(parts) >= 3:
                        name = parts[2].strip().strip('"')
                    result.append((idx, name))

        return result

    def parse_eqsp_eqnset_block(self, eqnset_idx: int) -> Optional[TimingEqnSetBlock]:
        """Parse an EQNSET block from the EQSP TIM,SPS region."""
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

        specs: Dict[str, TimingSpec] = {}
        specset_index = 0
        specset_name = ""

        i = eqnset_idx + 1
        while i < len(self.lines):
            line = self.lines[i]
            stripped = line.strip()
            if not stripped:
                i += 1
                continue
            if stripped.startswith("EQNSET ") or stripped.startswith("EQSP TIM,END") or stripped == "@":
                break
            if stripped.startswith("SPECSET "):
                spec_parts = stripped.split(None, 2)
                if len(spec_parts) >= 2:
                    try:
                        specset_index = int(spec_parts[1])
                    except ValueError:
                        pass
                if len(spec_parts) >= 3:
                    specset_name = spec_parts[2].strip().strip('"')
                i += 1
                continue
            if stripped == "SPECS" or stripped.startswith("# SPECNAME") or stripped.startswith("#SPECNAME"):
                i += 1
                while i < len(self.lines):
                    spec_line = self.lines[i].strip()
                    if not spec_line:
                        i += 1
                        continue
                    if (
                        spec_line.startswith("EQNSET ")
                        or spec_line.startswith("SPECSET ")
                        or spec_line.startswith("TIMINGSET ")
                        or spec_line.startswith("PINS ")
                        or spec_line.startswith("EQSP TIM,END")
                        or spec_line == "@"
                    ):
                        break
                    units_match = re.search(r'\[([^]]*)\]', spec_line)
                    units = units_match.group(1).strip() if units_match else ""
                    if units_match:
                        line_without_units = spec_line[:units_match.start()]
                    else:
                        line_without_units = spec_line
                    spec_parts = line_without_units.split()
                    if len(spec_parts) >= 1:
                        spec_name = spec_parts[0]
                        value = spec_parts[1] if len(spec_parts) > 1 else ""
                        specs[spec_name] = TimingSpec(value=value, units=units)
                    i += 1
                continue
            i += 1

        pins_groups: Dict[str, TimingPinConfig] = {}
        timingsets: Dict[int, TimingSetConfig] = {}

        i = eqnset_idx + 1
        while i < len(self.lines):
            line = self.lines[i]
            stripped = line.strip()
            if not stripped:
                i += 1
                continue
            if stripped.startswith("EQNSET ") or stripped.startswith("EQSP TIM,END") or stripped == "@":
                break
            if stripped.startswith("PINS "):
                pins_part = stripped[5:]
                if "#" in pins_part:
                    pins_part = pins_part.split("#", 1)[0]
                pins_name = pins_part.strip()
                if pins_name:
                    pins_groups[pins_name] = self.parse_pins_group(i)
                i += 1
                continue
            if stripped.startswith("TIMINGSET "):
                ts = self.parse_timingset(i)
                if ts is not None:
                    timingsets[ts.index] = ts
                i += 1
                continue
            i += 1

        return TimingEqnSetBlock(
            eqnset_index=eqnset_index,
            eqnset_name=eqnset_name,
            specset_index=specset_index,
            specset_name=specset_name,
            specs=specs,
            pins_groups=pins_groups,
            timingsets=timingsets,
        )

    def parse_wavetbl(self, wavetbl_idx: int) -> Optional[WaveTblBlock]:
        """Parse a WAVETBL block into WaveTblBlock."""
        if wavetbl_idx is None or wavetbl_idx >= len(self.lines):
            return None

        header = self.lines[wavetbl_idx].strip()
        # Handle both standalone "WAVETBL ..." and same-line "EQSP TIM,WVT,...WAVETBL ..."
        if header.startswith("WAVETBL "):
            name = header[8:].strip().strip('"')
        else:
            match = re.search(r'WAVETBL\s+"([^"]*)"', header)
            if match:
                name = match.group(1)
            else:
                return None

        if not name:
            return None

        pins_groups: Dict[str, WaveTblPinsGroup] = {}
        current_pins_name = ""
        current_rows: List[WaveTblRow] = []
        current_brk = ""
        current_f = ""

        def _save_current_group() -> None:
            nonlocal current_pins_name, current_rows, current_brk, current_f
            if current_pins_name:
                pins_groups[current_pins_name] = WaveTblPinsGroup(
                    pins_name=current_pins_name,
                    rows=tuple(current_rows),
                    brk=current_brk,
                    f=current_f,
                )
            current_pins_name = ""
            current_rows = []
            current_brk = ""
            current_f = ""

        for line in self.lines[wavetbl_idx + 1:]:
            stripped = line.strip()

            if not stripped:
                continue

            if stripped.startswith("WAVETBL "):
                break
            if stripped.startswith("SPST TIM,,"):
                break
            if stripped.startswith('SPECIFICATION "'):
                break
            if stripped.startswith("EQSP TIM,END"):
                break
            if stripped == "@":
                break

            if "#" in stripped:
                stripped = stripped.split("#", 1)[0].rstrip()
            if not stripped:
                continue

            if stripped.startswith("PINS "):
                _save_current_group()
                pins_part = stripped[5:].strip()
                current_pins_name = pins_part
                continue

            if stripped.startswith("f ") or stripped.startswith("f\t"):
                quote_match = re.search(r'"([^"]*)"', stripped)
                if quote_match:
                    current_f = quote_match.group(1)
                continue

            if stripped.startswith("brk ") or stripped.startswith("brk\t"):
                quote_match = re.search(r'"([^"]*)"', stripped)
                if quote_match:
                    current_brk = quote_match.group(1)
                continue

            row_match = re.match(r'(\S+)\s+"([^"]*)"(?:\s+(.*))?', stripped)
            if row_match:
                label = row_match.group(1)
                edge_spec = row_match.group(2)
                state = (row_match.group(3) or "").strip()
                current_rows.append(WaveTblRow(
                    label=label,
                    edge_spec=edge_spec,
                    state=state,
                ))

        _save_current_group()

        return WaveTblBlock(name=name, pins_groups=pins_groups)

    def extract_wavetbl_name_from_eqnset(self, eqnset_idx: int) -> Optional[str]:
        """Extract WAVETBL name from an EQNSET block."""
        if eqnset_idx >= len(self.lines):
            return None

        header = self.lines[eqnset_idx].strip()
        if not header.startswith("EQNSET "):
            return None

        for line in self.lines[eqnset_idx + 1:]:
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("EQNSET ") or stripped.startswith("EQSP TIM,END") or stripped == "@":
                break
            if stripped.startswith("WAVETBL "):
                return stripped[8:].strip().strip('"')

        return None

    def extract_wavetbl_names_from_specification(self, spec_idx: int) -> List[str]:
        """Extract all WAVETBL names from a SPECIFICATION block."""
        if spec_idx >= len(self.lines):
            return []

        result: List[str] = []
        depth = 0
        start = spec_idx + 1
        if start < len(self.lines) and self.lines[start].strip() == "{":
            depth = 1
            start += 1

        for line in self.lines[start:]:
            stripped = line.strip()
            if not stripped:
                continue
            if stripped == "{":
                depth += 1
                continue
            if stripped == "}":
                depth -= 1
                if depth <= 0:
                    break
                continue
            if depth <= 0 and (
                stripped.startswith('SPECIFICATION "')
                or stripped.startswith("EQSP TIM,END")
                or stripped == "@"
            ):
                break
            if stripped.startswith("WAVETBL "):
                name = stripped[8:].strip().strip('"')
                if name:
                    result.append(name)

        return result
