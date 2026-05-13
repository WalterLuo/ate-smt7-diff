#!/usr/bin/env python3
"""Batch diff report JSON formatter."""

from __future__ import annotations

import json

from ate_smt7_diff.formatters.json import format_json
from ate_smt7_diff.models import BatchDiffReport


def format_batch_json(batch: BatchDiffReport) -> str:
    """Format a batch diff report as JSON."""
    return json.dumps(
        {
            "old_package": batch.old_package,
            "new_package": batch.new_package,
            "total_flows": batch.total_pairs,
            "flows": [
                {
                    "old_file": old_f,
                    "new_file": new_f,
                    "report": json.loads(format_json(report)),
                }
                for old_f, new_f, report in batch.pairs
            ],
        },
        indent=2,
    )
