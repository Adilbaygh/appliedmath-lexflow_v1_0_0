from pathlib import Path

from appliedmath_lexflow.examples import load_all_benchmarks
from appliedmath_lexflow.stage1 import solve_stage1_closed_form
from appliedmath_lexflow.verification import verify_operator_exact

DATA = Path(__file__).resolve().parents[1] / "Data" / "benchmarks"


def test_exact_operator_equals_node_balance() -> None:
    for model in load_all_benchmarks(DATA):
        value = solve_stage1_closed_form(model).lambda_star
        ratios = {record: value for record in model.active_records}
        check = verify_operator_exact(model, ratios)
        assert check.maximum_absolute_difference == 0
        assert check.maximum_node_residual == 0
