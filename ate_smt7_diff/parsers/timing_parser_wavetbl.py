#!/usr/bin/env python3
"""WAVETBL parsing helpers for timing files."""

import re

from ate_smt7_diff.models import WaveTblBlock, WaveTblPinsGroup, WaveTblRow


def parse_wavetbl(lines: list[str], wavetbl_idx: int) -> WaveTblBlock | None:
    """Parse a WAVETBL block into WaveTblBlock."""
    if wavetbl_idx is None or wavetbl_idx >= len(lines):
        return None

    header = lines[wavetbl_idx].strip()
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

    pins_groups: dict[str, WaveTblPinsGroup] = {}
    current_pins_name = ""
    current_rows: list[WaveTblRow] = []
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

    for line in lines[wavetbl_idx + 1 :]:
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

        row_match = re.match(r'(\S+)\s+"([^"]*)"(?:\s+(.*))?\s*', stripped)
        if row_match:
            label = row_match.group(1)
            edge_spec = row_match.group(2)
            state = (row_match.group(3) or "").strip()
            current_rows.append(
                WaveTblRow(
                    label=label,
                    edge_spec=edge_spec,
                    state=state,
                )
            )

    _save_current_group()

    return WaveTblBlock(name=name, pins_groups=pins_groups)
