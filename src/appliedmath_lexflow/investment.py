"""Inverse design problem: minimum-cost rehabilitation of a lossy canal tree.

The allocation modules solve the *forward* problem -- given capacities,
efficiencies and demands, find a fair allocation.  This module solves the
*inverse* problem: given a target service guarantee ``tau``, find the
cheapest set of capacity or lining upgrades that attains it.

Every resource ``j`` (one per period-source pair and per period-edge pair)
carries a capacity ``c_j`` and a full-demand load ``L_j``; its headroom
ratio is ``xi_j = c_j / L_j`` and the Stage-1 guarantee is
``lambda* = min(1, min_j xi_j)``.

Results implemented here
------------------------

* :func:`expansion_plan` -- Theorem 1': the unique optimal widening plan is
  ``Delta_j = max(0, tau*L_j - c_j)``, because the constraints decouple
  coordinatewise.
* :func:`budget_function` -- Algorithm 1 / Theorem 2': the complete
  piecewise-linear description of ``B(tau)``, obtained by one sort in
  ``O(m log m)``.  ``B`` is convex, nondecreasing, and its slope
  ``sum_{j in S(tau)} p_j L_j`` is nondecreasing (diminishing returns).
* :func:`guarantee_for_budget` -- Corollary 2': the concave inverse
  ``lambda^(B)``.
* :func:`critical_resources` -- the only resources that can ever bind.
* :func:`relief_edges` -- Lemma 3': lining edge ``e`` reduces the load of a
  resource ``j`` exactly when ``e`` lies at or below ``j`` on an active
  route.
* :func:`epsilon_bottleneck_set` and :func:`lining_plan` -- Theorem 4' and
  Algorithm 2: any upgrade that leaves one member of the epsilon-bottleneck
  set unrelieved gains at most ``epsilon``, so single-edge ascent stalls on
  a plateau and the tied set must be relieved jointly.

All arithmetic is exact :class:`~fractions.Fraction`; no LP is solved.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, replace
from fractions import Fraction

from .domain import Benchmark
from .operators import user_paths
from .stage1 import full_demand_loads

__all__ = [
    "Resource",
    "ExpansionPlan",
    "BudgetSegment",
    "BudgetFunction",
    "Transversal",
    "LiningPlan",
    "MixedPlan",
    "resource_table",
    "lambda_star",
    "expansion_plan",
    "budget_function",
    "guarantee_for_budget",
    "critical_resources",
    "epsilon_bottleneck_set",
    "relief_edges",
    "minimum_cost_transversal",
    "apply_lining",
    "lining_plan",
    "mixed_plan",
]


# --------------------------------------------------------------------------
# Resources
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Resource:
    """One capacity constraint of the Stage-1 packing model."""

    label: str
    kind: str  # "source" | "edge"
    period: str
    edge_id: str | None
    capacity: Fraction  # c_j
    load: Fraction  # L_j > 0

    @property
    def headroom(self) -> Fraction:
        """``xi_j = c_j / L_j``."""
        return self.capacity / self.load


def resource_table(model: Benchmark) -> tuple[Resource, ...]:
    """Return every positive-load resource of ``model``, exactly.

    Zero-load resources are omitted: they impose no bound on the Stage-1
    guarantee and can never be a bottleneck, so no rehabilitation decision
    can concern them.
    """
    source_loads, edge_loads = full_demand_loads(model)
    rows: list[Resource] = []
    for period in model.periods:
        load = source_loads[period]
        if load > 0:
            rows.append(
                Resource(
                    label=f"source:{period}",
                    kind="source",
                    period=period,
                    edge_id=None,
                    capacity=model.source_capacity[period],
                    load=load,
                )
            )
    for period in model.periods:
        for edge_id in model.edge_ids:
            load = edge_loads[(period, edge_id)]
            if load > 0:
                rows.append(
                    Resource(
                        label=f"edge:{period}:{edge_id}",
                        kind="edge",
                        period=period,
                        edge_id=edge_id,
                        capacity=model.edge_capacity[period][edge_id],
                        load=load,
                    )
                )
    return tuple(rows)


def lambda_star(resources: Sequence[Resource]) -> Fraction:
    """Stage-1 guarantee ``min(1, min_j xi_j)`` from a resource table."""
    return min([Fraction(1)] + [item.headroom for item in resources])


def _prices(
    resources: Sequence[Resource], prices: Mapping[str, Fraction] | None
) -> dict[str, Fraction]:
    if prices is None:
        return {item.label: Fraction(1) for item in resources}
    resolved: dict[str, Fraction] = {}
    for item in resources:
        value = Fraction(prices.get(item.label, 1))
        if value <= 0:
            raise ValueError(f"Unit price for {item.label!r} must be positive.")
        resolved[item.label] = value
    return resolved


def _check_target(target: Fraction) -> Fraction:
    target = Fraction(target)
    if not (Fraction(0) < target <= Fraction(1)):
        raise ValueError("The target guarantee must satisfy 0 < tau <= 1.")
    return target


# --------------------------------------------------------------------------
# Theorem 1': the exact minimum-cost widening plan
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ExpansionPlan:
    """Minimum-cost capacity widening reaching a target guarantee."""

    target: Fraction
    lambda_before: Fraction
    increments: tuple[tuple[str, Fraction], ...]  # only the funded resources
    cost: Fraction

    @property
    def funded(self) -> tuple[str, ...]:
        """``S(tau)``: the resources that must be upgraded."""
        return tuple(label for label, _ in self.increments)

    def increment_map(self) -> dict[str, Fraction]:
        return dict(self.increments)


def expansion_plan(
    model: Benchmark,
    target: Fraction,
    prices: Mapping[str, Fraction] | None = None,
    resources: Sequence[Resource] | None = None,
) -> ExpansionPlan:
    """Theorem 1': the unique minimum-cost widening plan for ``target``.

    ``lambda*(c + Delta) >= tau`` decouples into the independent bounds
    ``Delta_j >= max(0, tau*L_j - c_j)``, and the objective is strictly
    increasing in every coordinate, so meeting each bound with equality is
    optimal and unique.
    """
    target = _check_target(target)
    rows = resource_table(model) if resources is None else tuple(resources)
    unit = _prices(rows, prices)
    increments: list[tuple[str, Fraction]] = []
    cost = Fraction(0)
    for item in rows:
        needed = target * item.load - item.capacity
        if needed > 0:
            increments.append((item.label, needed))
            cost += unit[item.label] * needed
    return ExpansionPlan(
        target=target,
        lambda_before=lambda_star(rows),
        increments=tuple(increments),
        cost=cost,
    )


def widened(model: Benchmark, plan: ExpansionPlan) -> Benchmark:
    """Return ``model`` with the plan's capacity increments applied."""
    delta = plan.increment_map()
    source_capacity = {
        period: model.source_capacity[period] + delta.get(f"source:{period}", Fraction(0))
        for period in model.periods
    }
    edge_capacity = {
        period: {
            edge_id: model.edge_capacity[period][edge_id]
            + delta.get(f"edge:{period}:{edge_id}", Fraction(0))
            for edge_id in model.edge_ids
        }
        for period in model.periods
    }
    return replace(model, source_capacity=source_capacity, edge_capacity=edge_capacity)


# --------------------------------------------------------------------------
# Theorem 2' / Algorithm 1: the budget function
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class BudgetSegment:
    """One linear piece ``B(tau) = slope*tau - intercept`` of the curve."""

    tau_low: Fraction
    tau_high: Fraction
    slope: Fraction  # sum_{j in S} p_j L_j
    intercept: Fraction  # sum_{j in S} p_j c_j
    funded_count: int

    def value(self, tau: Fraction) -> Fraction:
        return self.slope * tau - self.intercept


@dataclass(frozen=True, slots=True)
class BudgetFunction:
    """Complete piecewise-linear description of ``B(tau)`` on ``[lambda*, 1]``."""

    lambda_star: Fraction
    breakpoints: tuple[tuple[Fraction, Fraction], ...]  # (tau, B(tau)), tau ascending
    segments: tuple[BudgetSegment, ...]

    def cost(self, tau: Fraction) -> Fraction:
        """Budget needed for guarantee ``tau`` (0 below the current guarantee)."""
        tau = _check_target(tau)
        if tau <= self.lambda_star:
            return Fraction(0)
        for segment in self.segments:
            if tau <= segment.tau_high:
                return segment.value(tau)
        return self.segments[-1].value(tau)

    def guarantee(self, budget: Fraction) -> Fraction:
        """Corollary 2': the largest guarantee affordable with ``budget``."""
        budget = Fraction(budget)
        if budget < 0:
            raise ValueError("Budget must be nonnegative.")
        if not self.segments or budget <= 0:
            return self.lambda_star
        total = self.breakpoints[-1][1]
        if budget >= total:
            return self.breakpoints[-1][0]
        for segment in self.segments:
            if budget <= segment.value(segment.tau_high):
                if segment.slope == 0:
                    return segment.tau_high
                return (budget + segment.intercept) / segment.slope
        return self.breakpoints[-1][0]


def budget_function(
    model: Benchmark,
    prices: Mapping[str, Fraction] | None = None,
    resources: Sequence[Resource] | None = None,
) -> BudgetFunction:
    """Algorithm 1: build ``B(tau)`` with a single ``O(m log m)`` sort.

    The kinks of ``B`` sit exactly at the distinct headroom ratios
    ``xi_j < 1``; between consecutive kinks the funded set ``S(tau)`` is
    constant and ``B`` is affine.  No linear program is solved.
    """
    rows = resource_table(model) if resources is None else tuple(resources)
    unit = _prices(rows, prices)
    base = lambda_star(rows)

    ordered = sorted(rows, key=lambda item: item.headroom)
    knots = sorted({item.headroom for item in ordered if base < item.headroom < 1})
    grid = [base, *knots, Fraction(1)]

    segments: list[BudgetSegment] = []
    breakpoints: list[tuple[Fraction, Fraction]] = [(base, Fraction(0))]
    slope = Fraction(0)
    intercept = Fraction(0)
    cursor = 0
    for index in range(len(grid) - 1):
        low, high = grid[index], grid[index + 1]
        # Every resource whose ratio is <= low is funded on (low, high].
        while cursor < len(ordered) and ordered[cursor].headroom <= low:
            item = ordered[cursor]
            slope += unit[item.label] * item.load
            intercept += unit[item.label] * item.capacity
            cursor += 1
        segments.append(
            BudgetSegment(
                tau_low=low,
                tau_high=high,
                slope=slope,
                intercept=intercept,
                funded_count=cursor,
            )
        )
        breakpoints.append((high, slope * high - intercept))
    return BudgetFunction(
        lambda_star=base,
        breakpoints=tuple(breakpoints),
        segments=tuple(segments),
    )


def guarantee_for_budget(
    model: Benchmark,
    budget: Fraction,
    prices: Mapping[str, Fraction] | None = None,
) -> Fraction:
    """Corollary 2': the guarantee ``lambda^(B)`` affordable with ``budget``."""
    return budget_function(model, prices).guarantee(budget)


def critical_resources(
    model: Benchmark, resources: Sequence[Resource] | None = None
) -> tuple[Resource, ...]:
    """``J_crit = {j : c_j < L_j}`` -- the only resources that can ever bind."""
    rows = resource_table(model) if resources is None else tuple(resources)
    return tuple(item for item in rows if item.capacity < item.load)


def epsilon_bottleneck_set(
    model: Benchmark,
    epsilon: Fraction = Fraction(0),
    resources: Sequence[Resource] | None = None,
) -> tuple[Resource, ...]:
    """``J*_eps = {j : xi_j <= lambda* + eps}`` (Theorem 4')."""
    epsilon = Fraction(epsilon)
    if epsilon < 0:
        raise ValueError("epsilon must be nonnegative.")
    rows = resource_table(model) if resources is None else tuple(resources)
    threshold = lambda_star(rows) + epsilon
    return tuple(item for item in rows if item.headroom <= threshold)


# --------------------------------------------------------------------------
# Lemma 3' and Algorithm 2: lining
# --------------------------------------------------------------------------


def relief_edges(model: Benchmark, resource: Resource) -> frozenset[str]:
    """Lemma 3': the edges whose lining strictly reduces ``resource.load``.

    For a source resource this is every edge on an active route of that
    period.  For an edge resource ``e'`` it is ``e'`` together with the
    edges below it (towards the terminals) on active routes -- lining an
    edge upstream of ``e'`` leaves ``L_{e'}`` unchanged.
    """
    paths = user_paths(model)
    active = [
        user.user_id
        for user in model.users
        if model.demand[resource.period][user.user_id] > 0
    ]
    if resource.kind == "source":
        return frozenset(
            edge_id for user_id in active for edge_id in paths[user_id]
        )
    found: set[str] = set()
    for user_id in active:
        path = paths[user_id]
        if resource.edge_id in path:
            found.update(path[path.index(resource.edge_id) :])
    return frozenset(found)


@dataclass(frozen=True, slots=True)
class Transversal:
    """A set of edges hitting every relief set, with an optimality flag."""

    edges: frozenset[str]
    cost: Fraction
    exact: bool
    minimal_sets: int

    @property
    def certificate(self) -> str:
        return (
            "exact (laminar relief sets: minimal members are pairwise disjoint)"
            if self.exact
            else "greedy (relief sets are not laminar; upper bound only)"
        )


def minimum_cost_transversal(
    families: Iterable[frozenset[str]],
    costs: Mapping[str, Fraction] | None = None,
) -> Transversal:
    """Cheapest edge set meeting every relief set in ``families``.

    Relief sets of a rooted tree are subtrees, so the family is normally
    *laminar*: two of them are either nested or disjoint.  Then the
    inclusion-minimal members are pairwise disjoint, every hitting set must
    spend at least one element on each of them, and taking the cheapest
    element of each attains that lower bound -- an exact optimum.

    When the active-route restriction makes two relief sets overlap without
    nesting (possible when different periods activate different users), the
    laminar argument no longer applies and the routine falls back to the
    standard greedy set cover, reporting ``exact=False``.
    """
    sets = [item for item in families if item]
    if not sets:
        return Transversal(frozenset(), Fraction(0), True, 0)

    price = (
        {}
        if costs is None
        else {key: Fraction(value) for key, value in costs.items()}
    )

    def unit(edge_id: str) -> Fraction:
        value = price.get(edge_id, Fraction(1))
        if value <= 0:
            raise ValueError(f"Lining cost for {edge_id!r} must be positive.")
        return value

    unique = {frozenset(item) for item in sets}
    minimal = [
        item
        for item in unique
        if not any(other < item for other in unique)
    ]
    laminar = all(
        left == right or left.isdisjoint(right) or left < right or right < left
        for left in unique
        for right in unique
    )

    if laminar:
        chosen = {min(item, key=lambda e: (unit(e), e)) for item in minimal}
        return Transversal(
            edges=frozenset(chosen),
            cost=sum((unit(e) for e in chosen), Fraction(0)),
            exact=True,
            minimal_sets=len(minimal),
        )

    uncovered = [set(item) for item in unique]
    chosen: set[str] = set()
    while uncovered:
        candidates = {edge_id for item in uncovered for edge_id in item}
        best = min(
            candidates,
            key=lambda e: (
                unit(e) / max(1, sum(1 for item in uncovered if e in item)),
                e,
            ),
        )
        chosen.add(best)
        uncovered = [item for item in uncovered if best not in item]
    return Transversal(
        edges=frozenset(chosen),
        cost=sum((unit(e) for e in chosen), Fraction(0)),
        exact=False,
        minimal_sets=len(minimal),
    )


def apply_lining(
    model: Benchmark, edges: Iterable[str], target_efficiency: Fraction
) -> Benchmark:
    """Return ``model`` with ``edges`` lined up to ``target_efficiency``."""
    target_efficiency = Fraction(target_efficiency)
    if not (Fraction(0) < target_efficiency <= Fraction(1)):
        raise ValueError("The lining target must satisfy 0 < eta_bar <= 1.")
    selected = frozenset(edges)
    unknown = selected - set(model.edge_ids)
    if unknown:
        raise ValueError(f"Unknown edges: {sorted(unknown)}")
    efficiency = {
        period: {
            edge_id: (
                max(value, target_efficiency) if edge_id in selected else value
            )
            for edge_id, value in row.items()
        }
        for period, row in model.efficiency.items()
    }
    return replace(model, efficiency=efficiency)


@dataclass(frozen=True, slots=True)
class LiningPlan:
    """Result of the epsilon-bottleneck-set ascent (Algorithm 2)."""

    target: Fraction
    target_efficiency: Fraction
    lined: tuple[str, ...]
    cost: Fraction
    lambda_before: Fraction
    lambda_after: Fraction
    reached: bool
    iterations: int
    exact_transversals: bool

    @property
    def stalled(self) -> bool:
        return not self.reached


def lining_plan(
    model: Benchmark,
    target: Fraction,
    target_efficiency: Fraction,
    epsilon: Fraction = Fraction(0),
    costs: Mapping[str, Fraction] | None = None,
) -> LiningPlan:
    """Algorithm 2: raise ``lambda*`` towards ``target`` by lining only.

    Each iteration relieves the whole epsilon-bottleneck set at once.  By
    Theorem 4' a single-edge step gains at most ``epsilon`` whenever two or
    more resources are tied, so the joint step is what makes progress.  If
    the cheap transversal fails to move ``lambda*``, the iteration escalates
    to the union of all relief sets before giving up, and the plan reports
    ``reached=False`` rather than looping.
    """
    target = _check_target(target)
    start = lambda_star(resource_table(model))
    lined: set[str] = set()
    current = model
    exact = True
    iterations = 0
    limit = len(model.edge_ids) + 1

    while iterations < limit:
        rows = resource_table(current)
        value = lambda_star(rows)
        if value >= target:
            break
        iterations += 1
        tied = epsilon_bottleneck_set(current, epsilon, rows)
        families = [relief_edges(current, item) - lined for item in tied]
        if any(not family for family in families):
            break  # a tied resource cannot be relieved by lining at all
        transversal = minimum_cost_transversal(families, costs)
        exact = exact and transversal.exact
        candidate = apply_lining(model, lined | transversal.edges, target_efficiency)
        if lambda_star(resource_table(candidate)) > value:
            lined |= transversal.edges
            current = candidate
            continue
        escalated = lined | {edge for family in families for edge in family}
        candidate = apply_lining(model, escalated, target_efficiency)
        if lambda_star(resource_table(candidate)) > value:
            lined = escalated
            current = candidate
            continue
        break  # every relieving edge is already at the target efficiency

    final = lambda_star(resource_table(current))
    unit = {} if costs is None else {k: Fraction(v) for k, v in costs.items()}
    return LiningPlan(
        target=target,
        target_efficiency=Fraction(target_efficiency),
        lined=tuple(sorted(lined)),
        cost=sum((unit.get(e, Fraction(1)) for e in lined), Fraction(0)),
        lambda_before=start,
        lambda_after=final,
        reached=final >= target,
        iterations=iterations,
        exact_transversals=exact,
    )


# --------------------------------------------------------------------------
# (P3): the mixed plan
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class MixedPlan:
    """Line every edge to ``eta_bar`` first, then widen what still binds."""

    target: Fraction
    target_efficiency: Fraction
    lambda_before: Fraction
    lambda_after_lining: Fraction
    expansion: ExpansionPlan
    widening_only_cost: Fraction

    @property
    def saving_fraction(self) -> Fraction:
        """Share of the pure-widening capacity cost avoided by lining first."""
        if self.widening_only_cost == 0:
            return Fraction(0)
        return 1 - self.expansion.cost / self.widening_only_cost


def mixed_plan(
    model: Benchmark,
    target: Fraction,
    target_efficiency: Fraction,
    edges: Iterable[str] | None = None,
    prices: Mapping[str, Fraction] | None = None,
) -> MixedPlan:
    """(P3): compare widening alone against lining followed by widening."""
    target = _check_target(target)
    selected = model.edge_ids if edges is None else tuple(edges)
    lined = apply_lining(model, selected, target_efficiency)
    return MixedPlan(
        target=target,
        target_efficiency=Fraction(target_efficiency),
        lambda_before=lambda_star(resource_table(model)),
        lambda_after_lining=lambda_star(resource_table(lined)),
        expansion=expansion_plan(lined, target, prices),
        widening_only_cost=expansion_plan(model, target, prices).cost,
    )
