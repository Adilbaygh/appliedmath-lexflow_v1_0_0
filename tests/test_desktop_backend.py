from pathlib import Path

from appliedmath_lexflow.desktop_backend import (
    benchmark_names,
    ratio_rows,
    solve_benchmark,
    verification_rows,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_desktop_backend_uses_shared_solver() -> None:
    names = benchmark_names(PROJECT_ROOT)
    assert "temporal_lexicographic" in names

    snapshot = solve_benchmark(PROJECT_ROOT, "temporal_lexicographic")
    assert snapshot.verification_passed
    assert snapshot.solution.stage3.minimum_ratio >= float(snapshot.closed_form.lambda_star) - 5e-7
    assert snapshot.solution.stage3.temporal_variation <= snapshot.solution.stage2.temporal_variation + 5e-7
    assert len(ratio_rows(snapshot)) == len(snapshot.model.active_records)
    assert all(row[3] == "PASS" for row in verification_rows(snapshot))
