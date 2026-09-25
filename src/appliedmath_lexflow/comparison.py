"""Comparison of the three-stage hierarchy with alternative allocation rules.

Every rule is applied to the same physical feasible set R of (2), (10), (11):

* ``three_stage``          -- the proposed hierarchy (Stage-3 allocation);
* ``total_delivery_max``   -- maximize total net delivery sum d_kf r_kf, no floor;
* ``equal_proportional``   -- the largest common ratio, r_kf = lambda* for all
                              active records (the canonical Stage-1 vector);
* ``weighted_sum_*``       -- the single-objective model (35),
                              max a*lambda + b*S(r) - c*Omega(r)/|J|, for three
                              weight vectors (a, b, c);
* ``leximin``              -- the exact progressive-filling leximin allocation.

For each rule the table reports the minimum service ratio, whether the Stage-1
guarantee lambda* is kept, total net delivery, weighted satisfaction S, the
temporal variation Omega, and the number of users whose seasonal delivery X_f
is larger or smaller than under the three-stage solution. Computation times are
measured separately by ``bench/compare_rules.py`` because wall-clock times are
not byte-reproducible.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass
from typing import Callable

import numpy as np
from scipy.optimize import linprog

from .domain import Benchmark
from .lexicographic import (
    solve_three_stage,
    temporal_pairs,
    temporal_variation,
    weighted_coefficients,
    weighted_satisfaction,
)
from .robust import solve_leximin
from .stage1 import physical_matrices, solve_stage1_closed_form

_HIGHS = {"primal_feasibility_tolerance": 1e-9, "dual_feasibility_tolerance": 1e-9}

#: Weight vectors (a, b, c) of the single-objective model (35). Omega is divided
#: by the number of temporal pairs |J| so that all three terms lie in [0, 1].
WEIGHTED_SUM_VECTORS: dict[str, tuple[float, float, float]] = {
    "weighted_sum_balanced": (1.0, 1.0, 1.0),
    "weighted_sum_efficiency": (1.0, 5.0, 1.0),
    "weighted_sum_guarantee": (5.0, 1.0, 1.0),
}

RULE_LABELS = {
    "three_stage": "Three-stage lexicographic (proposed)",
    "total_delivery_max": "Total-delivery maximization",
    "equal_proportional": "Equal proportional allocation",
    "weighted_sum_balanced": "Weighted single objective (35), (a,b,c) = (1,1,1)",
    "weighted_sum_efficiency": "Weighted single objective (35), (a,b,c) = (1,5,1)",
    "weighted_sum_guarantee": "Weighted single objective (35), (a,b,c) = (5,1,1)",
    "leximin": "Full leximin (progressive filling)",
}

#: Relative tolerance when counting users as better or worse off.
USER_CHANGE_TOLERANCE = 1e-7


# --------------------------------------------------------------------------- #
#  rules
# --------------------------------------------------------------------------- #
def rule_three_stage(model: Benchmark) -> dict[tuple[str, str], float]:
    return dict(solve_three_stage(model).stage3.ratios)


def rule_equal_proportional(model: Benchmark) -> dict[tuple[str, str], float]:
    lam = float(solve_stage1_closed_form(model).lambda_star)
    return {rec: lam for rec in model.active_records}


def rule_total_delivery_max(model: Benchmark) -> dict[tuple[str, str], float]:
    physical_a, physical_b, records = physical_matrices(model)
    demand = np.array([float(model.demand[k][f]) for k, f in records])
    result = linprog(
        -demand, A_ub=physical_a, b_ub=physical_b,
        bounds=[(0.0, 1.0)] * len(records), method="highs", options=_HIGHS,
    )
    if not result.success:
        raise RuntimeError(f"total-delivery LP failed: {result.message}")
    return {rec: float(result.x[i]) for i, rec in enumerate(records)}


def rule_weighted_sum(model: Benchmark, a: float, b: float, c: float):
    """The single-objective model (35) with Omega normalized by |J|."""
    physical_a, physical_b, records = physical_matrices(model)
    n = len(records)
    index = {rec: i for i, rec in enumerate(records)}
    pairs = temporal_pairs(model)
    p = len(pairs)
    weighted = weighted_coefficients(model, records)
    total_weight = float(weighted.sum())

    # variables: r (n), lambda (1), z (p)
    objective = np.concatenate([
        -b * weighted / total_weight,
        [-a],
        np.full(p, c / max(p, 1)),
    ])
    rows, rhs = [], []
    for row, bound in zip(physical_a, physical_b):
        rows.append(np.concatenate([row, [0.0], np.zeros(p)]))
        rhs.append(float(bound))
    for i in range(n):  # lambda <= r_i
        row = np.zeros(n + 1 + p)
        row[i] = -1.0
        row[n] = 1.0
        rows.append(row)
        rhs.append(0.0)
    for j, (left, right) in enumerate(pairs):  # z_j >= |r_right - r_left|
        for sign in (1.0, -1.0):
            row = np.zeros(n + 1 + p)
            row[index[right]] = sign
            row[index[left]] = -sign
            row[n + 1 + j] = -1.0
            rows.append(row)
            rhs.append(0.0)
    result = linprog(
        objective, A_ub=np.vstack(rows), b_ub=np.asarray(rhs),
        bounds=[(0.0, 1.0)] * (n + 1) + [(0.0, None)] * p,
        method="highs", options=_HIGHS,
    )
    if not result.success:
        raise RuntimeError(f"weighted-sum LP failed: {result.message}")
    return {rec: float(result.x[i]) for i, rec in enumerate(records)}


def rule_leximin(model: Benchmark) -> dict[tuple[str, str], float]:
    return dict(solve_leximin(model, max_records=None).ratios)


def rules() -> dict[str, Callable[[Benchmark], dict[tuple[str, str], float]]]:
    out: dict[str, Callable] = {
        "three_stage": rule_three_stage,
        "total_delivery_max": rule_total_delivery_max,
        "equal_proportional": rule_equal_proportional,
    }
    for key, (a, b, c) in WEIGHTED_SUM_VECTORS.items():
        out[key] = (lambda m, a=a, b=b, c=c: rule_weighted_sum(m, a, b, c))
    out["leximin"] = rule_leximin
    return out


# --------------------------------------------------------------------------- #
#  metrics
# --------------------------------------------------------------------------- #
def seasonal_delivery(model: Benchmark, ratios) -> dict[str, float]:
    return {
        u: sum(float(model.demand[k][u]) * ratios.get((k, u), 0.0) for k in model.periods)
        for u in model.user_ids
    }


def metrics(model: Benchmark, ratios, reference, lambda_star: float) -> dict[str, object]:
    active = model.active_records
    minimum = min(ratios[rec] for rec in active) + 0.0  # no negative zero
    total = sum(float(model.demand[k][f]) * ratios[(k, f)] for k, f in active)
    x_rule = seasonal_delivery(model, ratios)
    x_ref = seasonal_delivery(model, reference)
    better = worse = 0
    for u in model.user_ids:
        scale = max(1.0, abs(x_ref[u]))
        if x_rule[u] > x_ref[u] + USER_CHANGE_TOLERANCE * scale:
            better += 1
        elif x_rule[u] < x_ref[u] - USER_CHANGE_TOLERANCE * scale:
            worse += 1
    return {
        "minimum_ratio": minimum,
        "guarantee_kept": bool(minimum >= lambda_star - 1e-9),
        "total_net_delivery": total,
        "weighted_satisfaction": weighted_satisfaction(model, ratios),
        "temporal_variation": temporal_variation(model, ratios),
        "users": len(model.user_ids),
        "users_better_than_three_stage": better,
        "users_worse_than_three_stage": worse,
    }


def compare_model(model: Benchmark) -> list[dict[str, object]]:
    """One row per rule for one model."""
    lambda_star = float(solve_stage1_closed_form(model).lambda_star)
    allocations = {key: fn(model) for key, fn in rules().items()}
    reference = allocations["three_stage"]
    ref_total = sum(
        float(model.demand[k][f]) * reference[(k, f)] for k, f in model.active_records
    )
    # Reviewer request (round 7): the comparison mixes instances whose service
    # weights are all equal with instances whose weights differ, while one of
    # the alternative rules maximizes the *unweighted* total. The grouping is
    # recorded per instance so that the two groups can be reported apart.
    equal_weights = len({model.weight_by_user[user] for user in model.user_ids}) == 1
    rows = []
    for key, ratios in allocations.items():
        row: dict[str, object] = {
            "benchmark": model.name,
            "rule": key,
            "rule_label": RULE_LABELS[key],
            "equal_weights": equal_weights,
            "lambda_star": lambda_star,
        }
        row.update(metrics(model, ratios, reference, lambda_star))
        row["total_delivery_relative_to_three_stage"] = (
            float(row["total_net_delivery"]) / ref_total if ref_total > 0 else 1.0
        )
        rows.append(row)
    return rows


def _percentile(values: list[float], share: float) -> float:
    """Linear-interpolation percentile, so that the range is reproducible."""
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = share * (len(ordered) - 1)
    low = int(position)
    high = min(low + 1, len(ordered) - 1)
    return ordered[low] + (position - low) * (ordered[high] - ordered[low])


def aggregate(
    rows: list[dict[str, object]], group: str = "all"
) -> list[dict[str, object]]:
    """Per-rule summary over many instances (rows from ``compare_model``).

    ``group`` is "all", "equal_weights" or "unequal_weights"; the last two keep
    only the instances whose service weights are, or are not, all equal. The
    medians are reported with the 5-95 % range across instances, because a
    median alone does not show how stable the difference between the rules is.
    """
    if group == "equal_weights":
        rows = [r for r in rows if r["equal_weights"]]
    elif group == "unequal_weights":
        rows = [r for r in rows if not r["equal_weights"]]
    elif group != "all":
        raise ValueError(f"unknown group {group!r}")
    out = []
    for key in rules():
        grp = [r for r in rows if r["rule"] == key]
        if not grp:
            continue
        users = [int(r["users"]) for r in grp]
        base = [x for x in rows if x["rule"] == "three_stage"]
        delivery = [float(r["total_delivery_relative_to_three_stage"]) for r in grp]
        variation = [float(r["temporal_variation"]) - float(t["temporal_variation"])
                     for r, t in zip(grp, base)]
        out.append({
            "group": group,
            "rule": key,
            "rule_label": RULE_LABELS[key],
            "instances": len(grp),
            "guarantee_kept": sum(1 for r in grp if r["guarantee_kept"]),
            "worst_minimum_ratio_over_lambda_star": min(
                float(r["minimum_ratio"]) / float(r["lambda_star"]) for r in grp),
            "median_minimum_ratio_over_lambda_star": statistics.median(
                float(r["minimum_ratio"]) / float(r["lambda_star"]) for r in grp),
            "median_total_delivery_relative_to_three_stage": statistics.median(
                float(r["total_delivery_relative_to_three_stage"]) for r in grp),
            "median_temporal_variation_minus_three_stage": statistics.median(
                float(r["temporal_variation"]) - float(t["temporal_variation"])
                for r, t in zip(grp, [x for x in rows if x["rule"] == "three_stage"])),
            "share_users_better": sum(int(r["users_better_than_three_stage"]) for r in grp)
            / sum(users),
            "share_users_worse": sum(int(r["users_worse_than_three_stage"]) for r in grp)
            / sum(users),
            "delivery_relative_p05": _percentile(delivery, 0.05),
            "delivery_relative_p95": _percentile(delivery, 0.95),
            "temporal_variation_difference_p05": _percentile(variation, 0.05),
            "temporal_variation_difference_p95": _percentile(variation, 0.95),
        })
    return out


@dataclass(frozen=True)
class ComparisonResult:
    per_benchmark: list[dict[str, object]]
    random_per_instance: list[dict[str, object]]
    random_summary: list[dict[str, object]]
    random_summary_by_weights: list[dict[str, object]]


def run_comparison(models: list[Benchmark], random_models: list[Benchmark]) -> ComparisonResult:
    per_benchmark = [row for m in models for row in compare_model(m)]
    random_rows = [row for m in random_models for row in compare_model(m)]
    return ComparisonResult(
        per_benchmark,
        random_rows,
        aggregate(random_rows),
        aggregate(random_rows, "equal_weights") + aggregate(random_rows, "unequal_weights"),
    )
