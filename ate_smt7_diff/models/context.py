#!/usr/bin/env python3
"""Program context and path resolution models."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ProgramContext:
    """Parsed context section from a flow file with resolved file paths."""

    program_root: Path
    config_file: str | None  # pin config file (no subdir)
    levels_file: str | None  # level file in levels/
    timing_file: str | None  # timing file in timing/
    vector_file: str | None  # pattern file in vectors/
    testtable_file: str | None  # testtable file in testtable/

    @property
    def levels_path(self) -> Path | None:
        if self.levels_file:
            return self.program_root / "levels" / self.levels_file
        return None

    @property
    def timing_path(self) -> Path | None:
        if self.timing_file:
            return self.program_root / "timing" / self.timing_file
        return None

    @property
    def vector_path(self) -> Path | None:
        if self.vector_file:
            return self.program_root / "vectors" / self.vector_file
        return None

    @property
    def testtable_path(self) -> Path | None:
        if self.testtable_file:
            return self.program_root / "testtable" / self.testtable_file
        return None

    @property
    def config_path(self) -> Path | None:
        if self.config_file:
            return self.program_root / self.config_file
        return None

    def all_paths(self) -> dict[str, Path | None]:
        """Return all resolved paths as a dict."""
        return {
            "levels": self.levels_path,
            "timing": self.timing_path,
            "vectors": self.vector_path,
            "testtable": self.testtable_path,
            "config": self.config_path,
        }
