from pathlib import Path

from appliedmath_lexflow.io import load_benchmark
from appliedmath_lexflow.lexicographic import solve_three_stage


DATA = Path(__file__).resolve().parents[1] / "Data" / "benchmarks"


def test_lexicographic_preservation_and_smoothing() -> None:
    model = load_benchmark(DATA / "temporal_lexicographic.json")
    solution = solve_three_stage(model)
    assert solution.stage2.minimum_ratio >= float(solution.lambda_closed_form) - 5e-7
    assert solution.stage3.minimum_ratio >= float(solution.lambda_closed_form) - 5e-7
    assert solution.stage3.weighted_satisfaction >= solution.stage2.weighted_satisfaction - 5e-7
    assert solution.stage3.temporal_variation < solution.stage2.temporal_variation - 1e-6
