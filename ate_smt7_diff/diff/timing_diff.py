#!/usr/bin/env python3
"""Backward-compat re-exports for timing diff functions.

New code should import directly from the focused submodules:
- ate_smt7_diff.diff.timing_spec_diff
- ate_smt7_diff.diff.timing_eqnset_diff
- ate_smt7_diff.diff.wavetbl_diff
"""

from ate_smt7_diff.diff.timing_eqnset_diff import (
    _diff_pins_group,
    _diff_timingsets,
    diff_timing_eqnset_blocks_full,
)
from ate_smt7_diff.diff.timing_spec_diff import (
    diff_timing_eqnset_blocks,
    diff_timing_specs,
)
from ate_smt7_diff.diff.wavetbl_diff import (
    diff_wavetbl_blocks,
    diff_wavetbl_pins_group,
    diff_wavetbls,
)

__all__ = [
    "diff_timing_specs",
    "diff_timing_eqnset_blocks",
    "diff_timing_eqnset_blocks_full",
    "_diff_pins_group",
    "_diff_timingsets",
    "diff_wavetbl_pins_group",
    "diff_wavetbl_blocks",
    "diff_wavetbls",
]
