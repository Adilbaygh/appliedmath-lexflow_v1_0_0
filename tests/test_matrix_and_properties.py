from dataclasses import replace
from pathlib import Path

import numpy as np

from appliedmath_lexflow.examples import load_all_benchmarks
from appliedmath_lexflow.operators import build_operator_exact, matrix_operator
from appliedmath_lexflow.stage1 import solve_stage1_closed_form


DATA = Path(__file__).resolve().parents[1] / "Data" / "benchmarks"


def test_matrix_operator_matches_path_operator() -> None:
    for model in load_all_benchmarks(DATA):
        exact_a, _ = build_operator_exact(model)
        for period in model.periods:
            matrix_a, edge_order = matrix_operator(model, period)
            expected = np.asarray(
                [
                    [float(exact_a[(period, edge, user)]) for user in model.user_ids]
                    for edge in edge_order
                ],
                dtype=float,
            )
            assert np.allclose(matrix_a, expected, rtol=0.0, atol=1e-13)


def test_stage1_value_is_monotone_in_capacities() -> None:
    for model in load_all_benchmarks(DATA):
        base = solve_stage1_closed_form(model).lambda_star
        larger_source = {
            period: value * 2 for period, value in model.source_capacity.items()
        }
        larger_edges = {
            period: {edge: value * 2 for edge, value in capacities.items()}
            for period, capacities in model.edge_capacity.items()
        }
        expanded = replace(
            model,
            source_capacity=larger_source,
            edge_capacity=larger_edges,
        )
        assert solve_stage1_closed_form(expanded).lambda_star >= base
