"""Randomized robustness suite for the three-stage lexicographic model.

The published verification exercises five hand-built rational benchmarks, a
deterministic scaling generator and one controlled canal scenario. Those
instances share a fixed topology family and a fixed way of setting the scarcity
limits, so agreement between the closed form and the linear program could in
principle be an artefact of that particular construction. This module removes
that objection: it draws instances at random from six families that vary the
topology depth, the conveyance efficiencies, the capacity ratios, the active
demand pattern, the service weights and the margin between competing
bottlenecks, and it re-checks every acceptance gate of Section 4 on each one.

Every generated instance is feasible by construction: r = 0 satisfies every
constraint of (1)-(15), because all gross loads are then zero and lambda = 0 is
admissible, so the Stage-1 feasible set is never empty and the three-stage
programme always has a solution.

Run from the repository root:

    python bench/robustness_suite.py
"""

from __future__ import annotations

import random
import sys
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from appliedmath_lexflow.domain import Benchmark, Edge, User          # noqa: E402
from appliedmath_lexflow.lexicographic import (                        # noqa: E402
    solve_three_stage,
    temporal_variation,
    weighted_satisfaction,
)
from appliedmath_lexflow.operators import build_operator_exact          # noqa: E402
from appliedmath_lexflow.stage1 import (                                # noqa: E402
    full_demand_loads,
    solve_stage1_closed_form,
    solve_stage1_lp,
)
from appliedmath_lexflow.verification import (                          # noqa: E402
    maximum_physical_violation,
    verify_operator_exact,
)

SEED = 20260916


# --------------------------------------------------------------------------- #
#  instance generation
# --------------------------------------------------------------------------- #
def _tree(rng: random.Random, depth: int, branching: int):
    """A rooted tree of the given depth; returns nodes, edges and the leaves."""
    nodes = ["s"]
    edges: list[Edge] = []
    frontier = ["s"]
    counter = 0
    for _ in range(depth):
        new_frontier = []
        for parent in frontier:
            for _ in range(rng.randint(1, branching)):
                counter += 1
                child = f"v{counter}"
                nodes.append(child)
                edges.append(Edge(f"e{counter}", parent, child))
                new_frontier.append(child)
        frontier = new_frontier
    return nodes, tuple(edges), frontier


def _route(edges, node, source="s"):
    parent = {e.head: e for e in edges}
    path = []
    while node != source:
        e = parent[node]
        path.append(e.edge_id)
        node = e.tail
    return path


def _instance(rng, *, depth, branching, periods, eta_choices, weight_choices,
              missing_rate, ratio_source, ratio_edge, tie_margin, name):
    nodes, edges, leaves = _tree(rng, depth, branching)
    users = tuple(
        User(f"f{i + 1}", leaf, rng.choice(weight_choices))
        for i, leaf in enumerate(leaves)
    )
    period_ids = tuple(f"k{i + 1}" for i in range(periods))

    efficiency = {
        k: {e.edge_id: rng.choice(eta_choices) for e in edges} for k in period_ids
    }
    demand = {
        k: {
            u.user_id: (
                Fraction(0)
                if rng.random() < missing_rate
                else Fraction(rng.randint(1, 40))
            )
            for u in users
        }
        for k in period_ids
    }
    # at least one active record per period keeps the instance non-trivial
    for k in period_ids:
        if all(v == 0 for v in demand[k].values()):
            demand[k][users[0].user_id] = Fraction(rng.randint(1, 40))

    draft = Benchmark(
        name=name, description=name, nodes=tuple(nodes), source="s", edges=edges,
        users=users, periods=period_ids, demand=demand,
        source_capacity={k: Fraction(1) for k in period_ids},
        edge_capacity={k: {e.edge_id: Fraction(1) for e in edges} for k in period_ids},
        efficiency=efficiency,
    )
    source_loads, edge_loads = full_demand_loads(draft)

    # Capacities are set as a prescribed multiple of the full-demand gross load,
    # so the binding resource — and the exact value of lambda* — is known before
    # the solver runs.
    source_capacity = {
        k: ratio_source * source_loads[k] if source_loads[k] > 0 else Fraction(1)
        for k in period_ids
    }
    edge_capacity = {
        k: {
            e.edge_id: (
                ratio_edge * edge_loads[(k, e.edge_id)]
                if edge_loads[(k, e.edge_id)] > 0
                else Fraction(1)
            )
            for e in edges
        }
        for k in period_ids
    }
    if tie_margin is not None:
        # Put one edge within tie_margin of the source ratio, so two resources
        # compete for the minimum in (25) to within that relative margin.
        k = period_ids[0]
        victim = max(
            (e.edge_id for e in edges if edge_loads[(k, e.edge_id)] > 0),
            key=lambda eid: edge_loads[(k, eid)],
            default=None,
        )
        if victim is not None:
            edge_capacity[k][victim] = (
                (ratio_source + tie_margin) * edge_loads[(k, victim)]
            )

    return Benchmark(
        name=name, description=name, nodes=tuple(nodes), source="s", edges=edges,
        users=users, periods=period_ids, demand=demand,
        source_capacity=source_capacity, edge_capacity=edge_capacity,
        efficiency=efficiency,
    )


ETA_COARSE = tuple(Fraction(x, 100) for x in range(80, 100, 5))
ETA_FINE = tuple(Fraction(x, 1000) for x in range(800, 1000, 7))
W_UNIT = (Fraction(1),)
W_WIDE = tuple(Fraction(x) for x in (1, 2, 3, 5, 8, 13, 21, 34))


@dataclass(frozen=True)
class Family:
    key: str
    label: str
    count: int
    kwargs: dict


FAMILIES = (
    Family("random_caps", "Random efficiencies and capacity ratios", 40, dict(
        depth=3, branching=3, periods=3, eta_choices=ETA_FINE,
        weight_choices=W_UNIT, missing_rate=0.0,
        ratio_source=Fraction(7, 10), ratio_edge=Fraction(13, 10), tie_margin=None)),
    Family("source_bind", "Source-binding configuration", 25, dict(
        depth=3, branching=3, periods=3, eta_choices=ETA_COARSE,
        weight_choices=W_UNIT, missing_rate=0.0,
        ratio_source=Fraction(1, 2), ratio_edge=Fraction(3), tie_margin=None)),
    Family("edge_bind", "Edge-binding configuration", 25, dict(
        depth=3, branching=3, periods=3, eta_choices=ETA_COARSE,
        weight_choices=W_UNIT, missing_rate=0.0,
        ratio_source=Fraction(3), ratio_edge=Fraction(1, 2), tie_margin=None)),
    Family("missing", "Missing-demand periods", 30, dict(
        depth=3, branching=3, periods=4, eta_choices=ETA_COARSE,
        weight_choices=W_UNIT, missing_rate=0.35,
        ratio_source=Fraction(4, 5), ratio_edge=Fraction(3, 2), tie_margin=None)),
    Family("deep", "Deeper trees (depth 5)", 20, dict(
        depth=5, branching=2, periods=3, eta_choices=ETA_COARSE,
        weight_choices=W_UNIT, missing_rate=0.1,
        ratio_source=Fraction(4, 5), ratio_edge=Fraction(3, 2), tie_margin=None)),
    Family("weights", "Heterogeneous service weights", 30, dict(
        depth=3, branching=3, periods=3, eta_choices=ETA_COARSE,
        weight_choices=W_WIDE, missing_rate=0.1,
        ratio_source=Fraction(4, 5), ratio_edge=Fraction(3, 2), tie_margin=None)),
    Family("degenerate", "Near-degenerate bottleneck ties", 30, dict(
        depth=3, branching=3, periods=3, eta_choices=ETA_COARSE,
        weight_choices=W_UNIT, missing_rate=0.0,
        ratio_source=Fraction(4, 5), ratio_edge=Fraction(3, 2),
        tie_margin=Fraction(1, 10**12))),
)


# --------------------------------------------------------------------------- #
#  checks
# --------------------------------------------------------------------------- #
def check(model: Benchmark) -> dict[str, float]:
    closed = solve_stage1_closed_form(model)
    lp = solve_stage1_lp(model)
    solution = solve_three_stage(model)

    canonical = {rec: closed.lambda_star for rec in model.active_records}
    operator = verify_operator_exact(model, canonical)
    a_coeff, b_coeff = build_operator_exact(model)

    lambda_star = float(closed.lambda_star)
    stage2 = solution.stage2
    stage3 = solution.stage3
    return {
        "closed_vs_lp": abs(lp.lambda_star - lambda_star),
        "operator_balance": float(operator.maximum_absolute_difference),
        "node_residual": float(operator.maximum_node_residual),
        "physical": maximum_physical_violation(model, stage3.ratios, a_coeff, b_coeff),
        "floor": max(0.0, lambda_star - stage3.minimum_ratio),
        "satisfaction": abs(stage3.weighted_satisfaction - stage2.weighted_satisfaction),
        "variation": max(0.0, stage3.temporal_variation - stage2.temporal_variation),
    }


GATES = ("closed_vs_lp", "operator_balance", "node_residual", "physical",
         "floor", "satisfaction", "variation")
TOLERANCE = {
    "closed_vs_lp": 1e-9, "operator_balance": 0.0, "node_residual": 0.0,
    "physical": 1e-6, "floor": 1e-9, "satisfaction": 1e-9, "variation": 1e-9,
}


def main() -> int:
    rng = random.Random(SEED)
    print(f"Randomized robustness suite — seed {SEED}")
    print(f"{'family':38} {'n':>4} " + " ".join(f"{g[:12]:>13}" for g in GATES))
    overall = dict.fromkeys(GATES, 0.0)
    total = 0
    failures = 0
    for fam in FAMILIES:
        worst = dict.fromkeys(GATES, 0.0)
        for i in range(fam.count):
            model = _instance(rng, name=f"{fam.key}_{i}", **fam.kwargs)
            res = check(model)
            for g in GATES:
                worst[g] = max(worst[g], res[g])
                if res[g] > TOLERANCE[g]:
                    failures += 1
            total += 1
        for g in GATES:
            overall[g] = max(overall[g], worst[g])
        print(f"{fam.label:38} {fam.count:>4} "
              + " ".join(f"{worst[g]:13.3e}" for g in GATES))
    print(f"{'ALL FAMILIES':38} {total:>4} "
          + " ".join(f"{overall[g]:13.3e}" for g in GATES))
    print()
    print(f"instances generated      {total}")
    print(f"feasible by construction {total}  (r = 0 is always admissible)")
    print(f"gate violations          {failures}")
    print("status                   " + ("PASS" if failures == 0 else "FAIL"))
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
