#!/usr/bin/env python3
"""Generic diff utilities to eliminate repeated set-difference logic."""

from __future__ import annotations

from typing import Callable, TypeVar

K = TypeVar("K")
V = TypeVar("V")


def diff_dicts(
    old: dict[K, V] | None,
    new: dict[K, V] | None,
    compare: Callable[[V, V], bool] | None = None,
) -> tuple[dict[K, V], dict[K, V], dict[K, tuple[V, V]]] | None:
    """Return (added, removed, changed) between two dicts.

    Returns ``None`` when both inputs are ``None``.
    If only one input is ``None``, returns appropriate add/remove
    with empty changed.

    ``compare`` defaults to ``==`` (i.e. ``old_val == new_val``).
    When provided, a return value of ``False`` indicates a change.
    """
    if old is None and new is None:
        return None
    if old is None:
        return (new or {}, {}, {})
    if new is None:
        return ({}, old, {})

    old_keys = set(old.keys())
    new_keys = set(new.keys())

    added = {k: new[k] for k in new_keys - old_keys}
    removed = {k: old[k] for k in old_keys - new_keys}
    changed: dict[K, tuple[V, V]] = {}

    _compare = compare if compare is not None else lambda a, b: a == b
    for k in old_keys & new_keys:
        if not _compare(old[k], new[k]):
            changed[k] = (old[k], new[k])

    return added, removed, changed
