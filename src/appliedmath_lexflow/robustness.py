"""Randomized robustness suite for the three-stage lexicographic model.

The suite answers two different questions and keeps them apart.

1. *Implementation agreement under prescribed bottlenecks.* The seven
   original families (seed 20260916) set every capacity as a prescribed multiple
   of the corresponding full-demand gross load. The binding resource class and
   the exact value of lambda* are therefore known before any solver runs; these
   families test that the closed form, the linear programs and the exact
   operator agree, but they do not test whether the closed form *finds* an
   unknown bottleneck, and because every resource of a class carries the same
   ratio they leave Stage 3 almost nothing to choose between.

2. *Bottleneck identification and Stage-3 activity beyond prescribed ratios.*
   Three further families (seed 20260921) no longer set each capacity as a
   prescribed multiple of its own load. In two of them (140 instances) the
   source allocations and the reach capacities are drawn independently of their
   own loads, so the binding resource is not known in advance; one uses
   canal-like data (efficiencies from a few lining classes, uniform weights)
   and the other generic data (a fine efficiency grid and heterogeneous
   weights), which separates the effect of ties in the data on the size of the
   Stage-2 optimal face. The third family (``seasonal_supply``, 60 instances)
   holds one seasonal source allocation against period-varying demand and gives
   each reach 1.2-2.0 times its own largest load; the source is therefore the
   binding class by construction there, and that family tests seasonal supply
   rather than bottleneck identification. Its capacity rule is labelled
   ``seasonal`` rather than ``independent`` for that reason.

On every instance, in addition to the acceptance gates, the suite identifies
the bottleneck in two independent ways: every resource the closed form names as
a minimizer of (25) must be tight at the Stage-1 LP optimum and at the Stage-3
optimum (Theorem 1 requires this of every Stage-1 optimal allocation), and the
Stage-1 LP alone must confirm it -- relaxing all other resources tenfold leaves
the LP guarantee unchanged, relaxing the named resources by 0.1% raises it.
It also records whether the Stage-2 optimum is a single point, which is the
structural condition under which Stage 3 is redundant, and how often Stage 3
lowers the temporal variation.

The acceptance thresholds are those of Section 2.9, unchanged; the relative
physical residual G5r (violation divided by the capacity of the same resource)
is added because the absolute residual G5 scales with the volumes drawn.

Every generated instance is feasible by construction: r = 0 satisfies every
constraint of (1)-(15), because all gross loads are then zero and lambda = 0 is
admissible, so the Stage-1 feasible set is never empty and the three-stage
programme always has a solution.

The original seven families consume their random stream exactly as in release
0.5.1, so their instances are unchanged; the new families use a separate stream.
"""

from __future__ import annotations

import random
import statistics
import zlib
from dataclasses import dataclass, field
from fractions import Fraction
from typing import Callable

import numpy as np
from scipy.optimize import linprog

from .domain import Benchmark, Edge, User
from .lexicographic import solve_three_stage, weighted_coefficients
from .operators import build_operator_exact
from .stage1 import (
    full_demand_loads,
    physical_matrices,
    solve_stage1_closed_form,
    solve_stage1_lp,
)
from .verification import maximum_physical_violation, verify_operator_exact

SEED_PRESCRIBED = 20260916
SEED_INDEPENDENT = 20260921

#: A resource named by the closed form is counted as tight when its relative
#: slack (C - B(r)) / C at the LP optimum does not exceed this value.
TIGHTNESS_TOLERANCE = 1e-9
#: Stage 3 is counted as active when it lowers Omega by more than this amount.
STAGE3_ACTIVITY_THRESHOLD = 1e-9
#: A ratio is counted as moved by Stage 3 when it changes by more than this.
RATIO_MOVE_THRESHOLD = 1e-9
#: Resources whose capacity-to-load ratio lies within this relative margin of
#: lambda* form the near-minimizer set used by the LP-based identification test
#: (the manuscript reads the diagnosis of (25) "to within the precision of the
#: data"; the near-degenerate family places a competitor at 1e-12).
NEAR_MINIMIZER_MARGIN = Fraction(1, 10**6)
#: Relaxation factors of the LP-based identification test.
RELAX_OTHERS = Fraction(10)
RELAX_NAMED = Fraction(1001, 1000)
#: The Stage-2 optimal face is counted as a single point when a random linear
#: functional varies over it by no more than this amount.
FACE_WIDTH_THRESHOLD = 1e-7


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


def _draft(rng, *, depth, branching, periods, eta_choices, weight_choices,
           missing_rate, name):
    """Topology, weights, efficiencies and demands; capacities are placeholders."""
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

    return Benchmark(
        name=name, description=name, nodes=tuple(nodes), source="s", edges=edges,
        users=users, periods=period_ids, demand=demand,
        source_capacity={k: Fraction(1) for k in period_ids},
        edge_capacity={k: {e.edge_id: Fraction(1) for e in edges} for k in period_ids},
        efficiency=efficiency,
    )


def _with_capacities(draft: Benchmark, source_capacity, edge_capacity) -> Benchmark:
    return Benchmark(
        name=draft.name, description=draft.description, nodes=draft.nodes,
        source=draft.source, edges=draft.edges, users=draft.users,
        periods=draft.periods, demand=draft.demand,
        source_capacity=source_capacity, edge_capacity=edge_capacity,
        efficiency=draft.efficiency,
    )


def prescribed_instance(rng, *, depth, branching, periods, eta_choices,
                        weight_choices, missing_rate, ratio_source, ratio_edge,
                        tie_margin, name) -> Benchmark:
    """Capacities are a prescribed multiple of the full-demand gross load."""
    draft = _draft(rng, depth=depth, branching=branching, periods=periods,
                   eta_choices=eta_choices, weight_choices=weight_choices,
                   missing_rate=missing_rate, name=name)
    source_loads, edge_loads = full_demand_loads(draft)
    period_ids = draft.periods
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
            for e in draft.edges
        }
        for k in period_ids
    }
    if tie_margin is not None:
        # Put one edge within tie_margin of the source ratio, so two resources
        # compete for the minimum in (25) to within that relative margin.
        k = period_ids[0]
        victim = max(
            (e.edge_id for e in draft.edges if edge_loads[(k, e.edge_id)] > 0),
            key=lambda eid: edge_loads[(k, eid)],
            default=None,
        )
        if victim is not None:
            edge_capacity[k][victim] = (
                (ratio_source + tie_margin) * edge_loads[(k, victim)]
            )
    return _with_capacities(draft, source_capacity, edge_capacity)


def _uniform(rng: random.Random, low: Fraction, high: Fraction) -> Fraction:
    """An exact rational drawn uniformly on a grid of 1/1000 in [low, high]."""
    lo, hi = int(low * 1000), int(high * 1000)
    return Fraction(rng.randint(lo, hi), 1000)


def _median(values) -> Fraction:
    positive = sorted(v for v in values if v > 0)
    return statistics.median_low(positive) if positive else Fraction(1)


def independent_instance(rng, *, name, eta_choices, weight_choices) -> Benchmark:
    """Source and reach capacities drawn independently of the loads.

    Q_k = median(L^src) * U(0.3, 1.3) for each period separately and
    C_ke = median(L_edge) * U(0.2, 2.5) for each reach and period separately,
    so any source or any reach may bind and the binding resource is not known
    before the closed form is evaluated.
    """
    depth = rng.choice((3, 4, 5))
    draft = _draft(
        rng, depth=depth, branching=3 if depth == 3 else 2,
        periods=rng.choice((3, 4)), eta_choices=eta_choices,
        weight_choices=weight_choices, missing_rate=0.1, name=name,
    )
    source_loads, edge_loads = full_demand_loads(draft)
    src_med = _median(source_loads.values())
    edge_med = _median(edge_loads.values())
    source_capacity = {
        k: src_med * _uniform(rng, Fraction(3, 10), Fraction(13, 10))
        for k in draft.periods
    }
    edge_capacity = {
        k: {e.edge_id: edge_med * _uniform(rng, Fraction(1, 5), Fraction(5, 2))
            for e in draft.edges}
        for k in draft.periods
    }
    return _with_capacities(draft, source_capacity, edge_capacity)


def seasonal_supply_instance(rng, *, name, eta_choices, weight_choices) -> Benchmark:
    """A constant seasonal source allocation against period-varying demand.

    Q_k = median_k(L_k^src) * U(0.6, 1.0), the same value in every period, and
    reach capacities C_e = max_k L_ke * U(1.2, 2.0), also constant over the
    season. Scarcity therefore varies from period to period, which is the
    situation of a headworks allocation fixed for the season.
    """
    depth = rng.choice((3, 4))
    draft = _draft(
        rng, depth=depth, branching=3 if depth == 3 else 2,
        periods=rng.choice((3, 4, 5)), eta_choices=eta_choices,
        weight_choices=weight_choices, missing_rate=0.1, name=name,
    )
    source_loads, edge_loads = full_demand_loads(draft)
    supply = _median(source_loads.values()) * _uniform(rng, Fraction(3, 5), Fraction(1))
    source_capacity = {k: supply for k in draft.periods}
    edge_capacity_constant = {
        e.edge_id: max(
            (edge_loads[(k, e.edge_id)] for k in draft.periods), default=Fraction(0)
        ) * _uniform(rng, Fraction(6, 5), Fraction(2))
        for e in draft.edges
    }
    edge_capacity = {
        k: {
            eid: (cap if cap > 0 else Fraction(1))
            for eid, cap in edge_capacity_constant.items()
        }
        for k in draft.periods
    }
    return _with_capacities(draft, source_capacity, edge_capacity)


ETA_COARSE = tuple(Fraction(x, 100) for x in range(80, 100, 5))
ETA_FINE = tuple(Fraction(x, 1000) for x in range(800, 1000, 7))
W_UNIT = (Fraction(1),)
W_WIDE = tuple(Fraction(x) for x in (1, 2, 3, 5, 8, 13, 21, 34))


@dataclass(frozen=True)
class Family:
    key: str
    label: str
    count: int
    capacity_rule: str  # "prescribed", "independent" or "seasonal"
    kwargs: dict = field(default_factory=dict)
    builder: Callable[..., Benchmark] | None = None


FAMILIES: tuple[Family, ...] = (
    Family("random_caps",
           "Random efficiencies, fixed capacity ratios (7/10, 13/10)", 40,
           "prescribed", dict(
               depth=3, branching=3, periods=3, eta_choices=ETA_FINE,
               weight_choices=W_UNIT, missing_rate=0.0,
               ratio_source=Fraction(7, 10), ratio_edge=Fraction(13, 10),
               tie_margin=None)),
    Family("source_bind", "Source-binding configuration", 25, "prescribed", dict(
        depth=3, branching=3, periods=3, eta_choices=ETA_COARSE,
        weight_choices=W_UNIT, missing_rate=0.0,
        ratio_source=Fraction(1, 2), ratio_edge=Fraction(3), tie_margin=None)),
    Family("edge_bind", "Edge-binding configuration (all loaded reaches tied)", 25,
           "prescribed", dict(
               depth=3, branching=3, periods=3, eta_choices=ETA_COARSE,
               weight_choices=W_UNIT, missing_rate=0.0,
               ratio_source=Fraction(3), ratio_edge=Fraction(1, 2),
               tie_margin=None)),
    Family("missing", "Missing-demand periods (35% inactive)", 30, "prescribed", dict(
        depth=3, branching=3, periods=4, eta_choices=ETA_COARSE,
        weight_choices=W_UNIT, missing_rate=0.35,
        ratio_source=Fraction(4, 5), ratio_edge=Fraction(3, 2), tie_margin=None)),
    Family("deep", "Deeper trees (depth 5)", 20, "prescribed", dict(
        depth=5, branching=2, periods=3, eta_choices=ETA_COARSE,
        weight_choices=W_UNIT, missing_rate=0.1,
        ratio_source=Fraction(4, 5), ratio_edge=Fraction(3, 2), tie_margin=None)),
    Family("weights", "Heterogeneous service weights", 30, "prescribed", dict(
        depth=3, branching=3, periods=3, eta_choices=ETA_COARSE,
        weight_choices=W_WIDE, missing_rate=0.1,
        ratio_source=Fraction(4, 5), ratio_edge=Fraction(3, 2), tie_margin=None)),
    Family("degenerate", "Near-degenerate bottleneck ties (1e-12)", 30,
           "prescribed", dict(
               depth=3, branching=3, periods=3, eta_choices=ETA_COARSE,
               weight_choices=W_UNIT, missing_rate=0.0,
               ratio_source=Fraction(4, 5), ratio_edge=Fraction(3, 2),
               tie_margin=Fraction(1, 10**12))),
    # Canal-like data: efficiencies from a few lining classes, uniform weights
    # (the neutral default rule (i) of Section 2.6).
    Family("independent", "Independent capacities, lining classes, uniform weights",
           80, "independent",
           dict(eta_choices=ETA_COARSE, weight_choices=W_UNIT),
           builder=independent_instance),
    Family("seasonal_supply", "Constant seasonal supply, varying demand", 60,
           "seasonal",
           dict(eta_choices=ETA_COARSE, weight_choices=W_UNIT),
           builder=seasonal_supply_instance),
    # Generic data: fine efficiency grid and heterogeneous weights, so that ties
    # between users are unlikely and the Stage-2 optimum is usually a vertex.
    Family("independent_generic",
           "Independent capacities, generic efficiencies and weights", 60,
           "independent",
           dict(eta_choices=ETA_FINE, weight_choices=W_WIDE),
           builder=independent_instance),
)


def generate_instances(families: tuple[Family, ...] = FAMILIES):
    """Yield ``(family, model)`` pairs in a fixed, seed-determined order."""
    rng_prescribed = random.Random(SEED_PRESCRIBED)
    rng_independent = random.Random(SEED_INDEPENDENT)
    for fam in families:
        for i in range(fam.count):
            name = f"{fam.key}_{i}"
            if fam.builder is None:
                yield fam, prescribed_instance(rng_prescribed, name=name, **fam.kwargs)
            else:
                yield fam, fam.builder(rng_independent, name=name, **fam.kwargs)


# --------------------------------------------------------------------------- #
#  checks
# --------------------------------------------------------------------------- #
def _loads(model: Benchmark, ratios, a_coeff, b_coeff):
    """Gross source and edge loads (float) of an allocation, keyed by label."""
    loads: dict[str, float] = {}
    for k in model.periods:
        loads[f"source:{k}"] = sum(
            float(b_coeff[(k, u)] * model.demand[k][u]) * ratios.get((k, u), 0.0)
            for u in model.user_ids
        )
        for e in model.edge_ids:
            loads[f"edge:{k}:{e}"] = sum(
                float(a_coeff[(k, e, u)] * model.demand[k][u]) * ratios.get((k, u), 0.0)
                for u in model.user_ids
            )
    return loads


def _capacity(model: Benchmark, label: str) -> float:
    parts = label.split(":")
    if parts[0] == "source":
        return float(model.source_capacity[parts[1]])
    return float(model.edge_capacity[parts[1]][parts[2]])


def _relative_physical_violation(model, ratios, a_coeff, b_coeff) -> float:
    worst = 0.0
    for label, load in _loads(model, ratios, a_coeff, b_coeff).items():
        cap = _capacity(model, label)
        if cap > 0:
            worst = max(worst, (load - cap) / cap)
    return max(0.0, worst)


def _max_relative_slack(model, labels, ratios, a_coeff, b_coeff) -> float:
    if not labels:
        return 0.0
    loads = _loads(model, ratios, a_coeff, b_coeff)
    return max(
        abs(_capacity(model, lab) - loads[lab]) / _capacity(model, lab)
        for lab in labels
    )


def _resource_ratios(model: Benchmark, closed) -> dict[str, Fraction]:
    """Capacity-to-full-load ratio of every positive-load resource."""
    ratios: dict[str, Fraction] = {}
    for k, load in closed.source_loads.items():
        if load > 0:
            ratios[f"source:{k}"] = model.source_capacity[k] / load
    for (k, e), load in closed.edge_loads.items():
        if load > 0:
            ratios[f"edge:{k}:{e}"] = model.edge_capacity[k][e] / load
    return ratios


def _scaled(model: Benchmark, factor_by_label: dict[str, Fraction]) -> Benchmark:
    source_capacity = {
        k: model.source_capacity[k] * factor_by_label.get(f"source:{k}", Fraction(1))
        for k in model.periods
    }
    edge_capacity = {
        k: {
            e: model.edge_capacity[k][e] * factor_by_label.get(f"edge:{k}:{e}", Fraction(1))
            for e in model.edge_ids
        }
        for k in model.periods
    }
    return _with_capacities(model, source_capacity, edge_capacity)


def lp_bottleneck_test(
    model: Benchmark, closed, lp_lambda_star: float | None = None,
) -> tuple[bool, bool, float, float]:
    """Identify the bottleneck with the Stage-1 LP alone.

    The near-minimizer set N collects the resources whose ratio lies within
    NEAR_MINIMIZER_MARGIN of a reference guarantee. That reference is the
    Stage-1 LP value whenever one is supplied, so the closed form contributes
    the prediction under test and never the value it is compared with. Two LP
    solves then test the set:

    * sufficiency -- relaxing every resource outside N tenfold leaves the LP
      guarantee unchanged, so N alone limits the guarantee;
    * necessity -- relaxing the resources of N by 0.1% raises the LP guarantee,
      so N does limit it.

    Returns (sufficient, necessary, lp_after_relaxing_others,
    lp_after_relaxing_named). For lambda* = 1 no resource binds and both tests
    are reported as passed.
    """
    reference = float(closed.lambda_star if lp_lambda_star is None else lp_lambda_star)
    if reference >= 1 - 1e-9:
        return True, True, 1.0, 1.0
    ratios = _resource_ratios(model, closed)
    margin = reference * (1 + float(NEAR_MINIMIZER_MARGIN))
    near = {lab for lab, xi in ratios.items() if float(xi) <= margin}
    others = {lab: RELAX_OTHERS for lab in ratios if lab not in near}
    lp_others = solve_stage1_lp(_scaled(model, others)).lambda_star
    lp_named = solve_stage1_lp(_scaled(model, {lab: RELAX_NAMED for lab in near})).lambda_star
    sufficient = abs(lp_others - reference) <= 1e-9
    necessary = lp_named - reference > 1e-9
    return sufficient, necessary, lp_others, lp_named


def stage2_face_width(model: Benchmark, lambda_star: float, stage2_ratios) -> float:
    """Spread of a random linear functional over the Stage-2 optimal face.

    Zero (to solver precision) means the Stage-2 optimum is a single point, in
    which case Stage 3 has nothing to choose and is redundant by structure.
    """
    records = model.active_records
    physical_a, physical_b, _ = physical_matrices(model)
    weighted = weighted_coefficients(model, records)
    w_star = float(weighted @ np.array([stage2_ratios[r] for r in records]))
    rng = np.random.default_rng(zlib.crc32(model.name.encode("utf-8")))
    direction = rng.uniform(-1.0, 1.0, size=len(records))
    values = []
    for sign in (1.0, -1.0):
        result = linprog(
            sign * direction,
            A_ub=physical_a, b_ub=physical_b,
            A_eq=weighted.reshape(1, -1), b_eq=np.array([w_star]),
            bounds=[(lambda_star, 1.0)] * len(records),
            method="highs",
            options={"primal_feasibility_tolerance": 1e-9,
                     "dual_feasibility_tolerance": 1e-9},
        )
        if not result.success:
            raise RuntimeError(f"Stage-2 face probe failed: {result.message}")
        values.append(float(direction @ result.x))
    return max(0.0, values[1] - values[0])


def check(model: Benchmark) -> dict[str, object]:
    """Every acceptance gate plus bottleneck and Stage-3 diagnostics."""
    closed = solve_stage1_closed_form(model)
    lp = solve_stage1_lp(model)
    solution = solve_three_stage(model)

    canonical = {rec: closed.lambda_star for rec in model.active_records}
    operator = verify_operator_exact(model, canonical)
    a_coeff, b_coeff = build_operator_exact(model)

    lambda_star = float(closed.lambda_star)
    stage2 = solution.stage2
    stage3 = solution.stage3

    resources = tuple(r for r in closed.active_resources if r != "demand_upper_bound")
    classes = sorted({r.split(":")[0] for r in resources})
    if not resources:
        bottleneck_class = "demand (lambda* = 1)"
    else:
        bottleneck_class = "+".join(classes)
    slack_lp = _max_relative_slack(model, resources, lp.ratios, a_coeff, b_coeff)
    slack_s3 = _max_relative_slack(model, resources, stage3.ratios, a_coeff, b_coeff)

    sufficient, necessary, lp_others, lp_named = lp_bottleneck_test(
        model, closed, lp.lambda_star)
    face_width = stage2_face_width(model, lambda_star, stage2.ratios)
    face_is_point = face_width <= FACE_WIDTH_THRESHOLD

    omega2 = stage2.temporal_variation
    omega3 = stage3.temporal_variation
    stage3_active = omega2 - omega3 > STAGE3_ACTIVITY_THRESHOLD
    if stage3_active:
        stage3_outcome = "active"
    elif face_is_point:
        stage3_outcome = "redundant: Stage-2 optimum unique"
    else:
        stage3_outcome = "inactive: Stage-2 vertex already smoothest"
    moved = sum(
        1 for rec in model.active_records
        if abs(stage3.ratios[rec] - stage2.ratios[rec]) > RATIO_MOVE_THRESHOLD
    )
    return {
        # acceptance gates, in the numbering of Section 2.9
        "G1_closed_vs_lp": abs(lp.lambda_star - lambda_star),
        "G3_operator_balance": float(operator.maximum_absolute_difference),
        "G4_node_residual": float(operator.maximum_node_residual),
        "G5_physical_abs": maximum_physical_violation(
            model, stage3.ratios, a_coeff, b_coeff),
        "G5_physical_rel": _relative_physical_violation(
            model, stage3.ratios, a_coeff, b_coeff),
        "G6_floor": max(0.0, lambda_star - stage3.minimum_ratio),
        "G7_satisfaction": abs(
            stage3.weighted_satisfaction - stage2.weighted_satisfaction),
        "G8_variation_excess": max(0.0, omega3 - omega2),
        # bottleneck diagnostics
        "lambda_star": lambda_star,
        "bottleneck_class": bottleneck_class,
        "bottleneck_count": len(resources),
        "bottleneck_slack_lp": slack_lp,
        "bottleneck_slack_stage3": slack_s3,
        "bottleneck_tight": bool(max(slack_lp, slack_s3) <= TIGHTNESS_TOLERANCE),
        "lp_relax_others": lp_others,
        "lp_relax_named": lp_named,
        "bottleneck_sufficient": sufficient,
        "bottleneck_necessary": necessary,
        "bottleneck_identified": bool(
            max(slack_lp, slack_s3) <= TIGHTNESS_TOLERANCE and sufficient and necessary),
        # Stage-3 diagnostics
        "omega_stage2": omega2,
        "omega_stage3": omega3,
        "stage2_face_width": face_width,
        "stage2_optimum_unique": bool(face_is_point),
        "stage3_active": bool(stage3_active),
        "stage3_outcome": stage3_outcome,
        "stage3_relative_reduction": (omega2 - omega3) / omega2 if omega2 > 0 else 0.0,
        "ratios_moved_by_stage3": moved,
        # size
        "users": len(model.users),
        "edges": len(model.edges),
        "periods": len(model.periods),
        "active_records": len(model.active_records),
    }


GATES = ("G1_closed_vs_lp", "G3_operator_balance", "G4_node_residual",
         "G5_physical_abs", "G5_physical_rel", "G6_floor", "G7_satisfaction",
         "G8_variation_excess")
#: The thresholds of Section 2.9, applied unchanged to every randomized
#: instance, plus the relative physical residual G5r (violation divided by the
#: capacity of the same resource), which is scale free.
TOLERANCE = {
    "G1_closed_vs_lp": 5e-7, "G3_operator_balance": 0.0, "G4_node_residual": 0.0,
    "G5_physical_abs": 5e-7, "G5_physical_rel": 1e-9, "G6_floor": 5e-7,
    "G7_satisfaction": 1e-8, "G8_variation_excess": 5e-7,
}


def run_suite(families: tuple[Family, ...] = FAMILIES) -> list[dict[str, object]]:
    """One row per instance: family, capacity rule, gates and diagnostics."""
    rows = []
    for fam, model in generate_instances(families):
        row: dict[str, object] = {
            "family": fam.key,
            "family_label": fam.label,
            "capacity_rule": fam.capacity_rule,
            "instance": model.name,
        }
        row.update(check(model))
        row["gate_violations"] = sum(
            1 for g in GATES if float(row[g]) > TOLERANCE[g])
        rows.append(row)
    return rows


def summarize(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    """Per-family maxima of the gates and counts of the diagnostics."""
    order: list[str] = []
    for r in rows:
        if r["family"] not in order:
            order.append(r["family"])
    groups = [(key, [r for r in rows if r["family"] == key]) for key in order]
    groups.append(("all", rows))

    out = []
    for key, grp in groups:
        active = [r for r in grp if r["stage3_active"]]
        with_bottleneck = [r for r in grp if r["bottleneck_count"] > 0]
        label = "All families" if key == "all" else grp[0]["family_label"]
        rule = (
            "mixed" if key == "all" else grp[0]["capacity_rule"]
        )
        summary: dict[str, object] = {
            "family": key, "family_label": label, "capacity_rule": rule,
            "instances": len(grp),
        }
        for g in GATES:
            summary[f"max_{g}"] = max(float(r[g]) for r in grp)
        summary.update({
            "gate_violations": sum(int(r["gate_violations"]) for r in grp),
            "source_bound": sum(1 for r in grp if r["bottleneck_class"] == "source"),
            "edge_bound": sum(1 for r in grp if r["bottleneck_class"] == "edge"),
            "source_and_edge_tied": sum(
                1 for r in grp if r["bottleneck_class"] == "edge+source"),
            "unconstrained": sum(1 for r in grp if r["bottleneck_count"] == 0),
            "multiple_minimizers": sum(1 for r in grp if r["bottleneck_count"] > 1),
            "bottleneck_tight": sum(1 for r in with_bottleneck if r["bottleneck_tight"]),
            "bottleneck_sufficient": sum(
                1 for r in with_bottleneck if r["bottleneck_sufficient"]),
            "bottleneck_necessary": sum(
                1 for r in with_bottleneck if r["bottleneck_necessary"]),
            "bottleneck_identified": sum(
                1 for r in with_bottleneck if r["bottleneck_identified"]),
            "with_bottleneck": len(with_bottleneck),
            "stage2_optimum_unique": sum(1 for r in grp if r["stage2_optimum_unique"]),
            "stage3_active": len(active),
            "stage3_inactive_face_not_point": sum(
                1 for r in grp
                if not r["stage3_active"] and not r["stage2_optimum_unique"]),
            "stage3_active_share": len(active) / len(grp),
            "median_relative_reduction_when_active": (
                statistics.median(float(r["stage3_relative_reduction"]) for r in active)
                if active else 0.0
            ),
            "median_ratios_moved_when_active": (
                statistics.median(int(r["ratios_moved_by_stage3"]) for r in active)
                if active else 0
            ),
        })
        out.append(summary)
    return out
