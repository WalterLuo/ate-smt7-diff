#!/usr/bin/env python3
"""
Vector / pattern mapping file parser.

Loads vector master files that define ``path:`` and ``files:`` sections,
building a lookup from pattern name to its mapped files.
"""

import logging
from pathlib import Path
from typing import Dict, Optional, Tuple

from ate_smt7_diff.models import VectorPatternMapping


class VectorLoader:
    """Load and parse a vector mapping file.

    The file format consists of ``path:`` blocks followed by ``files:`` blocks:

        path:
          ../vectors/SCAN_XSDS

        files:
        DC_SCAN_XSDS@NO_SCAN_XSDS
        DC_SCAN_XSDS@SCAN_XSDS
        NO_SCAN_XSDS

    Each ``path`` defines the directory for the subsequent ``files`` entries.
    Entries with ``@`` are pattern-to-file mappings; entries without ``@``
    are direct file references.

    Parsed data is exposed as ``pattern_lookup``:
        pattern_name -> (path_dir, Tuple[VectorPatternMapping, ...])
    """

    def __init__(self, path: str) -> None:
        self.path = path
        # pattern_name -> (path_dir, Tuple[VectorPatternMapping, ...])
        self.pattern_lookup: Dict[
            str, Tuple[str, Tuple[VectorPatternMapping, ...]]
        ] = {}
        self._load()

    def _load(self) -> None:
        try:
            text = Path(self.path).read_text(encoding="utf-8")
        except (FileNotFoundError, PermissionError) as e:
            logging.warning("Failed to read vector file %s: %s", self.path, e)
            return

        lines = text.splitlines()
        current_path: Optional[str] = None
        in_files = False

        for raw_line in lines:
            line = raw_line.strip()
            if not line or line.startswith("--"):
                continue

            if line.lower() == "path:":
                current_path = None
                in_files = False
                continue

            if line.lower() == "files:":
                in_files = True
                continue

            if current_path is None and not in_files:
                # Content after "path:" but before "files:" is treated as path value
                # It may be indented
                stripped = raw_line.strip()
                if stripped:
                    current_path = stripped
                continue

            if in_files:
                self._parse_file_entry(line, current_path or "")

    def _parse_file_entry(self, line: str, path_dir: str) -> None:
        """Parse a single files: entry and populate pattern_lookup."""
        if "@" in line:
            pattern_name, mapped_file = line.split("@", 1)
            pattern_name = pattern_name.strip()
            mapped_file = mapped_file.strip()
            if not pattern_name:
                return
            mapping = VectorPatternMapping(
                pattern_name=pattern_name,
                mapped_file=mapped_file,
                is_direct=False,
            )
            self._add_mapping(pattern_name, path_dir, mapping)
        else:
            file_name = line.strip()
            if not file_name:
                return
            mapping = VectorPatternMapping(
                pattern_name=file_name,
                mapped_file=None,
                is_direct=True,
            )
            self._add_mapping(file_name, path_dir, mapping)

    def _add_mapping(
        self,
        pattern_name: str,
        path_dir: str,
        mapping: VectorPatternMapping,
    ) -> None:
        """Add a mapping to the lookup table."""
        existing = self.pattern_lookup.get(pattern_name)
        if existing is not None:
            existing_path, existing_mappings = existing
            # If path changed, start a new group (last one wins)
            if existing_path != path_dir:
                self.pattern_lookup[pattern_name] = (
                    path_dir,
                    (mapping,),
                )
            else:
                self.pattern_lookup[pattern_name] = (
                    path_dir,
                    existing_mappings + (mapping,),
                )
        else:
            self.pattern_lookup[pattern_name] = (path_dir, (mapping,))

    def lookup(self, pattern_name: str) -> Optional[Tuple[str, Tuple[VectorPatternMapping, ...]]]:
        """Look up a pattern name and return (path_dir, mappings)."""
        return self.pattern_lookup.get(pattern_name)
