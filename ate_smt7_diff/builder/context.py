#!/usr/bin/env python3
"""
Program context loading.
"""

from pathlib import Path

from ate_smt7_diff.models import ProgramContext
from ate_smt7_diff.parsers.suite_parser import extract_context_section, parse_context


def load_program_context(flow_path: str) -> ProgramContext:
    """
    Load program context from a flow file.

    Derives program root as flow_file.parent.parent (e.g.,
    test1/example1/testflow/example1.flow -> test1/example1).
    """
    flow = Path(flow_path)
    if not flow.exists():
        raise FileNotFoundError(f"Flow file not found: {flow_path}")

    program_root = flow.parent.parent

    lines = flow.read_text(encoding="utf-8").splitlines()
    ctx_lines = extract_context_section(lines)
    ctx = parse_context(ctx_lines)

    return ProgramContext(
        program_root=program_root,
        config_file=ctx.get("context_config_file"),
        levels_file=ctx.get("context_levels_file"),
        timing_file=ctx.get("context_timing_file"),
        vector_file=ctx.get("context_vector_file"),
        testtable_file=ctx.get("context_testtable_file"),
    )
