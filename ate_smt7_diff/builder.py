#!/usr/bin/env python3
"""
Builder / assembler layer.
Orchestrates parsing, diff computation, and config view building.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from ate_smt7_diff.models import (
    DiffReport,
    EqnSetBlock,
    EqnSetDiff,
    LevelSpec,
    LevelSpecDiff,
    ProgramContext,
    SuiteConfigReport,
    SuiteConfigView,
    TimingEqnSetBlock,
    TimingEqnSetDiff,
    TimingSpec,
    TimingSpecDiff,
    VectorSuiteDiff,
    VectorSuiteMapping,
    WaveTblBlock,
)
from ate_smt7_diff.parsers.flow_parser import extract_test_flow_section, parse_test_flow
from ate_smt7_diff.parsers.suite_parser import (
    extract_context_section,
    extract_test_suites_section,
    parse_context,
    parse_suite_config,
)
from ate_smt7_diff.parsers.level_parser import LevelLoader
from ate_smt7_diff.parsers.timing_parser import TimingLoader
from ate_smt7_diff.parsers.testtable_parser import TestTableLoader
from ate_smt7_diff.parsers.vector_parser import VectorLoader
from ate_smt7_diff.diff.flow_diff import compute_diff, detect_moves, detect_swaps
from ate_smt7_diff.diff.suite_diff import diff_suite_configs
from ate_smt7_diff.diff.level_diff import diff_level_specs, diff_eqnset_blocks
from ate_smt7_diff.diff.timing_diff import (
    diff_timing_specs,
    diff_timing_eqnset_blocks,
    diff_timing_eqnset_blocks_full,
    diff_wavetbls,
)
from ate_smt7_diff.diff.testtable_diff import diff_testtables
from ate_smt7_diff.diff.vector_diff import diff_vectors


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


def _resolve_timing_config(
    cfg: Dict[str, str], suite_name: str
) -> Tuple[Optional[str], Optional[int], Optional[int], Optional[str]]:
    """Resolve timing spec set, EQNSET, SPECSET index, and timset from suite config."""
    timing_spec: Optional[str] = None
    tim_raw = cfg.get("override_tim_spec_set")
    if tim_raw:
        timing_spec = tim_raw.strip('"')

    timing_eqn: Optional[int] = None
    tim_eqn_raw = cfg.get("override_tim_equ_set")
    if tim_eqn_raw:
        try:
            timing_eqn = int(tim_eqn_raw)
        except ValueError:
            logging.warning(
                "Invalid override_tim_equ_set '%s' for suite %s",
                tim_eqn_raw, suite_name,
            )

    timing_spec_idx: Optional[int] = None
    tim_spec_idx_raw = cfg.get("override_tim_spec_set")
    if tim_spec_idx_raw:
        try:
            timing_spec_idx = int(tim_spec_idx_raw)
        except ValueError:
            pass

    timing_timset: Optional[str] = None
    timset_raw = cfg.get("override_timset")
    if timset_raw:
        timing_timset = timset_raw.strip('"')

    return timing_spec, timing_eqn, timing_spec_idx, timing_timset


def _resolve_level_config(
    cfg: Dict[str, str], suite_name: str
) -> Tuple[Optional[int], Optional[int], Optional[int]]:
    """Resolve level EQNSET, SPECSET, and levset from suite config."""
    level_eqn: Optional[int] = None
    lev_eqn_raw = cfg.get("override_lev_equ_set")
    if lev_eqn_raw:
        try:
            level_eqn = int(lev_eqn_raw)
        except ValueError:
            logging.warning(
                "Invalid override_lev_equ_set '%s' for suite %s",
                lev_eqn_raw, suite_name,
            )

    level_spec: Optional[int] = None
    lev_spec_raw = cfg.get("override_lev_spec_set")
    if lev_spec_raw:
        try:
            level_spec = int(lev_spec_raw)
        except ValueError:
            logging.warning(
                "Invalid override_lev_spec_set '%s' for suite %s",
                lev_spec_raw, suite_name,
            )

    level_levset: Optional[int] = None
    levset_raw = cfg.get("override_levset")
    if levset_raw:
        try:
            level_levset = int(levset_raw)
        except ValueError:
            logging.warning(
                "Invalid override_levset '%s' for suite %s",
                levset_raw, suite_name,
            )

    return level_eqn, level_spec, level_levset


def _extract_timing_data(
    timing_loader: Optional[TimingLoader],
    timing_spec: Optional[str],
    timing_eqn: Optional[int],
    timing_timset: Optional[str],
) -> Tuple[
    Optional[str],
    Optional[Dict[str, TimingSpec]],
    Optional[TimingEqnSetBlock],
    Optional[List[Tuple[int, str]]],
    Dict[int, TimingEqnSetBlock],
    Tuple[str, ...],
    Dict[str, WaveTblBlock],
]:
    """Extract timing snippet, specs, EQNSET block, port-spec EQNSET refs, and WAVETBLs."""
    if not timing_loader or not timing_spec:
        return None, None, None, None, {}, (), {}

    timing_snippet: Optional[str] = None
    timing_specs: Optional[Dict[str, TimingSpec]] = None
    timing_eqnset_block: Optional[TimingEqnSetBlock] = None
    timing_spec_eqnsets: Optional[List[Tuple[int, str]]] = None
    timing_eqnset_blocks: Dict[int, TimingEqnSetBlock] = {}
    wavetbl_names: List[str] = []
    wavetbl_blocks: Dict[str, WaveTblBlock] = {}

    is_port_spec = timing_eqn is None

    if is_port_spec:
        spec_idx = timing_loader.lookup_specification(timing_spec)
        if spec_idx is not None:
            timing_snippet = timing_loader.extract_snippet(spec_idx)
            timing_specs = timing_loader.parse_specification_specs(spec_idx)
            # Extract ALL EQNSET references from SPECIFICATION block
            timing_spec_eqnsets = timing_loader.parse_specification_all_eqnsets(spec_idx)
            # Load full EQNSET blocks for each referenced EQNSET
            for eq_idx, _eq_name in timing_spec_eqnsets:
                eqnset_line = timing_loader.lookup_eqsp_eqnset(eq_idx)
                if eqnset_line is not None:
                    block = timing_loader.parse_eqsp_eqnset_block(eqnset_line)
                    if block is not None:
                        timing_eqnset_blocks[eq_idx] = block
            # Extract WAVETBL names from SPECIFICATION block
            wavetbl_names = timing_loader.extract_wavetbl_names_from_specification(spec_idx)
        else:
            spec_idx = timing_loader.lookup_spec_set(timing_spec)
            if spec_idx is not None:
                timing_snippet = timing_loader.extract_snippet(spec_idx)
    else:
        eqn_idx = timing_loader.lookup_eqsp_eqnset(timing_eqn)
        if eqn_idx is not None:
            timing_snippet = timing_loader.extract_eqsp_snippet(eqn_idx)
            timing_eqnset_block = timing_loader.parse_eqsp_eqnset_block(eqn_idx)
            if timing_eqnset_block:
                timing_specs = timing_eqnset_block.specs
            # Extract WAVETBL name from EQNSET block
            wt_name = timing_loader.extract_wavetbl_name_from_eqnset(eqn_idx)
            if wt_name:
                wavetbl_names = [wt_name]

    # Load WAVETBL blocks
    for wt_name in wavetbl_names:
        if wt_name in wavetbl_blocks:
            continue
        wt_idx = timing_loader.lookup_wavetbl(wt_name)
        if wt_idx is not None:
            wt_block = timing_loader.parse_wavetbl(wt_idx)
            if wt_block is not None:
                wavetbl_blocks[wt_name] = wt_block

    return (
        timing_snippet,
        timing_specs,
        timing_eqnset_block,
        timing_spec_eqnsets,
        timing_eqnset_blocks,
        tuple(wavetbl_names),
        wavetbl_blocks,
    )


def _extract_level_data(
    level_loader: Optional[LevelLoader],
    level_eqn: Optional[int],
    level_spec: Optional[int],
) -> Tuple[Optional[str], Optional[Dict[str, LevelSpec]], Optional[EqnSetBlock]]:
    """Extract level snippet, specs, and EQNSET block."""
    if not level_loader or level_eqn is None:
        return None, None, None

    level_snippet: Optional[str] = None
    if level_spec is not None:
        spec_idx = level_loader.lookup_specset(level_eqn, level_spec)
        if spec_idx is not None:
            level_snippet = level_loader.extract_snippet(spec_idx)
        else:
            eqn_idx = level_loader.lookup_eqnset(level_eqn)
            if eqn_idx is not None:
                level_snippet = level_loader.extract_snippet(eqn_idx)

    level_specs: Optional[Dict[str, LevelSpec]] = None
    if level_spec is not None:
        spec_idx = level_loader.lookup_specset(level_eqn, level_spec)
        if spec_idx is not None:
            level_specs = level_loader.parse_specs(spec_idx)

    eqnset_block: Optional[EqnSetBlock] = None
    eqn_idx = level_loader.lookup_eqnset(level_eqn)
    if eqn_idx is not None:
        eqnset_block = level_loader.parse_eqnset_block(eqn_idx)

    return level_snippet, level_specs, eqnset_block


def _diff_port_timing(
    suite_name: str,
    old_v: SuiteConfigView,
    new_v: SuiteConfigView,
    timing_spec_diffs: List[TimingSpecDiff],
    timing_eqnset_diffs: List[TimingEqnSetDiff],
) -> None:
    """Diff port-spec timing (no override_tim_equ_set)."""
    spec_name = old_v.timing_spec_set or new_v.timing_spec_set or ""

    if old_v.timing_spec_set != new_v.timing_spec_set:
        spec_diff = TimingSpecDiff(
            suite_name=suite_name,
            spec_type="port",
            spec_name=new_v.timing_spec_set or "",
            replaced_from=old_v.timing_spec_set,
            old_specs=old_v.timing_specs,
            new_specs=new_v.timing_specs,
        )
        if spec_diff.has_changes:
            timing_spec_diffs.append(spec_diff)
        return

    old_eqnsets = tuple(old_v.timing_spec_eqnsets or [])
    new_eqnsets = tuple(new_v.timing_spec_eqnsets or [])

    if old_eqnsets != new_eqnsets:
        old_eqnset_set: Set[Tuple[int, str]] = set(old_eqnsets)
        new_eqnset_set: Set[Tuple[int, str]] = set(new_eqnsets)
        common_eqnsets: Set[Tuple[int, str]] = old_eqnset_set & new_eqnset_set
        old_only: Set[Tuple[int, str]] = old_eqnset_set - new_eqnset_set
        new_only: Set[Tuple[int, str]] = new_eqnset_set - old_eqnset_set

        if len(old_only) == 1 and len(new_only) == 1:
            old_eq = old_only.pop()
            new_eq = new_only.pop()
            old_idx, old_name = old_eq
            new_idx, new_name = new_eq
            te_diff = TimingEqnSetDiff(
                suite_name=suite_name,
                eqnset_index=new_idx,
                eqnset_name=new_name,
                replaced_from_index=old_idx,
                replaced_from_name=old_name,
                new_block=new_v.timing_eqnset_blocks.get(new_idx),
            )
            if te_diff.has_changes:
                timing_eqnset_diffs.append(te_diff)
        else:
            for old_idx, old_name in old_only:
                old_block = old_v.timing_eqnset_blocks.get(old_idx)
                te_diff = TimingEqnSetDiff(
                    suite_name=suite_name,
                    eqnset_index=old_idx,
                    eqnset_name=old_name,
                    specs_removed=old_block.specs if old_block else {},
                    pins_removed=old_block.pins_groups if old_block else {},
                    timingsets_removed=old_block.timingsets if old_block else {},
                )
                if te_diff.has_changes:
                    timing_eqnset_diffs.append(te_diff)
            for new_idx, new_name in new_only:
                new_block = new_v.timing_eqnset_blocks.get(new_idx)
                te_diff = TimingEqnSetDiff(
                    suite_name=suite_name,
                    eqnset_index=new_idx,
                    eqnset_name=new_name,
                    specs_added=new_block.specs if new_block else {},
                    pins_added=new_block.pins_groups if new_block else {},
                    timingsets_added=new_block.timingsets if new_block else {},
                )
                if te_diff.has_changes:
                    timing_eqnset_diffs.append(te_diff)

        for eq_idx, _eq_name in common_eqnsets:
            old_block = old_v.timing_eqnset_blocks.get(eq_idx)
            new_block = new_v.timing_eqnset_blocks.get(eq_idx)
            te_diff = diff_timing_eqnset_blocks_full(
                suite_name=suite_name,
                old_block=old_block,
                new_block=new_block,
            )
            if te_diff and te_diff.has_changes:
                timing_eqnset_diffs.append(te_diff)
        return

    spec_diff = diff_timing_specs(
        suite_name=suite_name,
        spec_type="port",
        spec_name=spec_name,
        old_specs=old_v.timing_specs,
        new_specs=new_v.timing_specs,
    )
    if spec_diff and spec_diff.has_changes:
        timing_spec_diffs.append(spec_diff)

    for eq_idx, _eq_name in old_eqnsets:
        old_block = old_v.timing_eqnset_blocks.get(eq_idx)
        new_block = new_v.timing_eqnset_blocks.get(eq_idx)
        te_diff = diff_timing_eqnset_blocks_full(
            suite_name=suite_name,
            old_block=old_block,
            new_block=new_block,
        )
        if te_diff and te_diff.has_changes:
            timing_eqnset_diffs.append(te_diff)


def _diff_regular_timing(
    suite_name: str,
    old_v: SuiteConfigView,
    new_v: SuiteConfigView,
    timing_spec_diffs: List[TimingSpecDiff],
    timing_eqnset_diffs: List[TimingEqnSetDiff],
) -> None:
    """Diff regular timing (by override_tim_equ_set)."""
    if old_v.timing_eqn_set != new_v.timing_eqn_set:
        old_block = old_v.timing_eqnset_block
        new_block = new_v.timing_eqnset_block
        old_idx = old_v.timing_eqn_set or 0
        old_name = old_block.eqnset_name if old_block else ""
        te_diff = TimingEqnSetDiff(
            suite_name=suite_name,
            eqnset_index=new_v.timing_eqn_set or 0,
            eqnset_name=new_block.eqnset_name if new_block else "",
            replaced_from_index=old_idx,
            replaced_from_name=old_name,
            new_block=new_block,
        )
        if te_diff.has_changes:
            timing_eqnset_diffs.append(te_diff)
        return

    tim_diff = diff_timing_eqnset_blocks(
        suite_name=suite_name,
        old_block=old_v.timing_eqnset_block,
        new_block=new_v.timing_eqnset_block,
    )
    if tim_diff and tim_diff.has_changes:
        timing_spec_diffs.append(tim_diff)

    te_diff = diff_timing_eqnset_blocks_full(
        suite_name=suite_name,
        old_block=old_v.timing_eqnset_block,
        new_block=new_v.timing_eqnset_block,
    )
    if te_diff and te_diff.has_changes:
        timing_eqnset_diffs.append(te_diff)


def build_suite_views(
    flow_path: str,
    common_suites: Set[str],
) -> Dict[str, SuiteConfigView]:
    """
    Build SuiteConfigView for each common suite.

    Loads program context, parses test_suites, and extracts relevant
    timing/level snippets based on override indices.
    """
    ctx = load_program_context(flow_path)

    timing_loader: Optional[TimingLoader] = None
    if ctx.timing_path and ctx.timing_path.exists():
        timing_loader = TimingLoader(ctx.timing_path)

    level_loader: Optional[LevelLoader] = None
    if ctx.levels_path and ctx.levels_path.exists():
        level_loader = LevelLoader(ctx.levels_path)

    testtable_loader: Optional[TestTableLoader] = None
    if ctx.testtable_path and ctx.testtable_path.exists():
        testtable_loader = TestTableLoader(str(ctx.testtable_path))

    vector_loader: Optional[VectorLoader] = None
    if ctx.vector_path and ctx.vector_path.exists():
        vector_loader = VectorLoader(str(ctx.vector_path))

    flow_lines = Path(flow_path).read_text(encoding="utf-8").splitlines()
    ts_lines = extract_test_suites_section(flow_lines)
    suite_configs = parse_suite_config(ts_lines)

    views: Dict[str, SuiteConfigView] = {}
    for suite_name in sorted(common_suites):
        cfg = suite_configs.get(suite_name, {})

        timing_spec, timing_eqn, timing_spec_idx, timing_timset = _resolve_timing_config(cfg, suite_name)
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

        testtable_rows = testtable_loader.rows_by_suite.get(suite_name) if testtable_loader else None

        # Resolve vector pattern mappings for this suite
        vector_mappings: Optional[VectorSuiteMapping] = None
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
        )

    return views


def diff_flow_files(
    old_path: str,
    new_path: str,
    include_suite_diff: bool = False,
    include_config_views: bool = False,
    include_testtable_diff: bool = False,
) -> DiffReport:
    """Main entry: parse two flow files and compute diff."""
    try:
        old_lines = Path(old_path).read_text(encoding="utf-8").splitlines()
        new_lines = Path(new_path).read_text(encoding="utf-8").splitlines()
    except FileNotFoundError as e:
        raise FileNotFoundError(f"Flow file not found: {e.filename}") from e
    except PermissionError as e:
        raise PermissionError(f"Permission denied reading flow file: {e.filename}") from e
    except UnicodeDecodeError as e:
        raise ValueError(f"File encoding error (expected UTF-8): {e}") from e

    old_tf = extract_test_flow_section(old_lines)
    new_tf = extract_test_flow_section(new_lines)

    old_tests = parse_test_flow(old_tf)
    new_tests = parse_test_flow(new_tf)

    diffs = compute_diff(old_tests, new_tests)
    diffs = detect_moves(diffs)
    diffs = detect_swaps(diffs)

    suite_report: Optional[SuiteConfigReport] = None
    if include_suite_diff:
        old_names = {t.suite_name for t in old_tests}
        new_names = {t.suite_name for t in new_tests}
        common_suites = old_names & new_names
        suite_report = diff_suite_configs(old_path, new_path, common_suites)

    old_views: Optional[Dict[str, SuiteConfigView]] = None
    new_views: Optional[Dict[str, SuiteConfigView]] = None
    level_spec_diffs: Optional[List[LevelSpecDiff]] = None
    eqnset_diffs: Optional[List[EqnSetDiff]] = None
    timing_spec_diffs: Optional[List[TimingSpecDiff]] = None
    timing_eqnset_diffs: Optional[List[TimingEqnSetDiff]] = None
    timing_wavetbl_diffs: Optional[List["WaveTblDiff"]] = None
    vector_diffs: Optional[List[VectorSuiteDiff]] = None
    if include_config_views:
        old_names = {t.suite_name for t in old_tests}
        new_names = {t.suite_name for t in new_tests}
        common_suites = old_names & new_names
        old_views = build_suite_views(old_path, common_suites)
        new_views = build_suite_views(new_path, common_suites)

        level_spec_diffs = []
        eqnset_diffs = []
        timing_spec_diffs = []
        timing_eqnset_diffs = []
        timing_wavetbl_diffs = []
        for suite_name in sorted(common_suites):
            old_v = old_views.get(suite_name)
            new_v = new_views.get(suite_name)
            if old_v and new_v:
                diff = diff_level_specs(suite_name, old_v.level_specs, new_v.level_specs)
                if diff and diff.has_changes:
                    level_spec_diffs.append(diff)
                eq_diff = diff_eqnset_blocks(suite_name, old_v.eqnset_block, new_v.eqnset_block)
                if eq_diff and eq_diff.has_changes:
                    eqnset_diffs.append(eq_diff)

                if old_v.timing_eqn_set is None and new_v.timing_eqn_set is None:
                    _diff_port_timing(
                        suite_name, old_v, new_v, timing_spec_diffs, timing_eqnset_diffs
                    )
                else:
                    _diff_regular_timing(
                        suite_name, old_v, new_v, timing_spec_diffs, timing_eqnset_diffs
                    )

                # WAVETBL diff
                wt_diffs = diff_wavetbls(
                    suite_name,
                    old_v.timing_wavetbl_blocks,
                    new_v.timing_wavetbl_blocks,
                )
                timing_wavetbl_diffs.extend(wt_diffs)
        if not level_spec_diffs:
            level_spec_diffs = None
        if not eqnset_diffs:
            eqnset_diffs = None
        if not timing_spec_diffs:
            timing_spec_diffs = None
        if not timing_eqnset_diffs:
            timing_eqnset_diffs = None
        if not timing_wavetbl_diffs:
            timing_wavetbl_diffs = None

        # Vector diff
        vector_diffs = diff_vectors(
            sorted(common_suites),
            old_views or {},
            new_views or {},
        )
        if not vector_diffs:
            vector_diffs = None

    testtable_diffs = None
    if include_testtable_diff:
        old_names = {t.suite_name for t in old_tests}
        new_names = {t.suite_name for t in new_tests}
        common_suites = old_names & new_names

        if old_views is not None and new_views is not None:
            # Reuse already-loaded testtable data from config views
            old_rows_by_suite = {
                suite_name: view.testtable_rows
                for suite_name, view in old_views.items()
                if view.testtable_rows is not None
            }
            new_rows_by_suite = {
                suite_name: view.testtable_rows
                for suite_name, view in new_views.items()
                if view.testtable_rows is not None
            }
        else:
            old_ctx = load_program_context(old_path)
            new_ctx = load_program_context(new_path)
            old_testtable = TestTableLoader(str(old_ctx.testtable_path)) if old_ctx.testtable_path else None
            new_testtable = TestTableLoader(str(new_ctx.testtable_path)) if new_ctx.testtable_path else None
            old_rows_by_suite = old_testtable.rows_by_suite if old_testtable else {}
            new_rows_by_suite = new_testtable.rows_by_suite if new_testtable else {}

        testtable_diffs = diff_testtables(
            sorted(common_suites),
            old_rows_by_suite,
            new_rows_by_suite,
        )
        if not testtable_diffs:
            testtable_diffs = None

    return DiffReport(
        old_file=old_path,
        new_file=new_path,
        old_tests=old_tests,
        new_tests=new_tests,
        diffs=diffs,
        suite_config_report=suite_report,
        old_suite_views=old_views,
        new_suite_views=new_views,
        level_spec_diffs=level_spec_diffs,
        eqnset_diffs=eqnset_diffs,
        timing_spec_diffs=timing_spec_diffs,
        timing_eqnset_diffs=timing_eqnset_diffs,
        timing_wavetbl_diffs=timing_wavetbl_diffs,
        testtable_diffs=testtable_diffs,
        vector_diffs=vector_diffs,
    )
