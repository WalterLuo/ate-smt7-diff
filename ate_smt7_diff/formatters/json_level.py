#!/usr/bin/env python3
"""JSON serialization helpers for level spec and EQNSET diffs."""

from ate_smt7_diff.formatters.shared import (
    arc as _arc,
    arc_all_fields as _arc_all_fields,
    level_spec_dict as _level_spec_dict,
    levelset_group_arc as _levelset_group_arc,
)
from ate_smt7_diff.models import EqnSetDiff, LevelSpecDiff


def _format_level_spec_json(diff: LevelSpecDiff) -> dict:
    """Serialize a LevelSpecDiff as a JSON dict."""
    return {
        "suite_name": diff.suite_name,
        **_arc(diff.added, diff.removed, diff.changed, _level_spec_dict),
    }


def _format_eqnset_json(diff: EqnSetDiff) -> dict:
    """Serialize an EqnSetDiff as a JSON dict."""
    return {
        "suite_name": diff.suite_name,
        "eqnset_index": diff.eqnset_index,
        "eqnset_name": diff.eqnset_name,
        "dpspins": _arc_all_fields(
            diff.dpspins_added, diff.dpspins_removed, diff.dpspins_changed
        ),
        "levelsets": _levelset_group_arc(
            diff.levelsets_added, diff.levelsets_removed, diff.levelsets_changed
        ),
    }
