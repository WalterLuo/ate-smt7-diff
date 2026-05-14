#!/usr/bin/env python3
"""Plugin architecture for diff types.

Diff plugins allow new diff types to be registered without modifying
the core orchestration code in builder/__init__.py.
"""

from __future__ import annotations

from typing import Any, Protocol

from ate_smt7_diff.models import SuiteConfigView


class DiffPlugin(Protocol):
    """Plugin that contributes diff results to a DiffReport."""

    name: str
    requires_views: bool

    def run(
        self,
        old_path: str,
        new_path: str,
        common_suites: set[str],
        old_views: dict[str, SuiteConfigView] | None,
        new_views: dict[str, SuiteConfigView] | None,
        fs: Any | None = None,
    ) -> dict[str, Any]:
        """Execute the plugin and return fields to set on DiffReport.

        Keys in the returned dict must match DiffReport field names
        (e.g. ``{"level_spec_diffs": [...]}``).
        """
        ...
