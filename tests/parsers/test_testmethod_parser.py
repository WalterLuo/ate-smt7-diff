#!/usr/bin/env python3
"""Tests for testmethod_parser.py."""

from ate_smt7_diff.parsers.testmethod_parser import (
    extract_testmethods_section,
    parse_testmethods,
)


class TestExtractTestmethodsSection:
    def test_extracts_section_between_testmethods_and_end(self) -> None:
        lines = [
            "test_suites\n",
            "  SuiteA;\n",
            "end\n",
            "testmethods\n",
            "  tm_100:\n",
            '    testmethod_class = "YT9911CP_TML.TML.pcie_gen2";\n',
            "end\n",
            "test_flow\n",
        ]
        result = extract_testmethods_section(lines)
        assert result == [
            "  tm_100:\n",
            '    testmethod_class = "YT9911CP_TML.TML.pcie_gen2";\n',
        ]

    def test_empty_section(self) -> None:
        lines = [
            "testmethods\n",
            "end\n",
        ]
        result = extract_testmethods_section(lines)
        assert result == []

    def test_no_section_returns_empty(self) -> None:
        lines = [
            "test_suites\n",
            "  SuiteA;\n",
            "end\n",
        ]
        result = extract_testmethods_section(lines)
        assert result == []

    def test_stops_at_first_end(self) -> None:
        lines = [
            "testmethods\n",
            "  tm_100:\n",
            "end\n",
            "  tm_200:\n",
            "end\n",
        ]
        result = extract_testmethods_section(lines)
        assert result == ["  tm_100:\n"]


class TestParseTestmethods:
    def test_parse_single_entry(self) -> None:
        lines = [
            "  tm_100:\n",
            '    testmethod_class = "YT9911CP_TML.TML.pcie_gen2";\n',
        ]
        result = parse_testmethods(lines)
        assert result == {"tm_100": "YT9911CP_TML.TML.pcie_gen2"}

    def test_parse_multiple_entries(self) -> None:
        lines = [
            "  tm_100:\n",
            '    testmethod_class = "YT9911CP_TML.TML.pcie_gen2";\n',
            "  tm_200:\n",
            '    testmethod_class = "ac_tml.AcTest.FunctionalTest";\n',
        ]
        result = parse_testmethods(lines)
        assert result == {
            "tm_100": "YT9911CP_TML.TML.pcie_gen2",
            "tm_200": "ac_tml.AcTest.FunctionalTest",
        }

    def test_skips_comments(self) -> None:
        lines = [
            "  // built-in testmethod\n",
            "  tm_100:\n",
            '    testmethod_class = "YT9911CP_TML.TML.pcie_gen2";\n',
        ]
        result = parse_testmethods(lines)
        assert result == {"tm_100": "YT9911CP_TML.TML.pcie_gen2"}

    def test_skips_inline_comments(self) -> None:
        lines = [
            "  tm_100:\n",
            '    testmethod_class = "YT9911CP_TML.TML.pcie_gen2"; // comment\n',
        ]
        result = parse_testmethods(lines)
        assert result == {"tm_100": "YT9911CP_TML.TML.pcie_gen2"}

    def test_empty_lines_ignored(self) -> None:
        lines = [
            "\n",
            "  tm_100:\n",
            "\n",
            '    testmethod_class = "YT9911CP_TML.TML.pcie_gen2";\n',
            "\n",
        ]
        result = parse_testmethods(lines)
        assert result == {"tm_100": "YT9911CP_TML.TML.pcie_gen2"}

    def test_entry_without_class_ignored(self) -> None:
        lines = [
            "  tm_100:\n",
            "  tm_200:\n",
            '    testmethod_class = "ac_tml.AcTest.FunctionalTest";\n',
        ]
        result = parse_testmethods(lines)
        assert result == {"tm_200": "ac_tml.AcTest.FunctionalTest"}

    def test_no_entries_returns_empty(self) -> None:
        lines = [
            "  // nothing here\n",
        ]
        result = parse_testmethods(lines)
        assert result == {}
