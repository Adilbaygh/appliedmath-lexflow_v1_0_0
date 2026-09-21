"""Checks of the randomized robustness suite (Section 4.10, Appendix A.5)."""

from __future__ import annotations

from dataclasses import replace
from fractions import Fraction

from appliedmath_lexflow.robustness import (
    FAMILIES,
    GATES,
    TOLERANCE,
    check,
    generate_instances,
    run_suite,
    summarize,
)
from appliedmath_lexflow.stage1 import solve_stage1_closed_form


def _small(count: int = 3):
    return tuple(replace(f, count=count) for f in FAMILIES)


def test_generator_is_deterministic() -> None:
    first = [m for _, m in generate_instances(_small(2))]
    second = [m for _, m in generate_instances(_small(2))]
    assert first == second


def test_prescribed_families_plant_the_expected_guarantee() -> None:
    # In the prescribed families lambda* is fixed by the construction:
    # min{1, ratio_source, ratio_edge}, or the tie value for the degenerate one.
    for fam, model in generate_instances(_small(3)):
        if fam.capacity_rule != "prescribed":
            continue
        expected = min(Fraction(1), fam.kwargs["ratio_source"], fam.kwargs["ratio_edge"])
        assert solve_stage1_closed_form(model).lambda_star == expected


def test_independent_families_do_not_plant_the_bottleneck() -> None:
    # With capacities drawn independently of the loads, the capacity-to-load
    # ratios of a family are not all equal, so the minimizer is not known in
    # advance: at least one instance must have a ratio spread across resources.
    spreads = []
    for fam, model in generate_instances(_small(4)):
        if fam.capacity_rule != "independent":
            continue
        closed = solve_stage1_closed_form(model)
        ratios = [
            model.edge_capacity[k][e] / load
            for (k, e), load in closed.edge_loads.items() if load > 0
        ]
        spreads.append(max(ratios) / min(ratios))
    assert spreads and all(s > 1 for s in spreads)


def test_named_bottlenecks_are_tight_and_gates_hold() -> None:
    # Theorem 1: every minimizer of (25) is tight at every Stage-1 optimum.
    for fam, model in generate_instances(_small(3)):
        row = check(model)
        for gate in GATES:
            assert float(row[gate]) <= TOLERANCE[gate], (fam.key, gate, row[gate])
        if row["bottleneck_count"] > 0:
            assert row["bottleneck_identified"], (fam.key, model.name)


def test_summary_counts_add_up() -> None:
    rows = run_suite(_small(2))
    table = summarize(rows)
    total = table[-1]
    assert total["family"] == "all"
    assert total["instances"] == len(rows) == 2 * len(FAMILIES)
    assert total["instances"] == sum(t["instances"] for t in table[:-1])
    assert total["stage3_active"] == sum(t["stage3_active"] for t in table[:-1])
    classified = (total["source_bound"] + total["edge_bound"]
                  + total["source_and_edge_tied"] + total["unconstrained"])
    assert classified == total["instances"]


def test_stage3_outcome_is_consistent_with_the_stage2_face() -> None:
    # Stage 3 can lower Omega only if the Stage-2 optimum is not unique.
    for _, model in generate_instances(_small(3)):
        row = check(model)
        if row["stage3_active"]:
            assert not row["stage2_optimum_unique"], model.name
        if row["stage2_optimum_unique"]:
            assert row["omega_stage3"] <= row["omega_stage2"] + 1e-9


def test_suite_uses_the_section_2_9_thresholds() -> None:
    assert TOLERANCE["G1_closed_vs_lp"] == 5e-7
    assert TOLERANCE["G5_physical_abs"] == 5e-7
    assert TOLERANCE["G6_floor"] == 5e-7
    assert TOLERANCE["G7_satisfaction"] == 1e-8
    assert TOLERANCE["G8_variation_excess"] == 5e-7
    assert TOLERANCE["G3_operator_balance"] == 0.0
    assert TOLERANCE["G4_node_residual"] == 0.0
