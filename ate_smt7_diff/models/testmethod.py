#!/usr/bin/env python3
"""Testmethod reference and source diff models."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class TestMethodInfo:
    """Resolved testmethod metadata and source file for a single suite."""

    tm_id: str
    testmethod_class: str
    file_path: Path | None = None
    content: str | None = None


@dataclass(frozen=True)
class TestMethodDiff:
    """Diff result for a suite's testmethod reference and optional source diff."""

    suite_name: str
    diff_type: str  # unchanged, tm_id_changed, class_changed, both_changed, file_changed, file_not_found
    old_tm_id: str | None = None
    new_tm_id: str | None = None
    old_class: str | None = None
    new_class: str | None = None
    file_diff: tuple[str, ...] = field(default_factory=tuple)

    @property
    def has_changes(self) -> bool:
        return self.diff_type != "unchanged"
