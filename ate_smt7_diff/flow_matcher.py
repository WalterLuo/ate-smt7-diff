"""Flow file matcher for pairing files between two program packages."""

from __future__ import annotations

import fnmatch
import logging
from pathlib import Path

from ate_smt7_diff.config_models import FlowMatchConfig

logger = logging.getLogger(__name__)


class FlowMatcher:
    """Matches flow files between two directories based on configuration."""

    def __init__(self, config: FlowMatchConfig) -> None:
        self.config = config

    @classmethod
    def from_config(cls, config_path: Path | str | None = None) -> FlowMatcher:
        """Create matcher from config file, or auto-discover / use smart defaults."""
        if config_path:
            path = Path(config_path)
            config = FlowMatchConfig.from_json(path)
            return cls(config)

        discovered = cls._discover_config()
        if discovered:
            logger.info("Auto-discovered config: %s", discovered)
            config = FlowMatchConfig.from_json(discovered)
            return cls(config)

        return cls(FlowMatchConfig())

    @classmethod
    def _discover_config(cls) -> Path | None:
        """Search common locations for a config file."""
        candidates = [
            Path(".smt7-diff-config.json"),
            Path.home() / ".smt7-diff-config.json",
        ]
        for candidate in candidates:
            if candidate.exists():
                return candidate.resolve()
        return None

    def _should_exclude(self, filename: str) -> bool:
        """Check if filename matches any exclusion pattern."""
        for pattern in self.config.get_exclude_patterns():
            if fnmatch.fnmatch(filename, pattern):
                return True
        return False

    def _parse_filename(self, filename: str) -> dict[str, str] | None:
        """Parse filename into field dictionary."""
        stem = Path(filename).stem

        # Try regex first (match against full name or stem)
        regex = self.config.get_regex_pattern()
        if regex:
            match = regex.match(filename)
            if match:
                return match.groupdict()
            match = regex.match(stem)
            if match:
                return match.groupdict()
            return None

        # Try delimiter-based parsing
        if self.config.delimiter and self.config.fields:
            parts = stem.split(self.config.delimiter)
            result: dict[str, str] = {}
            for field_def in self.config.fields:
                name = field_def.get("name")
                index = field_def.get("index")
                if name is not None and index is not None and index < len(parts):
                    result[name] = parts[index]
            return result if result else None

        # Fallback: no parsing, return empty dict
        return {}

    def _match_key(self, fields: dict[str, str]) -> tuple[str, ...]:
        """Build match key from parsed fields."""
        if not self.config.match_by:
            # Default: use all fields except version_field
            keys = sorted(
                k for k in fields if k != self.config.version_field
            )
            return tuple(fields.get(k, "") for k in keys)
        return tuple(fields.get(k, "") for k in self.config.match_by)

    def match_directories(
        self, old_dir: Path | str, new_dir: Path | str
    ) -> list[tuple[Path, Path]]:
        """Match flow files between two directories."""
        old_path = Path(old_dir)
        new_path = Path(new_dir)

        old_flows = self._collect_flows(old_path)
        new_flows = self._collect_flows(new_path)

        return self._match_flows(old_flows, new_flows)

    def _collect_flows(self, directory: Path) -> list[Path]:
        """Collect all .flow files from directory, excluding matches."""
        flows: list[Path] = []
        if not directory.exists():
            logger.warning("Directory does not exist: %s", directory)
            return flows
        for flow_file in sorted(directory.glob("*.flow")):
            if not self._should_exclude(flow_file.name):
                flows.append(flow_file)
            else:
                logger.debug("Excluding %s", flow_file.name)
        return flows

    def _match_flows(
        self, old_flows: list[Path], new_flows: list[Path]
    ) -> list[tuple[Path, Path]]:
        """Pair old/new flow files based on config."""
        # Parse all filenames
        old_parsed: list[tuple[Path, dict[str, str] | None]] = [
            (flow, self._parse_filename(flow.name)) for flow in old_flows
        ]
        new_parsed: list[tuple[Path, dict[str, str] | None]] = [
            (flow, self._parse_filename(flow.name)) for flow in new_flows
        ]

        # Exact matching by match key
        matches: list[tuple[Path, Path]] = []
        matched_new: set[int] = set()

        for old_flow, old_fields in old_parsed:
            if old_fields is None:
                continue
            old_key = self._match_key(old_fields)

            for idx, (new_flow, new_fields) in enumerate(new_parsed):
                if idx in matched_new or new_fields is None:
                    continue
                new_key = self._match_key(new_fields)
                if old_key == new_key:
                    matches.append((old_flow, new_flow))
                    matched_new.add(idx)
                    break

        # Fallback smart matching for leftovers
        matched_old_names = {m[0].name for m in matches}
        unmatched_old = [f for f, _ in old_parsed if f.name not in matched_old_names]
        unmatched_new = [
            f for idx, (f, _) in enumerate(new_parsed) if idx not in matched_new
        ]

        if unmatched_old and unmatched_new:
            smart = self._smart_match(unmatched_old, unmatched_new)
            matches.extend(smart)

        return sorted(matches, key=lambda x: x[0].name)

    def _smart_match(
        self, old_flows: list[Path], new_flows: list[Path]
    ) -> list[tuple[Path, Path]]:
        """Fallback smart matching using LCS similarity."""
        matches: list[tuple[Path, Path]] = []
        matched_new: set[int] = set()

        for old_flow in old_flows:
            best_score = 0.0
            best_idx = -1

            for idx, new_flow in enumerate(new_flows):
                if idx in matched_new:
                    continue
                score = _lcs_similarity(old_flow.stem, new_flow.stem)
                if score > best_score:
                    best_score = score
                    best_idx = idx

            if best_idx >= 0 and best_score >= 0.5:
                matches.append((old_flow, new_flows[best_idx]))
                matched_new.add(best_idx)
                logger.info(
                    "Smart-matched %s -> %s (score=%.2f)",
                    old_flow.name,
                    new_flows[best_idx].name,
                    best_score,
                )

        return matches


def _lcs_similarity(a: str, b: str) -> float:
    """Compute longest common subsequence similarity between two strings.

    Returns a score in [0, 1] where 1 means identical.
    """
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0

    m, n = len(a), len(b)
    # Use two rows to keep O(min(m, n)) space
    if m < n:
        a, b = b, a
        m, n = n, m

    prev = [0] * (n + 1)
    curr = [0] * (n + 1)

    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if a[i - 1] == b[j - 1]:
                curr[j] = prev[j - 1] + 1
            else:
                curr[j] = max(prev[j], curr[j - 1])
        prev, curr = curr, prev

    lcs_len = prev[n]
    return (2 * lcs_len) / (len(a) + len(b))
