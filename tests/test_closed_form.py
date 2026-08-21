from pathlib import Path

from appliedmath_lexflow.examples import load_all_benchmarks
from appliedmath_lexflow.stage1 import solve_stage1_closed_form, solve_stage1_lp

DATA = Path(__file__).resolve().parents[1] / "Data" / "benchmarks"


def test_closed_form_matches_lp() -> None:
    for model in load_all_benchmarks(DATA):
        closed = solve_stage1_closed_form(model)
        lp = solve_stage1_lp(model)
        assert abs(float(closed.lambda_star) - lp.lambda_star) <= 5e-7
