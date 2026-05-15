#!/usr/bin/env python3
"""
Data extractors: pull timing/level snippets and blocks from loaders.
"""

from ate_smt7_diff.models import (
    EqnSetBlock,
    LevelSpec,
    TimingEqnSetBlock,
    TimingSpec,
    WaveTblBlock,
)
from ate_smt7_diff.parsers.level_parser import LevelLoader
from ate_smt7_diff.parsers.timing_parser import TimingLoader


def _extract_timing_data(
    timing_loader: TimingLoader | None,
    timing_spec: str | None,
    timing_eqn: int | None,
) -> tuple[
    str | None,
    dict[str, TimingSpec] | None,
    TimingEqnSetBlock | None,
    list[tuple[int, str]] | None,
    dict[int, TimingEqnSetBlock],
    tuple[str, ...],
    dict[str, WaveTblBlock],
]:
    """Extract timing snippet, specs, EQNSET block, port-spec EQNSET refs, and WAVETBLs."""
    if not timing_loader or not timing_spec:
        return None, None, None, None, {}, (), {}

    timing_snippet: str | None = None
    timing_specs: dict[str, TimingSpec] | None = None
    timing_eqnset_block: TimingEqnSetBlock | None = None
    timing_spec_eqnsets: list[tuple[int, str]] | None = None
    timing_eqnset_blocks: dict[int, TimingEqnSetBlock] = {}
    wavetbl_names: list[str] = []
    wavetbl_blocks: dict[str, WaveTblBlock] = {}

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
    level_loader: LevelLoader | None,
    level_eqn: int | None,
    level_spec: int | None,
) -> tuple[str | None, dict[str, LevelSpec] | None, EqnSetBlock | None]:
    """Extract level snippet, specs, and EQNSET block."""
    if not level_loader or level_eqn is None:
        return None, None, None

    level_snippet: str | None = None
    if level_spec is not None:
        spec_idx = level_loader.lookup_specset(level_eqn, level_spec)
        if spec_idx is not None:
            level_snippet = level_loader.extract_snippet(spec_idx)
        else:
            eqn_idx = level_loader.lookup_eqnset(level_eqn)
            if eqn_idx is not None:
                level_snippet = level_loader.extract_snippet(eqn_idx)

    level_specs: dict[str, LevelSpec] | None = None
    if level_spec is not None:
        spec_idx = level_loader.lookup_specset(level_eqn, level_spec)
        if spec_idx is not None:
            level_specs = level_loader.parse_specs(spec_idx)

    eqnset_block: EqnSetBlock | None = None
    eqn_idx = level_loader.lookup_eqnset(level_eqn)
    if eqn_idx is not None:
        eqnset_block = level_loader.parse_eqnset_block(eqn_idx)

    return level_snippet, level_specs, eqnset_block
