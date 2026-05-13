#!/usr/bin/env python3
"""
FileSystem abstraction for testability.

Provides a Protocol so parsers and builders can work against
an in-memory filesystem in tests and the real filesystem at runtime.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol


class FileSystem(Protocol):
    """Abstract file system operations."""

    def read_text(self, path: str | Path, encoding: str = "utf-8") -> str:
        """Read file as text."""
        ...

    def exists(self, path: str | Path) -> bool:
        """Check whether path exists."""
        ...

    def read_bytes(self, path: str | Path) -> bytes:
        """Read file as bytes."""
        ...

    def glob(self, directory: str | Path, pattern: str) -> list[Path]:
        """Return paths matching pattern inside directory."""
        ...


class RealFileSystem:
    """Production file system backed by the OS."""

    def read_text(self, path: str | Path, encoding: str = "utf-8") -> str:
        return Path(path).read_text(encoding=encoding)

    def exists(self, path: str | Path) -> bool:
        return Path(path).exists()

    def read_bytes(self, path: str | Path) -> bytes:
        return Path(path).read_bytes()

    def glob(self, directory: str | Path, pattern: str) -> list[Path]:
        return list(Path(directory).glob(pattern))


class InMemoryFileSystem:
    """In-memory file system for testing."""

    def __init__(self, files: dict[str, str | bytes] | None = None) -> None:
        self._files: dict[str, str | bytes] = dict(files) if files else {}

    def add(self, path: str | Path, content: str | bytes) -> None:
        """Add or overwrite a file."""
        self._files[str(path)] = content

    def read_text(self, path: str | Path, encoding: str = "utf-8") -> str:
        content = self._files[str(path)]
        if isinstance(content, bytes):
            return content.decode(encoding)
        return content

    def exists(self, path: str | Path) -> bool:
        return str(path) in self._files

    def read_bytes(self, path: str | Path) -> bytes:
        content = self._files[str(path)]
        if isinstance(content, str):
            return content.encode("utf-8")
        return content

    def glob(self, directory: str | Path, pattern: str) -> list[Path]:
        import fnmatch

        dir_str = str(directory)
        prefix = dir_str + "/"
        results: list[Path] = []
        for p in self._files:
            if p.startswith(prefix):
                rel = p[len(prefix):]
                # Only match direct children (no subdirectories)
                if "/" in rel:
                    continue
                if fnmatch.fnmatch(rel, pattern):
                    results.append(Path(p))
        return sorted(results)
