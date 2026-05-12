#!/usr/bin/env python3
"""
Suite and context section parsers.
Extracts and parses 'context' and 'test_suites' blocks from flow files.
"""

import re

# Module-level compiled regex patterns
_SUITE_NAME_RE = re.compile(r"^([^:\s]+):$")
_CONFIG_KEY_RE = re.compile(r"^([^\s=]+)\s*=\s*(.+)$")


def extract_context_section(lines: list[str]) -> list[str]:
    """Extract lines between 'context' and its matching 'end'."""
    in_section = False
    section_lines = []

    for line in lines:
        stripped = line.strip()

        if stripped == "context":
            in_section = True
            continue

        if in_section:
            if stripped == "end":
                break
            section_lines.append(line)

    return section_lines


def parse_context(lines: list[str]) -> dict[str, str]:
    """Parse context section into {key: value}."""
    result: dict[str, str] = {}
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("//"):
            continue

        comment_idx = stripped.find("//")
        if comment_idx != -1:
            stripped = stripped[:comment_idx].strip()
        if not stripped:
            continue

        match = _CONFIG_KEY_RE.match(stripped)
        if match:
            key = match.group(1)
            raw_value = match.group(2).strip()
            if raw_value.endswith(";"):
                raw_value = raw_value[:-1].strip()
            if len(raw_value) >= 2 and raw_value[0] == '"' and raw_value[-1] == '"':
                raw_value = raw_value[1:-1]
            result[key] = raw_value

    return result


def extract_test_suites_section(lines: list[str]) -> list[str]:
    """Extract lines between 'test_suites' and its matching 'end'."""
    in_section = False
    section_lines = []

    for line in lines:
        stripped = line.strip()

        if stripped == "test_suites":
            in_section = True
            continue

        if in_section:
            if stripped == "end":
                break
            section_lines.append(line)

    return section_lines


def parse_suite_config(lines: list[str]) -> dict[str, dict[str, str]]:
    """
    Parse test_suites section into {suite_name: {key: value}}.

    Each suite starts with 'SuiteName:' and continues until the next
    'SuiteName:' or the end of the section.
    """
    result: dict[str, dict[str, str]] = {}
    current_suite: str | None = None

    for line in lines:
        stripped = line.strip()

        if not stripped or stripped.startswith("//"):
            continue

        comment_idx = stripped.find("//")
        if comment_idx != -1:
            stripped = stripped[:comment_idx].strip()
        if not stripped:
            continue

        match = _SUITE_NAME_RE.match(stripped)
        if match:
            current_suite = match.group(1)
            result[current_suite] = {}
            continue

        match = _CONFIG_KEY_RE.match(stripped)
        if match and current_suite is not None:
            key = match.group(1)
            raw_value = match.group(2).strip()
            if raw_value.endswith(";"):
                raw_value = raw_value[:-1].strip()
            result[current_suite][key] = raw_value
            continue

    return result
