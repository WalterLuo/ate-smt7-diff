#!/usr/bin/env python3
"""PINS and TIMINGSET parsing helpers for timing files."""

from ate_smt7_diff.models import TimingPinConfig, TimingSetConfig


def parse_pins_group(lines: list[str], pins_idx: int) -> TimingPinConfig:
    """Parse a PINS block into TimingPinConfig."""
    if pins_idx >= len(lines):
        return TimingPinConfig()

    fields: dict[str, str] = {}
    for line in lines[pins_idx + 1 :]:
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


def parse_timingset(lines: list[str], ts_idx: int) -> TimingSetConfig | None:
    """Parse a TIMINGSET block into TimingSetConfig."""
    if ts_idx >= len(lines):
        return None

    header = lines[ts_idx].strip()
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
    extra: dict[str, str] = {}
    for line in lines[ts_idx + 1 :]:
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
