#!/usr/bin/env python3
"""JSON serialization helpers for MCP tools."""

from __future__ import annotations

import json
from typing import Any


def json_response(payload: Any) -> str:
    """Return a stable JSON string for MCP tool responses."""
    return json.dumps(payload, indent=2, ensure_ascii=False)


def error_response(message: str) -> str:
    """Return the existing simple MCP input-error shape."""
    return json_response({"error": message})


def exception_response(error: Exception) -> str:
    """Return the existing handled-exception response shape."""
    return json_response({"error_type": type(error).__name__, "message": str(error)})
