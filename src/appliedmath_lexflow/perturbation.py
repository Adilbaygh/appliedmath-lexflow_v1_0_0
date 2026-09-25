"""Parameter perturbation of the controlled Gone Abat Jap scenario.

Each scenario perturbs the published demands and efficiencies or the imposed
capacities of the controlled scenario and re-solves the three-stage model.
All perturbations are exact rationals drawn from a fixed seed, so the results
are deterministic.

Scenarios (DRAWS instances each):

``demand``      every active demand d_kf scaled by an independent factor in
                [0.90, 1.10];
``efficiency``  every reach efficiency shifted by an independent amount in
                [-0.02, +0.02] (constant over the season, capped at 1);
``capacity``    every source allocation Q_k and reach capacity C_ke scaled by an
                independent factor in [0.90, 1.10];
``combined``    the three perturbations above together, independently;
``correlated``  one shock g_k in [-1, 1] per period moves demand and losses
                together: d_kf (1 + 0.10 g_k) and eta_ke - 0.02 g_k, so that a
                hot, dry period has both higher demand and lower efficiency.

For every draw the lambda*, the set of resources attaining (25) to within a
relative 1e-6, the margin to the runner-up resource, S* and Omega* are
recorded; the summary reports how often each of them changes.
"""

from __future__ import annotations

import random
import statistics
from fractions import Fraction

from .domain import Benchmark
from .lexicographic import solve_three_stage
from .robustness import _resource_ratios, _with_capacities
from .stage1 import solve_stage1_closed_form

SEED = 20260922
DRAWS = 200
SCENARIOS = ("demand", "efficiency", "capacity", "combined", "correlated")
NEAR = Fraction(1, 10**6)
CHANGE_TOLERANCE = 1e-6
FEASIBILITY_LADDER = (1e-9, 1e-8, 1e-7, 1e-6)


def _factor(rng, spread_permille: int) -> Fraction:
    return Fraction(1000 + rng.randint(-spread_permille, spread_permille), 1000)


def _shift(rng, spread_permille: int) -> Fraction:
    return Fraction(rng.randint(-spread_permille, spread_permille), 1000)


def _clip_eta(value: Fraction) -> Fraction:
    return min(Fraction(1), max(Fraction(1, 100), value))


def _replace(model: Benchmark, *, demand=None, efficiency=None,
             source_capacity=None, edge_capacity=None) -> Benchmark:
    base = Benchmark(
        name=model.name, description=model.description, nodes=model.nodes,
        source=model.source, edges=model.edges, users=model.users,
        periods=model.periods,
        demand=demand if demand is not None else model.demand,
        source_capacity=model.source_capacity, edge_capacity=model.edge_capacity,
        efficiency=efficiency if efficiency is not None else model.efficiency,
        **({"node_positions": model.node_positions}
           if getattr(model, "node_positions", None) is not None else {}),
    )
    return _with_capacities(
        base,
        source_capacity if source_capacity is not None else model.source_capacity,
        edge_capacity if edge_capacity is not None else model.edge_capacity,
    )


def perturb(model: Benchmark, scenario: str, rng: random.Random) -> Benchmark:
    periods, users, edges = model.periods, model.user_ids, model.edge_ids
    demand = efficiency = source_capacity = edge_capacity = None
    if scenario in ("demand", "combined"):
        demand = {k: {u: model.demand[k][u] * _factor(rng, 100) for u in users}
                  for k in periods}
    if scenario in ("efficiency", "combined"):
        shift = {e: _shift(rng, 20) for e in edges}
        efficiency = {k: {e: _clip_eta(model.efficiency[k][e] + shift[e]) for e in edges}
                      for k in periods}
    if scenario in ("capacity", "combined"):
        source_capacity = {k: model.source_capacity[k] * _factor(rng, 100) for k in periods}
        edge_capacity = {k: {e: model.edge_capacity[k][e] * _factor(rng, 100)
                             for e in edges} for k in periods}
    if scenario == "correlated":
        g = {k: Fraction(rng.randint(-1000, 1000), 1000) for k in periods}
        demand = {k: {u: model.demand[k][u] * (1 + Fraction(1, 10) * g[k]) for u in users}
                  for k in periods}
        efficiency = {k: {e: _clip_eta(model.efficiency[k][e] - Fraction(2, 100) * g[k])
                          for e in edges} for k in periods}
    return _replace(model, demand=demand, efficiency=efficiency,
                    source_capacity=source_capacity, edge_capacity=edge_capacity)


def diagnose(model: Benchmark) -> dict[str, object]:
    closed = solve_stage1_closed_form(model)
    # The scenario carries volumes of order 1e6 m3 while the ratios are of
    # order one; for a few perturbed instances HiGHS then declares the exact
    # Stage-2 preservation row infeasible at 1e-9. The feasibility tolerance is
    # relaxed step by step and the value used is recorded with the draw.
    solution, tolerance_used = None, None
    for tolerance in FEASIBILITY_LADDER:
        try:
            solution = solve_three_stage(model, feasibility_tolerance=tolerance)
            tolerance_used = tolerance
            break
        except RuntimeError:
            continue
    if solution is None:
        raise RuntimeError(f"{model.name}: three-stage solve failed at every tolerance")
    lam = closed.lambda_star
    ratios = _resource_ratios(model, closed)
    ordered = sorted(ratios.items(), key=lambda kv: kv[1])
    near = sorted(lab for lab, xi in ratios.items() if xi <= lam * (1 + NEAR))
    runner_up = next((xi for lab, xi in ordered if lab not in near), None)
    margin = float((runner_up - lam) / lam) if (runner_up is not None and lam > 0) else None
    classes = sorted({lab.split(":")[0] for lab in near})
    return {
        "lambda_star": float(lam),
        "bottleneck_argmin": closed.active_resources[0] if closed.active_resources else "",
        "bottleneck_near_set": ";".join(near),
        "bottleneck_class": "+".join(classes) if classes else "none",
        "near_set_size": len(near),
        "runner_up_margin": margin,
        "stage2_satisfaction": solution.stage2.weighted_satisfaction,
        "stage3_variation": solution.stage3.temporal_variation,
        "feasibility_tolerance": tolerance_used,
    }


def run(model: Benchmark, draws: int = DRAWS, scenarios=SCENARIOS, seed: int = SEED):
    base = diagnose(model)
    rows = []
    for s_index, scenario in enumerate(scenarios):
        rng = random.Random(seed + 1000 * s_index)
        for i in range(draws):
            row = {"scenario": scenario, "draw": i + 1}
            row.update(diagnose(perturb(model, scenario, rng)))
            rows.append(row)
    return base, rows


def summarize(base: dict[str, object], rows: list[dict[str, object]]):
    out = []
    for scenario in dict.fromkeys(r["scenario"] for r in rows):
        grp = [r for r in rows if r["scenario"] == scenario]
        lam = [float(r["lambda_star"]) for r in grp]
        s2 = [float(r["stage2_satisfaction"]) for r in grp]
        om = [float(r["stage3_variation"]) for r in grp]

        def q(values, p):
            return statistics.quantiles(values, n=20, method="inclusive")[p]

        base_set = set(str(base["bottleneck_near_set"]).split(";"))
        out.append({
            "scenario": scenario,
            "draws": len(grp),
            "lambda_star_p05": q(lam, 0), "lambda_star_median": statistics.median(lam),
            "lambda_star_p95": q(lam, 18),
            "lambda_star_changed": sum(
                1 for v in lam if abs(v - float(base["lambda_star"])) > CHANGE_TOLERANCE),
            "bottleneck_class_same": sum(
                1 for r in grp if r["bottleneck_class"] == base["bottleneck_class"]),
            "argmin_same_as_baseline": sum(
                1 for r in grp if r["bottleneck_argmin"] == base["bottleneck_argmin"]),
            "argmin_within_baseline_near_set": sum(
                1 for r in grp if r["bottleneck_argmin"] in base_set),
            "near_tie_draws_margin_below_1pct": sum(
                1 for r in grp if r["runner_up_margin"] is not None
                and float(r["runner_up_margin"]) < 0.01),
            "stage2_satisfaction_p05": q(s2, 0),
            "stage2_satisfaction_median": statistics.median(s2),
            "stage2_satisfaction_p95": q(s2, 18),
            "stage2_satisfaction_changed": sum(
                1 for v in s2 if abs(v - float(base["stage2_satisfaction"])) > CHANGE_TOLERANCE),
            "stage3_variation_p05": q(om, 0),
            "stage3_variation_median": statistics.median(om),
            "stage3_variation_p95": q(om, 18),
            "draws_solved_at_1e-9": sum(
                1 for r in grp if float(r["feasibility_tolerance"]) == 1e-9),
            "largest_tolerance_used": max(float(r["feasibility_tolerance"]) for r in grp),
            "stage3_variation_changed": sum(
                1 for v in om if abs(v - float(base["stage3_variation"])) > CHANGE_TOLERANCE),
        })
    return out
