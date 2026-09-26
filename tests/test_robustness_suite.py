"""Checks of the randomized robustness suite (Section 4.10, Appendix A.5)."""

from __future__ import annotations

from dataclasses import replace
from fractions import Fraction

from appliedmath_lexflow.robustness import (
    FAMILIES,
    FAMILIES_LOAD_INDEPENDENT,
    GATES,
    LI_BRANCHING,
    LI_DEMAND_MEAN,
    LI_DEPTH,
    LI_EDGE_SCALE,
    LI_ETA_MEAN,
    LI_NOMINAL_GROSSUP,
    LI_NOMINAL_LEAVES,
    LI_SOURCE_SCALE,
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
    # Stage 3 can lower Omega only where multiplicity was detected.
    for _, model in generate_instances(_small(3)):
        row = check(model)
        if row["stage3_active"]:
            assert not row["stage2_multiplicity_not_detected"], model.name
        if row["stage2_multiplicity_not_detected"]:
            assert row["omega_stage3"] <= row["omega_stage2"] + 1e-9


def test_load_independent_scales_come_from_declared_parameters_only() -> None:
    # The two volume scales must be functions of the declared family
    # parameters alone: nominal leaf count, mean of the declared demand
    # range and mean of the declared efficiency alphabet.  No realized load,
    # nor its median, maximum or minimum, may enter them.
    assert LI_ETA_MEAN == Fraction(7, 8)
    assert LI_DEMAND_MEAN == Fraction(41, 2)
    assert LI_NOMINAL_LEAVES == Fraction(LI_BRANCHING + 1, 2) ** LI_DEPTH
    assert LI_NOMINAL_GROSSUP == LI_ETA_MEAN ** (-LI_DEPTH)
    assert LI_SOURCE_SCALE == (
        LI_NOMINAL_LEAVES * LI_DEMAND_MEAN * LI_NOMINAL_GROSSUP)
    assert LI_EDGE_SCALE == LI_SOURCE_SCALE / Fraction(LI_BRANCHING + 1, 2)


def test_load_independent_capacities_are_scale_times_a_declared_coefficient() -> None:
    # Every capacity divided by its declared scale must be a rational on the
    # 1/1000 grid inside the declared coefficient range.  This is an exact
    # certificate that no capacity is a function of a realized load.
    families = tuple(replace(f, count=6) for f in FAMILIES_LOAD_INDEPENDENT)
    seen = 0
    for fam, model in generate_instances(families):
        assert fam.capacity_rule == "load_independent"
        for cap in model.source_capacity.values():
            u = cap / LI_SOURCE_SCALE
            assert Fraction(3, 10) <= u <= Fraction(13, 10), (model.name, u)
            assert (u * 1000).denominator == 1, (model.name, u)
            seen += 1
        for caps in model.edge_capacity.values():
            for cap in caps.values():
                v = cap / LI_EDGE_SCALE
                assert Fraction(1, 5) <= v <= Fraction(5, 2), (model.name, v)
                assert (v * 1000).denominator == 1, (model.name, v)
                seen += 1
    assert seen > 0


def test_load_independent_family_has_its_own_stream() -> None:
    # Its own seed must make its draws differ from the shared independent
    # stream, otherwise the family would repeat family 8.
    own = [m.demand for _, m in generate_instances(
        tuple(replace(f, count=3) for f in FAMILIES_LOAD_INDEPENDENT))]
    shared = [m.demand for fam, m in generate_instances(_small(3))
              if fam.key == "independent"]
    assert own and shared
    assert own != shared[:len(own)]


def test_suite_uses_the_section_2_9_thresholds() -> None:
    assert TOLERANCE["G1_closed_vs_lp"] == 5e-7
    assert TOLERANCE["G5_physical_abs"] == 5e-7
    assert TOLERANCE["G6_floor"] == 5e-7
    assert TOLERANCE["G7_satisfaction"] == 1e-8
    assert TOLERANCE["G8_variation_excess"] == 5e-7
    assert TOLERANCE["G3_operator_balance"] == 0.0
    assert TOLERANCE["G4_node_residual"] == 0.0
