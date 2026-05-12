#!/usr/bin/env python3
"""
Level file parser.
Loads and indexes level files, parses SPECSET, EQNSET, DPSPINS, and LEVELSET blocks.
"""

import re

from ate_smt7_diff.models import (
    DpsPinConfig,
    EqnSetBlock,
    LevelSetPinConfig,
    LevelSpec,
)


class LevelLoader:
    """Loads and indexes a level file."""

    def __init__(self, path: str) -> None:
        self.path = path
        self.lines: list[str] = []
        self.eqnsets: dict[int, int] = {}
        self.eqnset_specs: dict[tuple[int, int], int] = {}
        self._load()

    def _load(self) -> None:
        from pathlib import Path

        try:
            raw = Path(self.path).read_text(encoding="utf-8")
        except (FileNotFoundError, PermissionError, UnicodeDecodeError) as e:
            raise ValueError(f"Failed to read level file {self.path}: {e}") from e

        self.lines = raw.splitlines()
        current_eqn: int | None = None
        for i, line in enumerate(self.lines):
            stripped = line.strip()
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
            elif stripped.startswith("SPECSET ") and current_eqn is not None:
                parts = stripped.split(None, 2)
                if len(parts) >= 2:
                    try:
                        spec_idx = int(parts[1])
                    except ValueError:
                        continue
                    self.eqnset_specs[(current_eqn, spec_idx)] = i

    def lookup_eqnset(self, eqn_index: int) -> int | None:
        """Return line index of EQNSET entry."""
        return self.eqnsets.get(eqn_index)

    def lookup_specset(self, eqn_index: int, spec_index: int) -> int | None:
        """Return line index of SPECSET entry within EQNSET."""
        return self.eqnset_specs.get((eqn_index, spec_index))

    def extract_snippet(self, start_idx: int) -> str:
        """Extract lines from start_idx until next EQNSET or end of file."""
        if start_idx >= len(self.lines):
            return ""
        result: list[str] = []
        for line in self.lines[start_idx:]:
            if line.strip().startswith("EQNSET ") and result:
                break
            result.append(line)
        return "\n".join(result)

    def parse_specs(self, specset_idx: int) -> dict[str, LevelSpec]:
        """Parse spec lines from a SPECSET block into structured dict."""
        if specset_idx >= len(self.lines):
            return {}

        result: dict[str, LevelSpec] = {}
        in_specs = False
        units_re = re.compile(r"\[([^]]*)\]")

        for line in self.lines[specset_idx + 1 :]:
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

            units_match = units_re.search(line)
            units = units_match.group(1).strip() if units_match else ""
            if units_match:
                line_without_units = line[: units_match.start()]
                comment = line[units_match.end() :].strip()
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
        """Parse a DPSPINS block into DpsPinConfig."""
        if dpspins_idx >= len(self.lines):
            return DpsPinConfig()

        fields: dict[str, str] = {}
        for line in self.lines[dpspins_idx + 1 :]:
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

    def parse_levelset(self, levelset_idx: int) -> dict[str, LevelSetPinConfig]:
        """Parse a LEVELSET block into dict of PINS group -> LevelSetPinConfig."""
        if levelset_idx >= len(self.lines):
            return {}

        result: dict[str, LevelSetPinConfig] = {}
        current_pins: str | None = None
        current_fields: dict[str, str] = {}

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

        for line in self.lines[levelset_idx + 1 :]:
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
                pins_part = stripped[5:]
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

    def parse_eqnset_block(self, eqnset_idx: int) -> EqnSetBlock | None:
        """Parse an EQNSET block from the EQSP LEV,EQN region."""
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

        specs: dict[str, LevelSpec] = {}
        dpspins: dict[str, DpsPinConfig] = {}
        levelsets: dict[int, dict[str, LevelSetPinConfig]] = {}

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
                    units_match = re.search(r"\[([^]]*)\]", spec_line)
                    units = units_match.group(1).strip() if units_match else ""
                    if units_match:
                        line_without_units = spec_line[: units_match.start()]
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
