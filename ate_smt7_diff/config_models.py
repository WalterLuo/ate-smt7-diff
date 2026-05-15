"""Configuration models for flow file matching."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class FlowMatchConfig:
    """Configuration for matching flow files between two program packages."""

    # Regex pattern with named groups
    regex: str | None = None

    # Delimiter-based parsing (alternative to regex)
    delimiter: str | None = None
    fields: list[dict[str, Any]] = field(default_factory=list)

    # Fields that must match for pairing
    match_by: list[str] = field(default_factory=list)

    # Field that identifies version (can differ between old/new)
    version_field: str | None = None

    # Glob patterns to exclude (always includes *.bak and *SETUP*)
    exclude: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FlowMatchConfig:
        """Create config from a dictionary."""
        return cls(
            regex=data.get("regex"),
            delimiter=data.get("delimiter"),
            fields=data.get("fields", []),
            match_by=data.get("match_by", []),
            version_field=data.get("version_field"),
            exclude=data.get("exclude", []),
        )

    @classmethod
    def from_json(cls, path: Path | str) -> FlowMatchConfig:
        """Load config from a JSON file."""
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        # Support both top-level and nested "flow_matching" key
        return cls.from_dict(data.get("flow_matching", data))

    def get_regex_pattern(self) -> re.Pattern[str] | None:
        """Compile regex pattern if configured."""
        if self.regex:
            return re.compile(self.regex)
        return None

    def get_exclude_patterns(self) -> list[str]:
        """Return default exclusions plus configured ones."""
        defaults = ["*.bak", "*SETUP*"]
        extras = [e for e in self.exclude if e not in defaults]
        return defaults + extras
