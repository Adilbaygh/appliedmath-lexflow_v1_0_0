"""Regression tests for the corrected, solver-independent Results.

These lock in the two defects fixed in the Results block:

* the epsilon-tolerance leak that let Stage 3 undercut the exact Stage-2 optimum
  and report a temporal variation *below* the true minimum, and
* the reporting of the single-vertex Stage-2 variation (0.75) and a
  non-reproducible "46.7% reduction" as if it were an invariant.
"""

from fractions import Fraction
from pathlib import Path

from appliedmath_lexflow.io import load_benchmark
from appliedmath_lexflow.lexicographic import solve_three_stage
from appliedmath_lexflow.robust import (
    price_of_fairness,
    solve_leximin,
    stage2_variation_bounds,
)

DATA = Path(__file__).resolve().parents[1] / "Data" / "benchmarks"


def test_stage3_preserves_stage2_exactly() -> None:
    """Stage 3 must sit inside the EXACT Stage-2 optimal face (no eps leak)."""
    for name in (
        "temporal_lexicographic",
        "branching_shared_edge_bottleneck",
        "star_edge_bottleneck",
    ):
        solution = solve_three_stage(load_benchmark(DATA / f"{name}.json"))
        # Preservation is now an equality, so satisfaction matches to float noise,
        # never the old ~8e-9 drop below Stage 2.
        assert abs(
            solution.stage3.weighted_satisfaction - solution.stage2.weighted_satisfaction
        ) <= 1e-9


def test_stage3_variation_not_below_true_minimum() -> None:
    """The old leak reported Omega3 = 0.39999997... (below the true 0.40)."""
    model = load_benchmark(DATA / "temporal_lexicographic.json")
    solution = solve_three_stage(model)
    bounds = stage2_variation_bounds(model)
    assert bounds is not None
    assert solution.stage3.temporal_variation >= bounds.omega_min - 1e-9
    assert abs(solution.stage3.temporal_variation - 0.40) <= 1e-6


def test_temporal_variation_bounds_are_invariant() -> None:
    """Omega over the Stage-2 face ranges over [2/5, 21/20]; 0.75 is one vertex."""
    model = load_benchmark(DATA / "temporal_lexicographic.json")
    solution = solve_three_stage(model)
    bounds = stage2_variation_bounds(model)
    assert bounds is not None
    assert bounds.omega_min_exact == Fraction(2, 5)
    assert bounds.omega_max_exact == Fraction(21, 20)
    # The single-vertex value the solver returned lies strictly inside the range,
    # so it is not a well-defined result on its own.
    assert bounds.omega_min - 1e-9 <= solution.stage2.temporal_variation <= bounds.omega_max + 1e-9
    assert bounds.omega_max > solution.stage2.temporal_variation + 1e-6
    assert abs(bounds.reduction_fraction - (0.65 / 1.05)) <= 1e-9


def test_leximin_is_unique_and_smooth() -> None:
    """Leximin gives a single vector at the Stage-1 floor with minimal variation."""
    model = load_benchmark(DATA / "temporal_lexicographic.json")
    lex = solve_leximin(model)
    solution = solve_three_stage(model)
    assert abs(lex.minimum_ratio - float(solution.lambda_closed_form)) <= 1e-9
    # progressive filling produces strictly increasing freeze levels
    assert all(b > a - 1e-12 for a, b in zip(lex.levels, lex.levels[1:]))
    # leximin matches Stage-2 satisfaction and is at least as smooth as Stage 3
    assert lex.weighted_satisfaction >= solution.stage2.weighted_satisfaction - 1e-9
    assert lex.temporal_variation <= solution.stage3.temporal_variation + 1e-9


def test_leximin_handles_binding_capacity_and_guards_size() -> None:
    """Regression: tie_bottleneck saturates source AND edge at lambda=3/4.

    The freeze test used to demand r >= level exactly against that saturated
    capacity with an over-tight 1e-9 tolerance and HiGHS reported 'infeasible'.
    With the slack it must solve cleanly. The size guard must also refuse an
    oversized request with a ValueError (never an infeasible RuntimeError).
    """
    import pytest

    tie = load_benchmark(DATA / "tie_bottleneck.json")
    lex = solve_leximin(tie)  # binding source + edge; must not raise
    assert abs(lex.minimum_ratio - 0.75) <= 1e-9

    temporal = load_benchmark(DATA / "temporal_lexicographic.json")
    with pytest.raises(ValueError):
        solve_leximin(temporal, max_records=2)


def test_price_of_fairness_branching() -> None:
    """The branching benchmark pays a small but nonzero throughput price."""
    pof = price_of_fairness(load_benchmark(DATA / "branching_shared_edge_bottleneck.json"))
    assert pof.efficiency_optimum >= pof.fair_delivery
    assert 0.011 <= pof.price_of_fairness <= 0.013
