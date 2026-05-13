#!/usr/bin/env python3
"""Central data models for the SMT7 diff engine.

All domain models are re-exported here for backward compatibility.
New code may import from the specific submodule for tighter dependencies.
"""

from ate_smt7_diff.models.context import ProgramContext
from ate_smt7_diff.models.flow import (
    BatchDiffReport,
    DiffReport,
    DiffType,
    FlowDiff,
    TestItem,
)
from ate_smt7_diff.models.level import (
    DpsPinConfig,
    EqnSetBlock,
    EqnSetDiff,
    LevelSetPinConfig,
    LevelSpec,
    LevelSpecDiff,
)
from ate_smt7_diff.models.suite import (
    SuiteConfigDiff,
    SuiteConfigReport,
    SuiteConfigView,
)
from ate_smt7_diff.models.testmethod import TestMethodDiff, TestMethodInfo
from ate_smt7_diff.models.testtable import (
    TestTableRow,
    TestTableRowDiff,
    TestTableSuiteDiff,
)
from ate_smt7_diff.models.timing import (
    TimingEqnSetBlock,
    TimingEqnSetDiff,
    TimingPinConfig,
    TimingSetConfig,
    TimingSpec,
    TimingSpecDiff,
)
from ate_smt7_diff.models.vector import (
    VectorFileDateChange,
    VectorPatternMapping,
    VectorSuiteDiff,
    VectorSuiteMapping,
)
from ate_smt7_diff.models.wavetable import (
    WaveTblBlock,
    WaveTblDiff,
    WaveTblPinsGroup,
    WaveTblPinsGroupDiff,
    WaveTblRow,
)

__all__ = [
    "BatchDiffReport",
    "DiffReport",
    "DiffType",
    "DpsPinConfig",
    "EqnSetBlock",
    "EqnSetDiff",
    "FlowDiff",
    "LevelSetPinConfig",
    "LevelSpec",
    "LevelSpecDiff",
    "ProgramContext",
    "SuiteConfigDiff",
    "SuiteConfigReport",
    "SuiteConfigView",
    "TestItem",
    "TestMethodDiff",
    "TestMethodInfo",
    "TestTableRow",
    "TestTableRowDiff",
    "TestTableSuiteDiff",
    "TimingEqnSetBlock",
    "TimingEqnSetDiff",
    "TimingPinConfig",
    "TimingSetConfig",
    "TimingSpec",
    "TimingSpecDiff",
    "VectorFileDateChange",
    "VectorPatternMapping",
    "VectorSuiteDiff",
    "VectorSuiteMapping",
    "WaveTblBlock",
    "WaveTblDiff",
    "WaveTblPinsGroup",
    "WaveTblPinsGroupDiff",
    "WaveTblRow",
]
