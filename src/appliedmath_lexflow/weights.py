"""Stage-2 service-weight sensitivity (Appendix A.6, Tables A4 and A5).

Two analyses:

* ``weight_ratio_sweep`` -- the three-period benchmark with w1:w2 swept
  geometrically from 1:8 to 8:1 (Table A4);
* ``weighting_rules`` -- three weighting rules applied to the 20 service blocks
  of the controlled Gone Abat Jap scenario (Table A5).

The weights of Table A5 are SYNTHETIC. The dataset contains no licensed-area,
water-right or priority records, so the three rules are illustrations of how
an auditable rule would be applied, not observed weights: ``uniform`` is rule
(i) of Section 2.6; ``synthetic_rank_1_to_20`` assigns w_f = 1, ..., 20 in
block order and stands in for a pro-rata entitlement rule (ii) of the same
shape; ``synthetic_two_classes`` gives the first ten blocks w = 1 and the last
ten w = 3 and stands in for an administrative priority rule (iv).
"""

from __future__ import annotations

from dataclasses import replace
from fractions import Fraction

from .domain import Benchmark, User
from .lexicographic import solve_three_stage
from .stage1 import solve_stage1_closed_form

RATIO_SWEEP = ((1, 8), (1, 4), (1, 2), (1, 1), (2, 1), (4, 1), (8, 1))


def reweight(model: Benchmark, weights: dict[str, Fraction]) -> Benchmark:
    users = tuple(
        User(u.user_id, u.terminal, weights.get(u.user_id, u.weight))
        for u in model.users
    )
    return replace(model, users=users)


def delivered(model: Benchmark, ratios) -> dict[str, float]:
    out = {u.user_id: 0.0 for u in model.users}
    for (period, user), ratio in ratios.items():
        out[user] += ratio * float(model.demand[period][user])
    return out


def weight_ratio_sweep(model: Benchmark) -> list[dict[str, object]]:
    """Table A4. ``model`` is the three-period benchmark with users f1 and f2."""
    rows = []
    for a, b in RATIO_SWEEP:
        m = reweight(model, {"f1": Fraction(a), "f2": Fraction(b)})
        sol = solve_three_stage(m)
        x = delivered(m, sol.stage3.ratios)
        rows.append({
            "w1": a, "w2": b,
            "lambda_star": float(solve_stage1_closed_form(m).lambda_star),
            "stage2_weighted_satisfaction": sol.stage2.weighted_satisfaction,
            "X1_stage3": x["f1"], "X2_stage3": x["f2"],
            "omega_stage2": sol.stage2.temporal_variation,
            "omega_stage3": sol.stage3.temporal_variation,
        })
    return rows


def rule_weights(model: Benchmark) -> dict[str, dict[str, Fraction]]:
    blocks = [u.user_id for u in model.users]
    half = len(blocks) // 2
    return {
        "uniform": {b: Fraction(1) for b in blocks},
        "synthetic_rank_1_to_20": {b: Fraction(i + 1) for i, b in enumerate(blocks)},
        "synthetic_two_classes": {
            b: Fraction(1 if i < half else 3) for i, b in enumerate(blocks)},
    }


RULE_DESCRIPTIONS = {
    "uniform": "w_f = 1 for every block (rule (i) of Section 2.6)",
    "synthetic_rank_1_to_20": (
        "SYNTHETIC w_f = 1..20 in block order; illustrates a pro-rata "
        "entitlement rule (ii); not licensed-area data"),
    "synthetic_two_classes": (
        "SYNTHETIC w_f = 1 (first ten blocks) or 3 (last ten); illustrates an "
        "administrative priority rule (iv); not an observed priority list"),
}


def weighting_rules(model: Benchmark) -> list[dict[str, object]]:
    """Table A5. ``model`` is the controlled Gone Abat Jap scenario."""
    rows = []
    for key, w in rule_weights(model).items():
        m = reweight(model, w)
        sol = solve_three_stage(m)
        rows.append({
            "rule": key,
            "description": RULE_DESCRIPTIONS[key],
            "weights_are_observed_data": "no" if key != "uniform" else "not applicable",
            "lambda_star": float(solve_stage1_closed_form(m).lambda_star),
            "minimum_ratio_stage3": sol.stage3.minimum_ratio,
            "stage2_weighted_satisfaction": sol.stage2.weighted_satisfaction,
            "omega_stage3": sol.stage3.temporal_variation,
        })
    return rows
