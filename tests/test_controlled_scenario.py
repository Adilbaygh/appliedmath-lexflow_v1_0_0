"""Table A2 and the reach-capacity statements of Appendix A.4."""

from __future__ import annotations

from pathlib import Path

from appliedmath_lexflow.io import load_benchmark
from appliedmath_lexflow.scenario import period_parameters, reach_ratios

DATA = Path(__file__).resolve().parents[1] / "Data" / "benchmarks"


def test_controlled_scenario_parameters_match_appendix_a4() -> None:
    model = load_benchmark(DATA / "gone_abat_jap.json")
    periods = {r["period"]: r for r in period_parameters(model)}
    assert len(periods) == 16
    assert sum(r["active_blocks"] for r in periods.values()) == 308
    expected_ratio = {**{str(k): 1.05 for k in range(11, 18)},
                      **{str(k): 0.85 for k in range(18, 25)},
                      "25": 0.90, "26": 0.90}
    for period, ratio in expected_ratio.items():
        assert abs(periods[period]["source_ratio"] - ratio) < 1e-9
    assert round(periods["22"]["gross_source_load"]) == 1285985
    assert round(periods["22"]["source_allocation"]) == 1093088

    reaches = reach_ratios(model)
    loaded = [r for r in reaches if r["ratio"] is not None]
    assert len(loaded) == 532 and len(reaches) - len(loaded) == 28
    binding = sorted((r["period"], r["edge"]) for r in loaded
                     if abs(r["ratio"] - 0.90) < 4e-10)
    assert binding == sorted([("11", "K6"), ("12", "K5"), ("13", "K8"), ("14", "K12"),
                              ("15", "K5"), ("16", "K5"), ("17", "K8"), ("25", "K6"),
                              ("26", "K6")])
    assert all(r["ratio"] > 1.04 for r in loaded
               if (r["period"], r["edge"]) not in binding)
