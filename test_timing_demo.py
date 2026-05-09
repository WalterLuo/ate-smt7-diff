#!/usr/bin/env python3
"""Demo script to verify timing spec diff output."""

from ate_smt7_diff.diff.timing_diff import (
    diff_timing_specs,
    diff_timing_eqnset_blocks,
    diff_timing_eqnset_blocks_full,
)
from ate_smt7_diff.models import (
    TimingEqnSetBlock,
    TimingPinConfig,
    TimingSetConfig,
    TimingSpec,
)


def demo_port_spec_diff():
    """Demo: Port Spec mode diff (override_tim_spec_set only)."""
    old = {
        "TCLK": TimingSpec(value="10.0", units="ns", comment=""),
        "TPER": TimingSpec(value="20.0", units="ns", comment=""),
    }
    new = {
        "TCLK": TimingSpec(value="12.0", units="ns", comment="# updated"),
        "TPER": TimingSpec(value="20.0", units="ns", comment=""),
        "TSET": TimingSpec(value="5.0", units="ns", comment=""),
    }
    diff = diff_timing_specs(
        suite_name="BSCAN_HV",
        spec_type="port",
        spec_name="BSCAN",
        old_specs=old,
        new_specs=new,
    )
    print("=== Port Spec Diff ===")
    if diff:
        print(f"Suite: {diff.suite_name}")
        print(f"Type: {diff.spec_type}, Name: {diff.spec_name}")
        print(f"Added: {list(diff.added.keys())}")
        print(f"Removed: {list(diff.removed.keys())}")
        print(f"Changed: {list(diff.changed.keys())}")
    else:
        print("No diff")
    print()


def demo_eqnset_spec_diff():
    """Demo: Regular Spec mode diff (EQNSET + SPECSET)."""
    old_block = TimingEqnSetBlock(
        eqnset_index=1,
        eqnset_name="TIM1",
        specset_index=1,
        specset_name="SPS1",
        specs={
            "TCLK": TimingSpec(value="10.0", units="ns"),
            "TPER": TimingSpec(value="20.0", units="ns"),
        },
    )
    new_block = TimingEqnSetBlock(
        eqnset_index=1,
        eqnset_name="TIM1",
        specset_index=1,
        specset_name="SPS1",
        specs={
            "TCLK": TimingSpec(value="10.0", units="ns"),
            "TPER": TimingSpec(value="25.0", units="ns"),
            "TSET": TimingSpec(value="5.0", units="ns"),
        },
    )
    diff = diff_timing_eqnset_blocks(
        suite_name="C1_HV",
        old_block=old_block,
        new_block=new_block,
    )
    print("=== EQNSET Spec Diff ===")
    if diff:
        print(f"Suite: {diff.suite_name}")
        print(f"Type: {diff.spec_type}, Name: {diff.spec_name}")
        print(f"Added: {list(diff.added.keys())}")
        print(f"Removed: {list(diff.removed.keys())}")
        print(f"Changed: {list(diff.changed.keys())}")
        for name, (o, n) in diff.changed.items():
            print(f"  ~ {name}: value {o.value} -> {n.value}")
    else:
        print("No diff")
    print()


def demo_eqnset_full_diff():
    """Demo: Full EQNSET block diff with pins and timingsets."""
    old_block = TimingEqnSetBlock(
        eqnset_index=4,
        eqnset_name="gen_tp1_BSCAN",
        specset_index=1,
        specset_name="SPS1",
        specs={"per_40": TimingSpec(value="50", units="ns")},
        pins_groups={
            "GPIOC_5": TimingPinConfig(d1="0.0*per_40", r1="0.725*per_40"),
            "GPIOC_1": TimingPinConfig(d1="0.0*per_40", d2="0.25*per_40", r1="0.225*per_40"),
        },
        timingsets={1: TimingSetConfig(index=1, name="gen_tp1_BSCAN", period="per_40")},
    )
    new_block = TimingEqnSetBlock(
        eqnset_index=4,
        eqnset_name="gen_tp1_BSCAN",
        specset_index=1,
        specset_name="SPS1",
        specs={"per_40": TimingSpec(value="50", units="ns")},
        pins_groups={
            "GPIOC_5": TimingPinConfig(d1="0.0*per_40", r1="0.725*per_40"),
            "GPIOC_1": TimingPinConfig(d1="0.0*per_40", d2="0.30*per_40", r1="0.225*per_40"),
            "NEW_PINS": TimingPinConfig(d1="0.0*per_40"),
        },
        timingsets={1: TimingSetConfig(index=1, name="gen_tp1_BSCAN", period="per_40")},
    )
    diff = diff_timing_eqnset_blocks_full(
        suite_name="BSCAN_HV",
        old_block=old_block,
        new_block=new_block,
    )
    print("=== Full EQNSET Diff ===")
    if diff:
        print(f"Suite: {diff.suite_name}")
        print(f"EQNSET: {diff.eqnset_index} \"{diff.eqnset_name}\"")
        print(f"Specs Added: {list(diff.specs_added.keys())}")
        print(f"Specs Removed: {list(diff.specs_removed.keys())}")
        print(f"Specs Changed: {list(diff.specs_changed.keys())}")
        print(f"Pins Added: {list(diff.pins_added.keys())}")
        print(f"Pins Removed: {list(diff.pins_removed.keys())}")
        print(f"Pins Changed: {list(diff.pins_changed.keys())}")
        for name, (o, n) in diff.pins_changed.items():
            print(f"  ~ {name}: {o.all_fields()} -> {n.all_fields()}")
        print(f"Timingsets Added: {list(diff.timingsets_added.keys())}")
        print(f"Timingsets Removed: {list(diff.timingsets_removed.keys())}")
        print(f"Timingsets Changed: {list(diff.timingsets_changed.keys())}")
    else:
        print("No diff")
    print()


def demo_no_changes():
    """Demo: identical specs produce no diff."""
    specs = {
        "TCLK": TimingSpec(value="10.0", units="ns"),
    }
    diff = diff_timing_specs(
        suite_name="SAME",
        spec_type="port",
        spec_name="TEST",
        old_specs=specs,
        new_specs=specs,
    )
    print("=== Identical Specs ===")
    print("Diff is None" if diff is None else f"Unexpected diff: {diff}")
    print()


if __name__ == "__main__":
    demo_port_spec_diff()
    demo_eqnset_spec_diff()
    demo_eqnset_full_diff()
    demo_no_changes()
