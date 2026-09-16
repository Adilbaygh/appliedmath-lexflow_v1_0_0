"""Extended Stage-2 service-weight sensitivity sweep.

Table 7 of the article reports three weight vectors on the three-period
benchmark. This script widens that analysis in two directions asked for in
review: a geometric sweep of the weight ratio on the small benchmark, where
every quantity can be checked by hand, and three auditable weighting rules on
the 20-block controlled canal scenario, where the point is that the Stage-1
guarantee is invariant while the Stage-2 and Stage-3 optima are not.

Run from the repository root:

    python bench/weight_sweep.py
"""

from __future__ import annotations

import sys
from dataclasses import replace
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from appliedmath_lexflow.domain import User                     # noqa: E402
from appliedmath_lexflow.io import load_benchmark               # noqa: E402
from appliedmath_lexflow.lexicographic import solve_three_stage  # noqa: E402
from appliedmath_lexflow.stage1 import solve_stage1_closed_form  # noqa: E402


def reweight(model, weights: dict[str, Fraction]):
    users = tuple(
        User(u.user_id, u.terminal, weights.get(u.user_id, u.weight))
        for u in model.users
    )
    return replace(model, users=users)


def delivered(model, solution):
    out = {u.user_id: 0.0 for u in model.users}
    for (period, user), ratio in solution.stage3.ratios.items():
        out[user] += ratio * float(model.demand[period][user])
    return out


def small_sweep() -> None:
    model = load_benchmark(ROOT / "Data" / "benchmarks" / "temporal_lexicographic.json")
    ratios = [(1, 8), (1, 4), (1, 2), (1, 1), (2, 1), (4, 1), (8, 1)]
    print("Three-period benchmark — geometric weight sweep")
    print(f"{'w1:w2':>8} {'lambda*':>10} {'S*':>12} {'X1':>8} {'X2':>8} "
          f"{'Om(S2)':>9} {'Om(S3)':>9}")
    for a, b in ratios:
        m = reweight(model, {"f1": Fraction(a), "f2": Fraction(b)})
        closed = solve_stage1_closed_form(m)
        sol = solve_three_stage(m)
        x = delivered(m, sol)
        print(f"{f'{a}:{b}':>8} {float(closed.lambda_star):10.4f} "
              f"{sol.stage2.weighted_satisfaction:12.6f} "
              f"{x['f1']:8.2f} {x['f2']:8.2f} "
              f"{sol.stage2.temporal_variation:9.4f} "
              f"{sol.stage3.temporal_variation:9.4f}")


def canal_rules() -> None:
    model = load_benchmark(ROOT / "Data" / "benchmarks" / "gone_abat_jap.json")
    blocks = [u.user_id for u in model.users]
    rules = {
        "equal (w = 1)": {b: Fraction(1) for b in blocks},
        "entitlement proxy (w = 1..20)":
            {b: Fraction(i + 1) for i, b in enumerate(blocks)},
        "two priority classes (1 / 3)":
            {b: Fraction(1 if i < len(blocks) // 2 else 3)
             for i, b in enumerate(blocks)},
    }
    print()
    print("Controlled Gone Abat Jap scenario — auditable weighting rules")
    print(f"{'rule':32} {'lambda*':>10} {'S*':>12} {'Omega*':>12} {'min r':>9}")
    for label, w in rules.items():
        m = reweight(model, w)
        closed = solve_stage1_closed_form(m)
        sol = solve_three_stage(m)
        print(f"{label:32} {float(closed.lambda_star):10.6f} "
              f"{sol.stage2.weighted_satisfaction:12.6f} "
              f"{sol.stage3.temporal_variation:12.6f} "
              f"{sol.stage3.minimum_ratio:9.6f}")


if __name__ == "__main__":
    small_sweep()
    canal_rules()
