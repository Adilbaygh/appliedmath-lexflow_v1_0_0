"""Tests for the inverse design problem (minimum-cost rehabilitation).

Each test names the result it locks in:

* Theorem 1'  -- the widening plan is feasible, tight, and coordinatewise minimal;
* Corollary 1' -- the funded sets are nested, so the roadmap is a chain;
* Theorem 2'  -- ``B(tau)`` is convex, piecewise linear, with nondecreasing slope;
* Corollary 2' -- ``lambda^(B)`` inverts ``B`` and is concave;
* Lemma 3'    -- lining edge ``e`` moves exactly the loads at or above ``e``;
* Theorem 4'  -- an unrelieved epsilon-bottleneck caps the gain at epsilon, so
                 single-edge lining ascent stalls on a plateau.
"""

from __future__ import annotations

from fractions import Fraction
from pathlib import Path

import pytest

from appliedmath_lexflow.examples import load_all_benchmarks
from appliedmath_lexflow.investment import (
    apply_lining,
    budget_function,
    critical_resources,
    epsilon_bottleneck_set,
    expansion_plan,
    guarantee_for_budget,
    lambda_star,
    lining_plan,
    minimum_cost_transversal,
    mixed_plan,
    relief_edges,
    resource_table,
    widened,
)
from appliedmath_lexflow.io import load_benchmark
from appliedmath_lexflow.stage1 import solve_stage1_closed_form

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "Data" / "benchmarks"
DESIGN = ROOT / "Data" / "design"

TARGETS = (Fraction(9, 10), Fraction(19, 20), Fraction(1))


def _benchmarks():
    return load_all_benchmarks(DATA)


# ---------------------------------------------------------------- resources


def test_resource_table_reproduces_the_stage1_closed_form() -> None:
    """The design layer and the allocation layer must agree on lambda*."""
    for model in _benchmarks():
        rows = resource_table(model)
        assert lambda_star(rows) == solve_stage1_closed_form(model).lambda_star
        assert all(item.load > 0 for item in rows)


def test_gone_abat_jap_resource_count_and_critical_set() -> None:
    """The headline structural claim of the paper."""
    model = load_benchmark(DATA / "gone_abat_jap.json")
    rows = resource_table(model)
    assert len(rows) == 548
    assert len(critical_resources(model, rows)) == 18
    assert lambda_star(rows) == Fraction(489061655669511240854544523485423,
                                          575366653729073409930683320905560)


# ------------------------------------------------------------- Theorem 1'


def test_expansion_plan_is_feasible_and_tight() -> None:
    """Theorem 1': after the plan lambda* equals the target exactly."""
    for model in _benchmarks():
        for target in TARGETS:
            plan = expansion_plan(model, target)
            upgraded = widened(model, plan)
            assert lambda_star(resource_table(upgraded)) == target


def test_expansion_plan_is_coordinatewise_minimal() -> None:
    """Theorem 1': shaving any funded increment breaks feasibility."""
    model = load_benchmark(DATA / "branching_shared_edge_bottleneck.json")
    target = Fraction(19, 20)
    plan = expansion_plan(model, target)
    assert plan.increments
    for label, value in plan.increments:
        reduced = {
            other: (amount if other != label else amount - Fraction(1, 10**6))
            for other, amount in plan.increments
        }
        shaved = widened(model, plan.__class__(
            target=plan.target,
            lambda_before=plan.lambda_before,
            increments=tuple(reduced.items()),
            cost=plan.cost,
        ))
        assert lambda_star(resource_table(shaved)) < target


def test_no_expansion_needed_below_the_current_guarantee() -> None:
    for model in _benchmarks():
        current = lambda_star(resource_table(model))
        assert expansion_plan(model, current).cost == 0
        assert not expansion_plan(model, current).funded


def test_expansion_plan_rejects_targets_outside_the_unit_interval() -> None:
    model = load_benchmark(DATA / "tie_bottleneck.json")
    for bad in (Fraction(0), Fraction(-1, 2), Fraction(11, 10)):
        with pytest.raises(ValueError):
            expansion_plan(model, bad)


# ------------------------------------------------------------ Corollary 1'


def test_funded_sets_are_nested() -> None:
    """Corollary 1': S(tau1) subseteq S(tau2) whenever tau1 < tau2."""
    for model in _benchmarks():
        previous: set[str] = set()
        base = lambda_star(resource_table(model))
        for step in range(0, 21):
            target = base + (Fraction(1) - base) * Fraction(step, 20)
            if target <= 0:
                continue
            funded = set(expansion_plan(model, target).funded)
            assert previous <= funded
            previous = funded


# ------------------------------------------------------------- Theorem 2'


def test_budget_function_is_convex_with_nondecreasing_slope() -> None:
    """Theorem 2': convex, piecewise linear, diminishing returns."""
    for model in _benchmarks():
        curve = budget_function(model)
        slopes = [segment.slope for segment in curve.segments]
        assert slopes == sorted(slopes)
        counts = [segment.funded_count for segment in curve.segments]
        assert counts == sorted(counts)
        taus = [tau for tau, _ in curve.breakpoints]
        values = [value for _, value in curve.breakpoints]
        assert taus == sorted(taus)
        assert values == sorted(values)
        for i in range(1, len(values) - 1):
            left = (values[i] - values[i - 1]) / (taus[i] - taus[i - 1])
            right = (values[i + 1] - values[i]) / (taus[i + 1] - taus[i])
            assert left <= right  # convexity


def test_budget_function_matches_the_direct_plan_cost() -> None:
    """Algorithm 1 and Theorem 1' must return identical numbers."""
    for model in _benchmarks():
        curve = budget_function(model)
        base = curve.lambda_star
        for step in range(0, 41):
            target = base + (Fraction(1) - base) * Fraction(step, 40)
            if target <= 0:
                continue
            assert curve.cost(target) == expansion_plan(model, target).cost


def test_budget_is_zero_exactly_up_to_the_current_guarantee() -> None:
    """Theorem 2' (iv)."""
    for model in _benchmarks():
        curve = budget_function(model)
        base = curve.lambda_star
        assert curve.cost(base) == 0
        if base < 1:
            above = base + (Fraction(1) - base) / 100
            assert curve.cost(above) > 0


def test_budget_function_honours_unit_prices() -> None:
    model = load_benchmark(DATA / "temporal_lexicographic.json")
    plain = expansion_plan(model, Fraction(1))
    doubled = expansion_plan(
        model,
        Fraction(1),
        prices={item.label: Fraction(2) for item in resource_table(model)},
    )
    assert doubled.cost == 2 * plain.cost
    assert doubled.funded == plain.funded


# ------------------------------------------------------------ Corollary 2'


def test_guarantee_for_budget_inverts_the_budget_function() -> None:
    """Corollary 2': lambda^(B(tau)) == tau on the reachable range."""
    for model in _benchmarks():
        curve = budget_function(model)
        base = curve.lambda_star
        for step in range(0, 21):
            target = base + (Fraction(1) - base) * Fraction(step, 20)
            if target <= 0:
                continue
            assert curve.guarantee(curve.cost(target)) == target


def test_guarantee_for_budget_is_concave() -> None:
    """Corollary 2': marginal service gain per unit of budget decreases."""
    for model in _benchmarks():
        curve = budget_function(model)
        total = curve.breakpoints[-1][1]
        if total == 0:
            continue
        points = [
            (Fraction(i, 24) * total, curve.guarantee(Fraction(i, 24) * total))
            for i in range(25)
        ]
        for i in range(1, len(points) - 1):
            left = (points[i][1] - points[i - 1][1]) / (points[i][0] - points[i - 1][0])
            right = (points[i + 1][1] - points[i][1]) / (points[i + 1][0] - points[i][0])
            assert right <= left


def test_zero_budget_returns_the_current_guarantee() -> None:
    for model in _benchmarks():
        assert guarantee_for_budget(model, Fraction(0)) == lambda_star(
            resource_table(model)
        )


# --------------------------------------------------------------- Lemma 3'


def test_relief_edges_are_exactly_the_loads_that_move() -> None:
    """Lemma 3': lining e reduces L_j iff e lies at or below j on a route."""
    model = load_benchmark(DATA / "branching_shared_edge_bottleneck.json")
    before = {item.label: item.load for item in resource_table(model)}
    for edge_id in model.edge_ids:
        lined = apply_lining(model, {edge_id}, Fraction(1))
        after = {item.label: item.load for item in resource_table(lined)}
        for item in resource_table(model):
            moved = after[item.label] < before[item.label]
            predicted = edge_id in relief_edges(model, item)
            assert moved == predicted, (edge_id, item.label)


def test_lining_never_reduces_the_guarantee() -> None:
    """Monotonicity of lambda* in the efficiencies."""
    for model in _benchmarks():
        base = lambda_star(resource_table(model))
        lined = apply_lining(model, model.edge_ids, Fraction(1))
        assert lambda_star(resource_table(lined)) >= base


def test_apply_lining_validates_its_arguments() -> None:
    model = load_benchmark(DATA / "tie_bottleneck.json")
    with pytest.raises(ValueError):
        apply_lining(model, {"nonexistent"}, Fraction(1))
    with pytest.raises(ValueError):
        apply_lining(model, model.edge_ids, Fraction(3, 2))


# --------------------------------------------------------------- Theorem 4'


def test_greedy_lining_trap_single_edge_gains_nothing() -> None:
    """Theorem 4': the minimal counterexample, verified in exact arithmetic."""
    model = load_benchmark(DESIGN / "greedy_lining_trap.json")
    base = lambda_star(resource_table(model))
    assert base == Fraction(1, 2)

    for edge_id in model.edge_ids:
        single = apply_lining(model, {edge_id}, Fraction(1))
        assert lambda_star(resource_table(single)) == base  # zero gain

    joint = apply_lining(model, {"e1", "e2"}, Fraction(1))
    assert lambda_star(resource_table(joint)) == Fraction(1)


def test_epsilon_bottleneck_set_bounds_any_partial_upgrade() -> None:
    """Theorem 4': leaving one tied resource unrelieved caps lambda* at lambda*+eps."""
    model = load_benchmark(DESIGN / "greedy_lining_trap.json")
    tied = epsilon_bottleneck_set(model)
    assert {item.label for item in tied} == {"edge:k1:e1", "edge:k1:e2"}

    base = lambda_star(resource_table(model))
    for item in tied:
        # line everything that does NOT relieve this resource
        spared = set(model.edge_ids) - relief_edges(model, item)
        partial = apply_lining(model, spared, Fraction(1))
        assert lambda_star(resource_table(partial)) <= base


def test_gone_abat_jap_has_a_wide_near_tied_bottleneck_set() -> None:
    """Near-ties, not exact ties, are what makes greedy ascent fail on real data."""
    model = load_benchmark(DATA / "gone_abat_jap.json")
    rows = resource_table(model)
    assert len(epsilon_bottleneck_set(model, Fraction(0), rows)) == 1
    assert len(epsilon_bottleneck_set(model, Fraction(1, 10**9), rows)) == 7


# ------------------------------------------------------------- transversals


def test_transversal_is_exact_on_a_laminar_family() -> None:
    """Minimal members of a laminar family are disjoint, so greedy is optimal."""
    families = [
        frozenset({"e0", "e1", "e2"}),
        frozenset({"e1"}),
        frozenset({"e2"}),
    ]
    result = minimum_cost_transversal(families)
    assert result.exact
    assert result.edges == {"e1", "e2"}
    assert result.cost == 2
    assert result.minimal_sets == 2


def test_transversal_respects_costs_and_flags_non_laminar_input() -> None:
    cheap = minimum_cost_transversal(
        [frozenset({"a", "b"})], costs={"a": Fraction(5), "b": Fraction(1)}
    )
    assert cheap.edges == {"b"} and cheap.exact

    overlapping = minimum_cost_transversal(
        [frozenset({"a", "b"}), frozenset({"b", "c"}), frozenset({"c", "d"})]
    )
    assert not overlapping.exact
    assert all(
        overlapping.edges & item
        for item in (frozenset({"a", "b"}), frozenset({"b", "c"}), frozenset({"c", "d"}))
    )


def test_empty_family_needs_no_edges() -> None:
    result = minimum_cost_transversal([])
    assert result.edges == frozenset() and result.cost == 0 and result.exact


# ------------------------------------------------------- Algorithm 2 / (P3)


def test_lining_plan_escapes_the_plateau_the_greedy_step_cannot() -> None:
    """Algorithm 2 relieves the tied set jointly and reaches full service."""
    model = load_benchmark(DESIGN / "greedy_lining_trap.json")
    plan = lining_plan(model, Fraction(1), Fraction(1))
    assert plan.reached
    assert plan.lambda_before == Fraction(1, 2)
    assert plan.lambda_after == Fraction(1)
    assert set(plan.lined) == {"e1", "e2"}
    assert plan.exact_transversals


def test_lining_plan_reports_a_stall_instead_of_looping() -> None:
    """An unreachable target must terminate with reached=False."""
    model = load_benchmark(DATA / "chain_source_bottleneck.json")
    plan = lining_plan(model, Fraction(1), Fraction(1))
    assert plan.iterations <= len(model.edge_ids) + 1
    assert plan.reached or plan.stalled


def test_mixed_plan_never_costs_more_than_widening_alone() -> None:
    """(P3): lining first can only reduce the capacity still required."""
    for model in _benchmarks():
        plan = mixed_plan(model, Fraction(1), Fraction(19, 20))
        assert plan.expansion.cost <= plan.widening_only_cost
        assert plan.lambda_after_lining >= plan.lambda_before
        assert plan.saving_fraction >= 0


def test_gone_abat_jap_headline_numbers() -> None:
    """The figures quoted in the paper, to the printed precision."""
    model = load_benchmark(DATA / "gone_abat_jap.json")
    curve = budget_function(model)

    widen_100 = curve.cost(Fraction(1))
    assert round(float(widen_100)) == 1176721
    assert len(expansion_plan(model, Fraction(9, 10)).funded) == 12
    assert len(expansion_plan(model, Fraction(1)).funded) == 18

    for eta_bar, expected in ((Fraction(9, 10), 656675), (Fraction(23, 25), 378334)):
        plan = mixed_plan(model, Fraction(1), eta_bar)
        assert round(float(plan.expansion.cost)) == expected
        assert plan.expansion.cost < widen_100

    saving = mixed_plan(model, Fraction(1), Fraction(9, 10)).saving_fraction
    assert Fraction(44, 100) < saving < Fraction(45, 100)
