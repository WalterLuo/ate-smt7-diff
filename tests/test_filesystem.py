#!/usr/bin/env python3
"""Tests for FileSystem abstraction."""

import pytest

from ate_smt7_diff.filesystem import InMemoryFileSystem, RealFileSystem


class TestInMemoryFileSystem:
    """Test InMemoryFileSystem behavior."""

    def test_exists_existing_file(self) -> None:
        fs = InMemoryFileSystem({"a.txt": "hello"})
        assert fs.exists("a.txt") is True

    def test_exists_missing_file(self) -> None:
        fs = InMemoryFileSystem()
        assert fs.exists("missing.txt") is False

    def test_read_text_str_content(self) -> None:
        fs = InMemoryFileSystem({"a.txt": "hello"})
        assert fs.read_text("a.txt") == "hello"

    def test_read_text_bytes_content(self) -> None:
        fs = InMemoryFileSystem({"a.txt": b"hello"})
        assert fs.read_text("a.txt") == "hello"

    def test_read_bytes_str_content(self) -> None:
        fs = InMemoryFileSystem({"a.txt": "hello"})
        assert fs.read_bytes("a.txt") == b"hello"

    def test_read_bytes_bytes_content(self) -> None:
        fs = InMemoryFileSystem({"a.txt": b"hello"})
        assert fs.read_bytes("a.txt") == b"hello"

    def test_add_overwrite(self) -> None:
        fs = InMemoryFileSystem()
        fs.add("b.txt", "first")
        assert fs.read_text("b.txt") == "first"
        fs.add("b.txt", "second")
        assert fs.read_text("b.txt") == "second"

    def test_glob_pattern(self) -> None:
        fs = InMemoryFileSystem(
            {
                "dir/a.txt": "1",
                "dir/b.txt": "2",
                "dir/sub/c.txt": "3",
            }
        )
        results = fs.glob("dir", "*.txt")
        assert [str(p) for p in results] == ["dir/a.txt", "dir/b.txt"]

    def test_glob_no_match(self) -> None:
        fs = InMemoryFileSystem({"dir/a.txt": "1"})
        assert fs.glob("dir", "*.py") == []

    def test_glob_wrong_directory(self) -> None:
        fs = InMemoryFileSystem({"dir/a.txt": "1"})
        assert fs.glob("other", "*.txt") == []


class TestRealFileSystem:
    """Smoke tests for RealFileSystem using actual temp files."""

    def test_read_text_roundtrip(self, tmp_path) -> None:
        f = tmp_path / "test.txt"
        f.write_text("hello world", encoding="utf-8")
        fs = RealFileSystem()
        assert fs.read_text(str(f)) == "hello world"

    def test_exists_true(self, tmp_path) -> None:
        f = tmp_path / "test.txt"
        f.write_text("x")
        fs = RealFileSystem()
        assert fs.exists(str(f)) is True

    def test_exists_false(self, tmp_path) -> None:
        fs = RealFileSystem()
        assert fs.exists(str(tmp_path / "missing.txt")) is False

    def test_read_bytes_roundtrip(self, tmp_path) -> None:
        f = tmp_path / "test.bin"
        f.write_bytes(b"\x00\x01\x02")
        fs = RealFileSystem()
        assert fs.read_bytes(str(f)) == b"\x00\x01\x02"

    def test_glob(self, tmp_path) -> None:
        (tmp_path / "a.txt").write_text("1")
        (tmp_path / "b.txt").write_text("2")
        (tmp_path / "c.py").write_text("3")
        fs = RealFileSystem()
        results = fs.glob(str(tmp_path), "*.txt")
        assert sorted(str(p) for p in results) == sorted(
            [str(tmp_path / "a.txt"), str(tmp_path / "b.txt")]
        )
