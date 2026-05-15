#!/usr/bin/env python3
"""SmartDiffAgent: intelligent reasoning layer over ate-smt7-diff."""

from ate_smt7_diff.agent.discover import (
    DiscoveryResult,
    FlowPairSummary,
    SuiteChangeSummary,
    discover,
)
from ate_smt7_diff.agent.explain import ExplanationItem, explain
from ate_smt7_diff.agent.suggest import SuggestionItem, suggest
from ate_smt7_diff.agent.validate import ValidationItem, ValidationResult, validate

__all__ = [
    "discover",
    "suggest",
    "explain",
    "validate",
    "DiscoveryResult",
    "FlowPairSummary",
    "SuiteChangeSummary",
    "SuggestionItem",
    "ExplanationItem",
    "ValidationResult",
    "ValidationItem",
]
