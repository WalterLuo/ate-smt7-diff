#!/usr/bin/env python3
"""
Config resolvers: extract override indices from suite flow config.
"""

import contextlib
import logging


def _resolve_timing_config(
    cfg: dict[str, str], suite_name: str
) -> tuple[str | None, int | None, int | None]:
    """Resolve timing spec set, EQNSET, and SPECSET index from suite config."""
    timing_spec: str | None = None
    tim_raw = cfg.get("override_tim_spec_set")
    if tim_raw:
        timing_spec = tim_raw.strip('"')

    timing_eqn: int | None = None
    tim_eqn_raw = cfg.get("override_tim_equ_set")
    if tim_eqn_raw:
        try:
            timing_eqn = int(tim_eqn_raw)
        except ValueError:
            logging.warning(
                "Invalid override_tim_equ_set '%s' for suite %s",
                tim_eqn_raw,
                suite_name,
            )

    timing_spec_idx: int | None = None
    tim_spec_idx_raw = cfg.get("override_tim_spec_set")
    if tim_spec_idx_raw:
        with contextlib.suppress(ValueError):
            timing_spec_idx = int(tim_spec_idx_raw)

    return timing_spec, timing_eqn, timing_spec_idx


def _resolve_level_config(
    cfg: dict[str, str], suite_name: str
) -> tuple[int | None, int | None]:
    """Resolve level EQNSET and SPECSET from suite config."""
    level_eqn: int | None = None
    lev_eqn_raw = cfg.get("override_lev_equ_set")
    if lev_eqn_raw:
        try:
            level_eqn = int(lev_eqn_raw)
        except ValueError:
            logging.warning(
                "Invalid override_lev_equ_set '%s' for suite %s",
                lev_eqn_raw,
                suite_name,
            )

    level_spec: int | None = None
    lev_spec_raw = cfg.get("override_lev_spec_set")
    if lev_spec_raw:
        try:
            level_spec = int(lev_spec_raw)
        except ValueError:
            logging.warning(
                "Invalid override_lev_spec_set '%s' for suite %s",
                lev_spec_raw,
                suite_name,
            )

    return level_eqn, level_spec
