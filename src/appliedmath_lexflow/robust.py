"""Solver-independent (invariant) diagnostics for the lexicographic model.

The single-vertex Stage-2 temporal variation reported by :mod:`lexicographic`
is *not* an invariant of the problem: Stage 2 is degenerate, so its optimal
face contains many extreme points and different LP solvers (or the same solver
after a version bump) return different ones with different temporal variation
Omega. Reporting one such value -- and a "reduction" computed from it -- is not
reproducible.

This module computes quantities that depend only on the model, not on solver
pivoting:

* ``stage2_variation_bounds`` -- the range ``[Omega_min, Omega_max]`` of the
  temporal variation over the *entire* Stage-2 optimal face. ``Omega_min`` is
  the value Stage 3 attains; ``Omega_max`` is the worst any solver could report.
  The guaranteed Stage-3 improvement is ``(Omega_max - Omega_min) / Omega_max``.
* ``price_of_fairness`` -- how much total net delivery the Stage-1 max-min
  guarantee costs relative to the pure-efficiency optimum.
* ``solve_leximin`` -- the full lexicographic max-min (leximin) allocation by
  progressive filling; unlike Stage 1 it is a single, solver-independent vector.

Every routine here uses only physical capacities, demands, efficiencies and the
exact Stage-1 floor, so its output is reproducible across solvers.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass
from fractions import Fraction

import numpy as np
from scipy.optimize import linprog

from .domain import Benchmark
from .lexicographic import temporal_pairs, weighted_coefficients
from .stage1 import physical_matrices, solve_stage1_closed_form

_HIGHS = {"primal_feasibility_tolerance": 1e-9, "dual_feasibility_tolerance": 1e-9}


def _rationalize(value: float, max_den: int = 10**6, tol: float = 1e-7) -> Fraction | None:
    """Return the simplest rational within ``tol`` of ``value`` (or ``None``)."""
    candidate = Fraction(value).limit_denominator(max_den)
    return candidate if abs(float(candidate) - value) <= tol else None


@dataclass(frozen=True, slots=True)
class VariationBounds:
    omega_min: float
    omega_max: float
    reduction_fraction: float          # (omega_max - omega_min) / omega_max
    omega_min_exact: Fraction | None
    omega_max_exact: Fraction | None
    enumerated_pairs: int


def stage2_optimum(model: Benchmark) -> tuple[float, np.ndarray, np.ndarray, tuple]:
    """Return the Stage-2 optimal weighted-delivery value W* and matrices."""
    physical_a, physical_b, records = physical_matrices(model)
    weighted = weighted_coefficients(model, records)
    lam = float(solve_stage1_closed_form(model).lambda_star)
    res = linprog(
        -weighted, A_ub=physical_a, b_ub=physical_b,
        bounds=[(lam, 1.0)] * len(records), method="highs", options=_HIGHS,
    )
    if not res.success:
        raise RuntimeError(f"Stage-2 optimum failed: {res.message}")
    return float(weighted @ res.x), physical_a, physical_b, records


def stage2_variation_bounds(
    model: Benchmark, max_pairs: int = 14
) -> VariationBounds | None:
    """Extremes of temporal variation over the exact Stage-2 optimal face.

    ``Omega = sum |r_right - r_left|`` is convex, so both its minimum and maximum
    over the polytope ``{physical caps, weighted @ r == W*, r in [lambda*, 1]}``
    are attained at vertices. We obtain ``Omega_max`` by maximising every signed
    linearisation ``sum s_i (r_right - r_left)`` (``s in {+1,-1}^p``) and taking
    the best; ``Omega_min`` by the standard z-linearisation. Returns ``None``
    (with no silent guess) when the number of consecutive-active pairs ``p``
    exceeds ``max_pairs`` and the 2**p enumeration would be too large.
    """
    pairs = temporal_pairs(model)
    p = len(pairs)
    if p == 0:
        return VariationBounds(0.0, 0.0, 0.0, Fraction(0), Fraction(0), 0)
    if p > max_pairs:
        return None

    wstar, physical_a, physical_b, records = stage2_optimum(model)
    n = len(records)
    lam = float(solve_stage1_closed_form(model).lambda_star)
    index = {rec: i for i, rec in enumerate(records)}
    weighted = weighted_coefficients(model, records)
    bounds = [(lam, 1.0)] * n

    def omega(x: np.ndarray) -> float:
        return float(sum(abs(x[index[r]] - x[index[l]]) for l, r in pairs))

    # Omega_min: minimise sum z, z >= |r_r - r_l|, on the exact face.
    obj = np.concatenate([np.zeros(n), np.ones(p)])
    rows, rhs = [], []
    for row, bound in zip(physical_a, physical_b):
        rows.append(np.concatenate([row, np.zeros(p)]))
        rhs.append(float(bound))
    for i, (left, right) in enumerate(pairs):
        z = np.zeros(n + p); z[index[right]] = 1.0; z[index[left]] = -1.0; z[n + i] = -1.0
        rows.append(z); rhs.append(0.0)
        z = np.zeros(n + p); z[index[left]] = 1.0; z[index[right]] = -1.0; z[n + i] = -1.0
        rows.append(z); rhs.append(0.0)
    eq = np.concatenate([weighted, np.zeros(p)])
    res_min = linprog(
        obj, A_ub=np.vstack(rows), b_ub=np.asarray(rhs, float),
        A_eq=[eq], b_eq=[wstar], bounds=bounds + [(0.0, None)] * p,
        method="highs", options=_HIGHS,
    )
    if not res_min.success:
        raise RuntimeError(f"Omega_min failed: {res_min.message}")
    omega_min = float(res_min.fun)

    # Omega_max: best signed linearisation over the same face.
    omega_max = 0.0
    for signs in itertools.product((1.0, -1.0), repeat=p):
        c = np.zeros(n)
        for (left, right), s in zip(pairs, signs):
            c[index[right]] -= s
            c[index[left]] += s
        res = linprog(
            c, A_ub=physical_a, b_ub=physical_b, A_eq=[weighted], b_eq=[wstar],
            bounds=bounds, method="highs", options=_HIGHS,
        )
        if res.success:
            omega_max = max(omega_max, omega(res.x))

    reduction = (omega_max - omega_min) / omega_max if omega_max > 0 else 0.0
    return VariationBounds(
        omega_min, omega_max, reduction,
        _rationalize(omega_min), _rationalize(omega_max), p,
    )


@dataclass(frozen=True, slots=True)
class PriceOfFairness:
    efficiency_optimum: float          # Z_eff: max total net delivery, no floor
    fair_delivery: float               # Z_fair: total net delivery under the floor
    price_of_fairness: float           # 1 - Z_fair / Z_eff


def price_of_fairness(model: Benchmark) -> PriceOfFairness:
    """Total-delivery cost of the Stage-1 max-min guarantee.

    ``Z_eff`` maximises unweighted net delivery ``sum d_kf r_kf`` with the
    physical capacities but *no* fairness floor (``r in [0, 1]``); ``Z_fair`` is
    the same total under the Stage-1 floor and Stage-2 weighting. The price of
    fairness ``1 - Z_fair/Z_eff`` is what equity costs in throughput.
    """
    physical_a, physical_b, records = physical_matrices(model)
    demand = np.asarray(
        [float(model.demand[k][f]) for (k, f) in records], dtype=float
    )
    lam = float(solve_stage1_closed_form(model).lambda_star)

    res_eff = linprog(
        -demand, A_ub=physical_a, b_ub=physical_b,
        bounds=[(0.0, 1.0)] * len(records), method="highs", options=_HIGHS,
    )
    res_fair = linprog(
        -demand, A_ub=physical_a, b_ub=physical_b,
        bounds=[(lam, 1.0)] * len(records), method="highs", options=_HIGHS,
    )
    if not (res_eff.success and res_fair.success):
        raise RuntimeError("Price-of-fairness LP failed.")
    z_eff = float(demand @ res_eff.x)
    z_fair = float(demand @ res_fair.x)
    pof = 1.0 - z_fair / z_eff if z_eff > 0 else 0.0
    return PriceOfFairness(z_eff, z_fair, pof)


@dataclass(frozen=True, slots=True)
class LeximinSolution:
    ratios: dict[tuple[str, str], float]
    levels: tuple[float, ...]              # distinct max-min levels, in freeze order
    minimum_ratio: float
    weighted_satisfaction: float
    temporal_variation: float


def solve_leximin(
    model: Benchmark,
    feasibility_tolerance: float = 1e-7,
    slack: float = 1e-7,
    max_records: int | None = 64,
) -> LeximinSolution:
    """Full lexicographic max-min (leximin) allocation by progressive filling.

    Stage 1 only maximises the *single* smallest service ratio, so its optimal
    r-vector is non-unique. Leximin instead maximises the smallest ratio, then
    the second smallest, and so on: it repeatedly applies the Stage-1 max-min LP
    to the residual system, freezing at each round the records that cannot be
    raised further. The result is a UNIQUE vector -- removing the degeneracy that
    makes Stage 2/3 solver-dependent -- and needs no subjective weights ``w_f``.

    Numerical robustness: when a capacity is exactly binding the max-min ``level``
    returned by the solver can sit an ``ulp`` above the true value; requiring the
    remaining free records to reach *exactly* that level against a saturated
    capacity is then reported as infeasible. Both the freeze test and the freeze
    threshold therefore use a small ``slack`` (and HiGHS' default feasibility
    tolerance rather than an over-tight one). ``max_records`` guards the cost:
    progressive filling runs O(records) LPs per round, so it is refused (with a
    clear error) on benchmarks far larger than the exact article examples; the
    caller decides what to report for those.
    """
    physical_a, physical_b, records = physical_matrices(model)
    n = len(records)
    if max_records is not None and n > max_records:
        raise ValueError(
            f"Leximin refused: {n} active records exceeds max_records={max_records}. "
            "Progressive filling is intended for the small exact benchmarks; "
            "raise max_records explicitly to force it."
        )
    index = {rec: i for i, rec in enumerate(records)}
    fixed: dict[int, float] = {}
    levels: list[float] = []

    def solve_maxmin(free: list[int]) -> float:
        # maximise lambda s.t. caps, r_free >= lambda, fixed columns substituted.
        cols = n + 1  # r variables + lambda
        a_ub = np.zeros((physical_a.shape[0] + len(free), cols))
        b_ub = np.zeros(physical_a.shape[0] + len(free))
        a_ub[: physical_a.shape[0], :n] = physical_a
        b_ub[: physical_a.shape[0]] = physical_b
        for r, j in enumerate(free):
            a_ub[physical_a.shape[0] + r, j] = -1.0
            a_ub[physical_a.shape[0] + r, n] = 1.0
        bounds = []
        for j in range(n):
            bounds.append((fixed[j], fixed[j]) if j in fixed else (0.0, 1.0))
        bounds.append((0.0, 1.0))
        obj = np.zeros(cols); obj[n] = -1.0
        res = linprog(
            obj, A_ub=a_ub, b_ub=b_ub, bounds=bounds, method="highs",
            options={"primal_feasibility_tolerance": feasibility_tolerance,
                     "dual_feasibility_tolerance": feasibility_tolerance},
        )
        if not res.success:
            raise RuntimeError(f"Leximin max-min round failed: {res.message}")
        return float(res.x[n])

    def max_single(target: int, free: list[int], level: float) -> float:
        # maximise r_target s.t. caps, all free >= level, fixed substituted.
        a_ub = np.zeros((physical_a.shape[0] + len(free), n))
        b_ub = np.zeros(physical_a.shape[0] + len(free))
        a_ub[: physical_a.shape[0], :] = physical_a
        b_ub[: physical_a.shape[0]] = physical_b
        for r, j in enumerate(free):
            a_ub[physical_a.shape[0] + r, j] = -1.0
            # r_j >= level - slack: a hair of slack so a level that saturates a
            # capacity (returned an ulp high) does not make the LP infeasible.
            b_ub[physical_a.shape[0] + r] = -(level - slack)
        bounds = [(fixed[j], fixed[j]) if j in fixed else (0.0, 1.0) for j in range(n)]
        obj = np.zeros(n); obj[target] = -1.0
        res = linprog(obj, A_ub=a_ub, b_ub=b_ub, bounds=bounds, method="highs",
                      options={"primal_feasibility_tolerance": feasibility_tolerance,
                               "dual_feasibility_tolerance": feasibility_tolerance})
        if not res.success:
            raise RuntimeError(f"Leximin freeze test failed: {res.message}")
        return float(res.x[target])

    free = list(range(n))
    guard = 0
    while free:
        guard += 1
        if guard > n + 2:
            raise RuntimeError("Leximin did not converge; check the model.")
        level = solve_maxmin(free)
        levels.append(level)
        # A record is blocked at this level when it cannot be raised beyond it
        # (within slack) without violating a capacity or lowering another free
        # record below the level.
        newly_frozen = [j for j in free if max_single(j, free, level) <= level + 2 * slack]
        if not newly_frozen:  # numerical safety: freeze the tightest record
            newly_frozen = [min(free, key=lambda j: max_single(j, free, level))]
        for j in newly_frozen:
            fixed[j] = level
        free = [j for j in free if j not in fixed]

    ratios = {rec: fixed[index[rec]] for rec in records}

    # Collapse consecutive near-equal freeze levels into the distinct leximin
    # levels (a saturated level can take a couple of rounds to drain under the
    # numerical slack, producing e.g. [0.6, 0.6, 0.8, 0.8]).
    distinct_levels: list[float] = []
    for value in levels:
        if not distinct_levels or abs(value - distinct_levels[-1]) > 1e-6:
            distinct_levels.append(value)
    levels = distinct_levels

    weights = model.weight_by_user
    num = den = 0.0
    for (k, f) in records:
        c = float(weights[f] * model.demand[k][f])
        num += c * ratios[(k, f)]; den += c
    weighted_sat = num / den if den > 0 else 1.0
    variation = float(
        sum(abs(ratios[r] - ratios[l]) for l, r in temporal_pairs(model))
    )
    return LeximinSolution(
        ratios=ratios,
        levels=tuple(levels),
        minimum_ratio=min(ratios.values()) if ratios else 1.0,
        weighted_satisfaction=weighted_sat,
        temporal_variation=variation,
    )
