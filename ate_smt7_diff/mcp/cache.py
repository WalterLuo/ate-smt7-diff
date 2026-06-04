#!/usr/bin/env python3
"""Local in-process cache for MCP tool results."""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass, field
from typing import TypeVar

from ate_smt7_diff.models import BatchDiffReport, DiffReport

ReportValue = DiffReport | BatchDiffReport | object
AgentValue = object
T = TypeVar("T")


def cache_key(old: str, new: str) -> str:
    """Build the stable cache key shared by diff and agent tools."""
    return f"{old}::{new}"


@dataclass
class McpCache:
    """Bounded LRU cache used by one MCP server process."""

    max_entries: int = 10
    report_cache: OrderedDict[str, ReportValue] = field(default_factory=OrderedDict)
    agent_cache: OrderedDict[str, AgentValue] = field(default_factory=OrderedDict)

    def store_report(self, key: str, report: ReportValue) -> None:
        self._store(self.report_cache, key, report)

    def get_report(self, key: str) -> ReportValue | None:
        return self._get(self.report_cache, key)

    def store_agent(self, key: str, result: AgentValue) -> None:
        self._store(self.agent_cache, key, result)

    def get_agent(self, key: str) -> AgentValue | None:
        return self._get(self.agent_cache, key)

    def _store(self, cache: OrderedDict[str, T], key: str, value: T) -> None:
        if key in cache:
            cache.move_to_end(key)
        elif len(cache) >= self.max_entries:
            cache.popitem(last=False)
        cache[key] = value

    def _get(self, cache: OrderedDict[str, T], key: str) -> T | None:
        if key not in cache:
            return None
        cache.move_to_end(key)
        return cache[key]
