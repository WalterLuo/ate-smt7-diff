#!/usr/bin/env python3
"""Tests for MCP cache and serializer primitives."""

from __future__ import annotations

import json

from ate_smt7_diff.mcp.cache import McpCache, cache_key
from ate_smt7_diff.mcp.serializers import error_response, exception_response, json_response


def test_cache_key_joins_old_and_new_paths() -> None:
    assert cache_key("/old.flow", "/new.flow") == "/old.flow::/new.flow"


def test_report_cache_uses_lru_eviction() -> None:
    cache = McpCache(max_entries=2)
    cache.store_report("a", "report-a")
    cache.store_report("b", "report-b")
    assert cache.get_report("a") == "report-a"

    cache.store_report("c", "report-c")

    assert cache.get_report("a") == "report-a"
    assert cache.get_report("b") is None
    assert cache.get_report("c") == "report-c"


def test_agent_cache_uses_lru_eviction() -> None:
    cache = McpCache(max_entries=2)
    cache.store_agent("a", {"id": "a"})
    cache.store_agent("b", {"id": "b"})
    assert cache.get_agent("a") == {"id": "a"}

    cache.store_agent("c", {"id": "c"})

    assert cache.get_agent("a") == {"id": "a"}
    assert cache.get_agent("b") is None
    assert cache.get_agent("c") == {"id": "c"}


def test_json_response_preserves_unicode_and_indentation() -> None:
    payload = json.loads(json_response({"message": "删除", "count": 1}))

    assert payload == {"message": "删除", "count": 1}


def test_error_response_shape() -> None:
    assert json.loads(error_response("bad input")) == {"error": "bad input"}


def test_exception_response_shape() -> None:
    assert json.loads(exception_response(ValueError("bad value"))) == {
        "error_type": "ValueError",
        "message": "bad value",
    }
