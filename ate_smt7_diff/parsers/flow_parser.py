#!/usr/bin/env python3
"""
Test flow section parser.
Extracts and parses 'test_flow' blocks into a flat list of TestItems.
"""

import re
from typing import List

from ate_smt7_diff.models import TestItem


# Module-level compiled regex patterns for parsing test_flow
_RUN_RE = re.compile(r'^\s*run\(\s*([^)]+?)\s*\)\s*;\s*$')
_RUN_BRANCH_RE = re.compile(r'^\s*run_and_branch\(\s*([^)]+?)\s*\)\s*$')
_GROUP_END_RE = re.compile(
    r'^\s*}\s*,\s*(open|close|groupbypass)\s*,\s*"((?:[^"\\\\]|\\\\.)*)"\s*$'
)


def extract_test_flow_section(lines: List[str]) -> List[str]:
    """Extract lines between 'test_flow' and its matching 'end'."""
    in_test_flow = False
    test_flow_lines = []

    for line in lines:
        stripped = line.strip()

        if stripped == "test_flow":
            in_test_flow = True
            continue

        if in_test_flow:
            if stripped == "end":
                break
            test_flow_lines.append(line)

    return test_flow_lines


def parse_test_flow(lines: List[str]) -> List[TestItem]:
    """
    Parse test_flow lines into a flat list of TestItems.

    Handles:
      - run(SuiteName);
      - run_and_branch(SuiteName)
      - { ... }, open,"GroupName", ""
      - { ... }, close,"GroupName", ""
    """
    result: List[TestItem] = []
    group_stack: List[str] = []
    i = 0

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if not stripped or stripped.startswith('//'):
            i += 1
            continue

        match = _RUN_RE.match(line)
        if match:
            suite_name = match.group(1).strip()
            result.append(TestItem(
                suite_name=suite_name,
                group_path=tuple(group_stack),
                line_number=i + 1,
                is_branch=False
            ))
            i += 1
            continue

        match = _RUN_BRANCH_RE.match(line)
        if match:
            suite_name = match.group(1).strip()
            result.append(TestItem(
                suite_name=suite_name,
                group_path=tuple(group_stack),
                line_number=i + 1,
                is_branch=True
            ))
            i += 1
            continue

        match = _GROUP_END_RE.match(line)
        if match:
            group_type = match.group(1)
            group_name = match.group(2)
            if group_type == "open":
                group_stack.append(group_name)
            elif group_type == "close":
                if group_stack and group_stack[-1] == group_name:
                    group_stack.pop()
                elif group_name in group_stack:
                    while group_stack and group_stack[-1] != group_name:
                        group_stack.pop()
                    if group_stack:
                        group_stack.pop()
            elif group_type == "groupbypass":
                pass
            i += 1
            continue

        if stripped == '{':
            i += 1
            continue

        i += 1

    return result
