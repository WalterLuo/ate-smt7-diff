#!/usr/bin/env python3
"""EQNSET block parsing helpers for timing files."""

import contextlib
import re

from ate_smt7_diff.models import TimingEqnSetBlock, TimingSpec
from ate_smt7_diff.parsers.timing_parser_pins import parse_pins_group, parse_timingset


def parse_eqsp_eqnset_block(lines: list[str], eqnset_idx: int) -> TimingEqnSetBlock | None:
    """Parse an EQNSET block from the EQSP TIM,SPS region."""
    if eqnset_idx >= len(lines):
        return None

    header = lines[eqnset_idx].strip()
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

    specs: dict[str, TimingSpec] = {}
    specset_index = 0
    specset_name = ""

    i = eqnset_idx + 1
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if not stripped:
            i += 1
            continue
        if (
            stripped.startswith("EQNSET ")
            or stripped.startswith("EQSP TIM,END")
            or stripped == "@"
        ):
            break
        if stripped.startswith("SPECSET "):
            spec_parts = stripped.split(None, 2)
            if len(spec_parts) >= 2:
                with contextlib.suppress(ValueError):
                    specset_index = int(spec_parts[1])
            if len(spec_parts) >= 3:
                specset_name = spec_parts[2].strip().strip('"')
            i += 1
            continue
        if (
            stripped == "SPECS"
            or stripped.startswith("# SPECNAME")
            or stripped.startswith("#SPECNAME")
        ):
            i += 1
            while i < len(lines):
                spec_line = lines[i].strip()
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
                units_match = re.search(r"\[([^]]*)\]", spec_line)
                units = units_match.group(1).strip() if units_match else ""
                if units_match:
                    line_without_units = spec_line[: units_match.start()]
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

    pins_groups: dict[str, "TimingPinConfig"] = {}
    timingsets: dict[int, "TimingSetConfig"] = {}

    i = eqnset_idx + 1
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if not stripped:
            i += 1
            continue
        if (
            stripped.startswith("EQNSET ")
            or stripped.startswith("EQSP TIM,END")
            or stripped == "@"
        ):
            break
        if stripped.startswith("PINS "):
            pins_part = stripped[5:]
            if "#" in pins_part:
                pins_part = pins_part.split("#", 1)[0]
            pins_name = pins_part.strip()
            if pins_name:
                pins_groups[pins_name] = parse_pins_group(lines, i)
            i += 1
            continue
        if stripped.startswith("TIMINGSET "):
            ts = parse_timingset(lines, i)
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


def extract_wavetbl_name_from_eqnset(lines: list[str], eqnset_idx: int) -> str | None:
    """Extract WAVETBL name from an EQNSET block."""
    if eqnset_idx >= len(lines):
        return None

    header = lines[eqnset_idx].strip()
    if not header.startswith("EQNSET "):
        return None

    for line in lines[eqnset_idx + 1 :]:
        stripped = line.strip()
        if not stripped:
            continue
        if (
            stripped.startswith("EQNSET ")
            or stripped.startswith("EQSP TIM,END")
            or stripped == "@"
        ):
            break
        if stripped.startswith("WAVETBL "):
            return stripped[8:].strip().strip('"')

    return None
