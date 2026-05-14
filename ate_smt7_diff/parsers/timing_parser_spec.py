#!/usr/bin/env python3
"""SPECIFICATION parsing helpers for timing files."""

import re

from ate_smt7_diff.models import TimingSpec


def parse_specification_specs(lines: list[str], spec_idx: int) -> dict[str, TimingSpec]:
    """Parse a SPECIFICATION block into Dict[str, TimingSpec]."""
    if spec_idx >= len(lines):
        return {}

    result: dict[str, TimingSpec] = {}
    units_re = re.compile(r"\[([^]]*)\]")

    depth = 0
    start = spec_idx + 1
    if start < len(lines) and lines[start].strip() == "{":
        depth = 1
        start += 1

    context = ""

    for line in lines[start:]:
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
        if stripped.startswith(
            (
                "SYNC",
                "CHECK ",
                "SPST TIM,,"
                'SPECIFICATION "'
                "EQSP TIM,END",
                "@",
                "#",
            )
        ):
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


def parse_specification_all_eqnsets(lines: list[str], spec_idx: int) -> list[tuple[int, str]]:
    """Extract all EQNSET (index, name) pairs from a SPECIFICATION block."""
    if spec_idx >= len(lines):
        return []

    result: list[tuple[int, str]] = []
    depth = 0
    start = spec_idx + 1
    if start < len(lines) and lines[start].strip() == "{":
        depth = 1
        start += 1

    for line in lines[start:]:
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


def parse_specification_eqnset_index(lines: list[str], spec_idx: int) -> int | None:
    """Extract the first EQNSET index from a SPECIFICATION block."""
    eqnsets = parse_specification_all_eqnsets(lines, spec_idx)
    return eqnsets[0][0] if eqnsets else None


def extract_wavetbl_names_from_specification(lines: list[str], spec_idx: int) -> list[str]:
    """Extract all WAVETBL names from a SPECIFICATION block."""
    if spec_idx >= len(lines):
        return []

    result: list[str] = []
    depth = 0
    start = spec_idx + 1
    if start < len(lines) and lines[start].strip() == "{":
        depth = 1
        start += 1

    for line in lines[start:]:
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
