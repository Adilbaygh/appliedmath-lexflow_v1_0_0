"""Equation-level checks linking the mathematical specification to the solver."""

from fractions import Fraction
from pathlib import Path

from appliedmath_lexflow.examples import load_all_benchmarks
from appliedmath_lexflow.lexicographic import solve_three_stage
from appliedmath_lexflow.operators import (
    build_operator_exact,
    exact_node_residuals,
    flows_from_node_balance_exact,
    flows_from_operator_exact,
    user_paths,
)
from appliedmath_lexflow.stage1 import full_demand_loads, solve_stage1_closed_form

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _benchmarks():
    return load_all_benchmarks(PROJECT_ROOT / "Data" / "benchmarks")


def _weighted_numerator(model, ratios: dict[tuple[str, str], float]) -> float:
    weights = model.weight_by_user
    return sum(
        float(weights[user] * model.demand[period][user]) * ratios[(period, user)]
        for period, user in model.active_records
    )


def test_equations_for_path_operator_and_closed_form_are_exact() -> None:
    for model in _benchmarks():
        paths = user_paths(model)
        a_coeff, b_coeff = build_operator_exact(model)

        for period in model.periods:
            for user in model.users:
                path = paths[user.user_id]
                expected_source = Fraction(1)
                for edge_id in path:
                    expected_source /= model.efficiency[period][edge_id]
                assert b_coeff[(period, user.user_id)] == expected_source

                for edge_id in model.edge_ids:
                    if edge_id not in path:
                        expected_edge = Fraction(0)
                    else:
                        expected_edge = Fraction(1)
                        for downstream in path[path.index(edge_id) :]:
                            expected_edge /= model.efficiency[period][downstream]
                    assert a_coeff[(period, edge_id, user.user_id)] == expected_edge

        source_loads, edge_loads = full_demand_loads(model)
        candidates = [Fraction(1)]
        candidates.extend(
            model.source_capacity[period] / load
            for period, load in source_loads.items()
            if load > 0
        )
        candidates.extend(
            model.edge_capacity[period][edge_id] / load
            for (period, edge_id), load in edge_loads.items()
            if load > 0
        )
        assert solve_stage1_closed_form(model).lambda_star == min(candidates)


def test_independent_node_balance_and_lexicographic_objectives_match_model() -> None:
    for model in _benchmarks():
        ratios = {
            record: Fraction((index % 4) + 1, 5)
            for index, record in enumerate(model.active_records)
        }
        operator_edges, operator_source = flows_from_operator_exact(model, ratios)
        balance_edges, balance_source = flows_from_node_balance_exact(model, ratios)
        assert operator_edges == balance_edges
        assert operator_source == balance_source
        assert all(
            residual == 0
            for residual in exact_node_residuals(model, ratios, operator_edges).values()
        )

        solution = solve_three_stage(model)
        weights = model.weight_by_user
        denominator = sum(
            weights[user] * model.demand[period][user]
            for period, user in model.active_records
        )

        stage2_numerator = _weighted_numerator(model, solution.stage2.ratios)
        stage3_numerator = _weighted_numerator(model, solution.stage3.ratios)
        assert abs(solution.stage2.objective_value - stage2_numerator) <= 1e-8
        assert abs(
            solution.stage2.weighted_satisfaction
            - stage2_numerator / float(denominator)
        ) <= 1e-12
        assert abs(stage3_numerator - stage2_numerator) <= 1e-8
        assert abs(
            solution.stage3.objective_value - solution.stage3.temporal_variation
        ) <= 1e-8
