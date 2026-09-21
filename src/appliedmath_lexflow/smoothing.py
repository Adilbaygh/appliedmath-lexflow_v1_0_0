"""Alternative Stage-3 smoothness criteria.

Stage 3 of the model minimizes Omega(r), the unweighted sum of consecutive
service-ratio changes (21), over the Stage-2 optimal face. This module solves
the same Stage 3 -- same face, so lambda* and S* are preserved exactly -- with
four criteria, and evaluates every solution under all four, so that the
dependence of the conclusions on the smoothness definition can be read off:

``ratio``            sum_j |r_kf - r_k-1,f|                      (the model, (21))
``demand_weighted``  sum_j omega_j |r_kf - r_k-1,f|, omega_j the mean demand of
                     the two periods divided by the mean over all pairs
``volume``           sum_j |d_kf r_kf - d_k-1,f r_k-1,f|         (delivered volume)
``max_jump``         max_j |r_kf - r_k-1,f|                      (largest single jump;
                     its optimum is the smallest uniform per-block variation
                     limit that the Stage-2 face admits)
"""

from __future__ import annotations

import numpy as np
from scipy.optimize import linprog

from .domain import Benchmark
from .lexicographic import solve_three_stage, temporal_pairs, weighted_coefficients
from .stage1 import physical_matrices

VARIANTS = ("ratio", "demand_weighted", "volume", "max_jump")
_HIGHS = {"primal_feasibility_tolerance": 1e-9, "dual_feasibility_tolerance": 1e-9}


def _pair_data(model: Benchmark):
    pairs = temporal_pairs(model)
    d_left = np.array([float(model.demand[k][f]) for (k, f), _ in pairs])
    d_right = np.array([float(model.demand[k][f]) for _, (k, f) in pairs])
    return pairs, d_left, d_right


def evaluate(model: Benchmark, ratios) -> dict[str, float]:
    """All four criteria at one allocation."""
    pairs, d_left, d_right = _pair_data(model)
    if not pairs:
        return {v: 0.0 for v in VARIANTS}
    left = np.array([ratios[a] for a, _ in pairs])
    right = np.array([ratios[b] for _, b in pairs])
    diff = np.abs(right - left)
    mean_d = (d_left + d_right) / 2.0
    omega = mean_d / mean_d.mean()
    return {
        "ratio": float(diff.sum()),
        "demand_weighted": float((omega * diff).sum()),
        "volume": float(np.abs(d_right * right - d_left * left).sum()),
        "max_jump": float(diff.max()),
    }


def solve_stage3_variant(model: Benchmark, variant: str, solution=None):
    """Stage 3 over the Stage-2 optimal face with the chosen criterion."""
    if variant not in VARIANTS:
        raise ValueError(f"unknown smoothness variant {variant!r}")
    solution = solution or solve_three_stage(model)
    lam = float(solution.lambda_closed_form)
    records = model.active_records
    n = len(records)
    index = {rec: i for i, rec in enumerate(records)}
    physical_a, physical_b, _ = physical_matrices(model)
    weighted = weighted_coefficients(model, records)
    w_star = float(weighted @ np.array([solution.stage2.ratios[r] for r in records]))
    pairs, d_left, d_right = _pair_data(model)
    p = len(pairs)
    if p == 0:
        return dict(solution.stage3.ratios)

    single = variant == "max_jump"
    m = 1 if single else p                      # auxiliary variables
    if variant == "demand_weighted":
        mean_d = (d_left + d_right) / 2.0
        cost = mean_d / mean_d.mean()
    else:
        cost = np.ones(m)
    objective = np.concatenate([np.zeros(n), cost])

    rows, rhs = [], []
    for row, bound in zip(physical_a, physical_b):
        rows.append(np.concatenate([row, np.zeros(m)]))
        rhs.append(float(bound))
    for j, (left, right) in enumerate(pairs):
        cl = d_left[j] if variant == "volume" else 1.0
        cr = d_right[j] if variant == "volume" else 1.0
        aux = 0 if single else j
        for sign in (1.0, -1.0):
            row = np.zeros(n + m)
            row[index[right]] = sign * cr
            row[index[left]] = -sign * cl
            row[n + aux] = -1.0
            rows.append(row)
            rhs.append(0.0)
    result = linprog(
        objective,
        A_ub=np.vstack(rows), b_ub=np.asarray(rhs),
        A_eq=np.concatenate([weighted, np.zeros(m)]).reshape(1, -1),
        b_eq=np.array([w_star]),
        bounds=[(lam, 1.0)] * n + [(0.0, None)] * m,
        method="highs", options=_HIGHS,
    )
    if not result.success:
        raise RuntimeError(f"Stage 3 ({variant}) failed: {result.message}")
    return {rec: float(result.x[i]) for i, rec in enumerate(records)}


def cross_evaluation(model: Benchmark) -> list[dict[str, object]]:
    """One row per optimized criterion, with all four criteria evaluated."""
    solution = solve_three_stage(model)
    rows = []
    stage2 = evaluate(model, solution.stage2.ratios)
    rows.append({"benchmark": model.name, "optimized": "stage2_vertex",
                 **{f"omega_{k}": v for k, v in stage2.items()}})
    for variant in VARIANTS:
        ratios = solve_stage3_variant(model, variant, solution)
        values = evaluate(model, ratios)
        rows.append({"benchmark": model.name, "optimized": variant,
                     **{f"omega_{k}": v for k, v in values.items()},
                     "minimum_ratio": min(ratios.values()),
                     "weighted_satisfaction_minus_stage2": (
                         float(weighted_coefficients(model, model.active_records)
                               @ np.array([ratios[r] for r in model.active_records]))
                         / float(weighted_coefficients(model, model.active_records).sum())
                         - solution.stage2.weighted_satisfaction)})
    return rows


def attainment_summary(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    """How close each criterion's optimum comes to the optimum of the others.

    For every pair (optimized criterion A, evaluated criterion B) the entry is
    the median, over instances where Stage 3 has freedom under B, of
    (B(stage2) - B(r_A)) / (B(stage2) - B(r_B)): the share of the attainable
    reduction of B that optimizing A delivers (1 = as good as optimizing B).
    """
    import statistics

    by_model: dict[str, dict[str, dict[str, object]]] = {}
    for r in rows:
        by_model.setdefault(str(r["benchmark"]), {})[str(r["optimized"])] = r
    out = []
    for a in VARIANTS:
        entry: dict[str, object] = {"optimized": a}
        for b in VARIANTS:
            shares = []
            for data in by_model.values():
                base = float(data["stage2_vertex"][f"omega_{b}"])
                best = float(data[b][f"omega_{b}"])
                if base - best > 1e-9:
                    got = float(data[a][f"omega_{b}"])
                    shares.append((base - got) / (base - best))
            entry[f"share_of_attainable_{b}_reduction"] = (
                statistics.median(shares) if shares else None)
            entry[f"instances_with_{b}_freedom"] = len(shares)
        out.append(entry)
    return out
