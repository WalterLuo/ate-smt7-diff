#!/usr/bin/env python3
"""
Testmethods section parser.
Extracts and parses 'testmethods' blocks from flow files into
a map of {tm_id: testmethod_class}.
"""

import re

# Module-level compiled regex patterns
_TM_ID_RE = re.compile(r"^([a-zA-Z0-9_]+):\s*$")
_TM_CLASS_RE = re.compile(r'^\s*testmethod_class\s*=\s*"([^"]+)"\s*;\s*$')


def extract_testmethods_section(lines: list[str]) -> list[str]:
    """Extract lines between 'testmethods' and its matching 'end'."""
    in_section = False
    section_lines: list[str] = []

    for line in lines:
        stripped = line.strip()

        if stripped == "testmethods":
            in_section = True
            continue

        if in_section:
            if stripped == "end":
                break
            section_lines.append(line)

    return section_lines


def parse_testmethods(lines: list[str]) -> dict[str, str]:
    """
    Parse testmethods section into {tm_id: testmethod_class}.

    Each entry starts with 'tm_id:' and the next line(s) contain
    testmethod_class = "...";
    """
    result: dict[str, str] = {}
    current_tm_id: str | None = None

    for line in lines:
        stripped = line.strip()

        if not stripped or stripped.startswith("//"):
            continue

        comment_idx = stripped.find("//")
        if comment_idx != -1:
            stripped = stripped[:comment_idx].strip()
        if not stripped:
            continue

        match = _TM_ID_RE.match(stripped)
        if match:
            current_tm_id = match.group(1)
            continue

        match = _TM_CLASS_RE.match(stripped)
        if match and current_tm_id is not None:
            result[current_tm_id] = match.group(1)
            current_tm_id = None
            continue

    return result
