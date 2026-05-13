#!/usr/bin/env python3
"""Vector pattern mapping models."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class VectorPatternMapping:
    """A single pattern-to-file mapping from the vector file."""

    pattern_name: str
    mapped_file: str | None
    is_direct: bool


@dataclass(frozen=True)
class VectorSuiteMapping:
    """Resolved vector mappings for a single suite.

    ``path`` is the absolute resolved directory where mapped files live.
    """

    suite_name: str
    seqlbl: str
    path: str
    pattern_mappings: tuple[VectorPatternMapping, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class VectorFileDateChange:
    """A single file whose modification date differs."""

    file_path: str
    old_mtime: float
    new_mtime: float


@dataclass(frozen=True)
class VectorSuiteDiff:
    """Diff result for vector mappings of a single suite."""

    suite_name: str
    diff_type: str
    old_mappings: tuple[VectorPatternMapping, ...] | None = None
    new_mappings: tuple[VectorPatternMapping, ...] | None = None
    file_date_changes: tuple[VectorFileDateChange, ...] = field(default_factory=tuple)

    @property
    def has_changes(self) -> bool:
        return bool(self.diff_type in ("changed", "added", "removed", "file_date_changed"))
