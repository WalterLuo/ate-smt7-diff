#!/usr/bin/env python3
"""
Suite config view builder.
"""

from pathlib import Path

from ate_smt7_diff.builder.context import load_program_context
from ate_smt7_diff.builder.extractors import _extract_level_data, _extract_timing_data
from ate_smt7_diff.builder.resolvers import _resolve_level_config, _resolve_timing_config
from ate_smt7_diff.filesystem import FileSystem, RealFileSystem
from ate_smt7_diff.models import (
    SuiteConfigView,
    TestMethodInfo,
    VectorSuiteMapping,
)
from ate_smt7_diff.parsers.level_parser import LevelLoader
from ate_smt7_diff.parsers.suite_parser import extract_test_suites_section, parse_suite_config
from ate_smt7_diff.parsers.testmethod_parser import extract_testmethods_section, parse_testmethods
from ate_smt7_diff.parsers.testtable_parser import TestTableLoader
from ate_smt7_diff.parsers.timing_parser import TimingLoader
from ate_smt7_diff.parsers.vector_parser import VectorLoader


def build_suite_views(
    flow_path: str,
    common_suites: set[str],
    fs: FileSystem | None = None,
) -> dict[str, SuiteConfigView]:
    """
    Build SuiteConfigView for each common suite.

    Loads program context, parses test_suites, and extracts relevant
    timing/level snippets based on override indices.
    """
    fs = fs or RealFileSystem()
    ctx = load_program_context(flow_path, fs)

    timing_loader: TimingLoader | None = None
    if ctx.timing_path and fs.exists(ctx.timing_path):
        timing_loader = TimingLoader(str(ctx.timing_path), fs)

    level_loader: LevelLoader | None = None
    if ctx.levels_path and fs.exists(ctx.levels_path):
        level_loader = LevelLoader(str(ctx.levels_path), fs)

    testtable_loader: TestTableLoader | None = None
    if ctx.testtable_path and fs.exists(ctx.testtable_path):
        testtable_loader = TestTableLoader(str(ctx.testtable_path), fs)

    vector_loader: VectorLoader | None = None
    if ctx.vector_path and fs.exists(ctx.vector_path):
        vector_loader = VectorLoader(str(ctx.vector_path), fs)

    flow_lines = fs.read_text(flow_path, encoding="utf-8").splitlines()
    ts_lines = extract_test_suites_section(flow_lines)
    suite_configs = parse_suite_config(ts_lines)

    # Parse testmethods block once
    tm_lines = extract_testmethods_section(flow_lines)
    testmethods_map = parse_testmethods(tm_lines)

    views: dict[str, SuiteConfigView] = {}
    for suite_name in sorted(common_suites):
        cfg = suite_configs.get(suite_name, {})

        timing_spec, timing_eqn, timing_spec_idx, timing_timset = _resolve_timing_config(
            cfg, suite_name
        )
        level_eqn, level_spec, level_levset = _resolve_level_config(cfg, suite_name)

        (
            timing_snippet,
            timing_specs,
            timing_eqnset_block,
            timing_spec_eqnsets,
            timing_eqnset_blocks,
            timing_wavetbl_names,
            timing_wavetbl_blocks,
        ) = _extract_timing_data(timing_loader, timing_spec, timing_eqn, timing_timset)
        level_snippet, level_specs, eqnset_block = _extract_level_data(
            level_loader, level_eqn, level_spec
        )

        testtable_rows = (
            testtable_loader.rows_by_suite.get(suite_name) if testtable_loader else None
        )

        # Resolve vector pattern mappings for this suite
        vector_mappings: VectorSuiteMapping | None = None
        seqlbl_raw = cfg.get("override_seqlbl")
        if seqlbl_raw and vector_loader:
            seqlbl = seqlbl_raw.strip('"')
            lookup = vector_loader.lookup(seqlbl)
            if lookup is not None:
                path_dir, mappings = lookup
                # Resolve path relative to the vector file's directory
                vector_base = ctx.vector_path.parent if ctx.vector_path else ctx.program_root
                resolved_path = str((vector_base / path_dir).resolve())
                vector_mappings = VectorSuiteMapping(
                    suite_name=suite_name,
                    seqlbl=seqlbl,
                    path=resolved_path,
                    pattern_mappings=mappings,
                )

        # Resolve testmethod reference for this suite
        testmethod: TestMethodInfo | None = None
        override_testf = cfg.get("override_testf")
        if override_testf:
            tm_id = override_testf.strip().rstrip(";")
            tm_class = testmethods_map.get(tm_id)
            if tm_class:
                # Convert dot-separated class path to file path with .cpp extension
                rel_path = tm_class.replace(".", "/") + ".cpp"
                tm_file_path = ctx.program_root / rel_path
                content: str | None = None
                if fs.exists(str(tm_file_path)):
                    try:
                        content = fs.read_text(str(tm_file_path), encoding="utf-8")
                    except (UnicodeDecodeError, PermissionError, OSError):
                        content = None
                testmethod = TestMethodInfo(
                    tm_id=tm_id,
                    testmethod_class=tm_class,
                    file_path=tm_file_path if tm_file_path.exists() else None,
                    content=content,
                )

        views[suite_name] = SuiteConfigView(
            suite_name=suite_name,
            flow_config=cfg,
            timing_spec_set=timing_spec,
            timing_eqn_set=timing_eqn,
            timing_spec_index=timing_spec_idx,
            level_eqn_set=level_eqn,
            level_spec_set=level_spec,
            level_levset=level_levset,
            timing_snippet=timing_snippet,
            level_snippet=level_snippet,
            level_specs=level_specs,
            eqnset_block=eqnset_block,
            timing_specs=timing_specs,
            timing_eqnset_block=timing_eqnset_block,
            timing_spec_eqnsets=timing_spec_eqnsets,
            timing_eqnset_blocks=timing_eqnset_blocks,
            timing_wavetbl_names=timing_wavetbl_names,
            timing_wavetbl_blocks=timing_wavetbl_blocks,
            testtable_rows=testtable_rows,
            vector_mappings=vector_mappings,
            testmethod=testmethod,
        )

    return views
