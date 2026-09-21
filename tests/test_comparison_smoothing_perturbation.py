"""Alternative rules, alternative smoothness criteria and perturbation study."""

from __future__ import annotations

from pathlib import Path

from appliedmath_lexflow.comparison import compare_model
from appliedmath_lexflow.examples import load_all_benchmarks
from appliedmath_lexflow.io import load_benchmark
from appliedmath_lexflow.perturbation import run, summarize
from appliedmath_lexflow.smoothing import VARIANTS, cross_evaluation

DATA = Path(__file__).resolve().parents[1] / "Data" / "benchmarks"


def _model(name):
    return next(m for m in load_all_benchmarks(DATA) if m.name == name)


def test_rules_that_must_keep_the_guarantee_keep_it() -> None:
    for model in load_all_benchmarks(DATA):
        if model.name == "gone_abat_jap":
            continue
        rows = {r["rule"]: r for r in compare_model(model)}
        for rule in ("three_stage", "equal_proportional", "leximin"):
            assert rows[rule]["guarantee_kept"], (model.name, rule)
        # the reference rule is compared with itself
        assert rows["three_stage"]["users_better_than_three_stage"] == 0
        assert rows["three_stage"]["users_worse_than_three_stage"] == 0
        # total-delivery maximization delivers at least as much as any rule
        top = rows["total_delivery_max"]["total_net_delivery"]
        assert all(top >= r["total_net_delivery"] - 1e-7 for r in rows.values())


def test_temporal_benchmark_rule_comparison() -> None:
    rows = {r["rule"]: r for r in compare_model(_model("temporal_lexicographic"))}
    assert abs(rows["three_stage"]["temporal_variation"] - 0.4) < 1e-7
    assert abs(rows["equal_proportional"]["total_net_delivery"] - 18.0) < 1e-9
    assert not rows["total_delivery_max"]["guarantee_kept"]


def test_each_smoothness_criterion_is_optimal_for_itself() -> None:
    for name in ("temporal_lexicographic",):
        rows = {r["optimized"]: r for r in cross_evaluation(_model(name))}
        for a in VARIANTS:
            own = rows[a][f"omega_{a}"]
            for b in VARIANTS:
                assert own <= rows[b][f"omega_{a}"] + 1e-7, (a, b)
            assert abs(rows[a]["weighted_satisfaction_minus_stage2"]) < 1e-8
            assert rows[a]["minimum_ratio"] >= 0.6 - 1e-9


def test_temporal_smoothness_values() -> None:
    rows = {r["optimized"]: r for r in cross_evaluation(_model("temporal_lexicographic"))}
    assert abs(rows["ratio"]["omega_ratio"] - 0.40) < 1e-7
    assert abs(rows["volume"]["omega_volume"] - 15.6) < 1e-6
    assert abs(rows["volume"]["omega_ratio"] - 1.05) < 1e-6
    assert abs(rows["max_jump"]["omega_max_jump"] - 0.20) < 1e-7


def test_perturbation_is_deterministic() -> None:
    model = load_benchmark(DATA / "gone_abat_jap.json")
    base_1, rows_1 = run(model, draws=2, scenarios=("demand", "correlated"))
    base_2, rows_2 = run(model, draws=2, scenarios=("demand", "correlated"))
    assert base_1 == base_2 and rows_1 == rows_2
    assert base_1["bottleneck_class"] == "source"
    assert base_1["near_set_size"] == 7
    summary = summarize(base_1, rows_1)
    assert [s["scenario"] for s in summary] == ["demand", "correlated"]
