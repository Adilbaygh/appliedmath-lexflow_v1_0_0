"""Deterministic scale-suite construction and sparse Stage-1 verification.

The manuscript reports five complete-binary-tree instances.  Earlier versions
kept only one generated JSON file and a manually copied table, which allowed the
table to drift from the actual 0.60 benchmark.  This module makes the generator
and the HiGHS verification executable and testable.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from fractions import Fraction

import numpy as np
from scipy.optimize import linprog
from scipy.sparse import csr_matrix

from .domain import Benchmark, Edge, User
from .io import validate_benchmark
from .operators import flows_from_node_balance_exact, user_paths
from .stage1 import Stage1ClosedForm, Stage1LP

DEFAULT_SCALE_SIZES = (20, 50, 100, 250, 500)


def _next_power_of_two(value: int) -> int:
    if value < 1:
        raise ValueError("user_count must be positive.")
    return 1 << (value - 1).bit_length()


def build_scale_benchmark(user_count: int) -> Benchmark:
    """Build the prespecified four-period complete-binary-tree benchmark.

    The deterministic recipe is:

    * ``P = 2**ceil(log2(user_count))`` leaves;
    * ``d[k,f] = 20 + ((7 f + 11 k) mod 31)``;
    * period efficiencies ``(0.99, 0.98, 0.97, 0.96)`` on every edge;
    * every positive-load edge capacity is ``1.20`` times full-demand gross
      load; unused padding branches receive the harmless positive capacity 1;
    * source capacities are ``(0.90, 0.80, 0.70, 0.60)`` times full load.

    All quantities are exact :class:`Fraction` objects.  The final-period source
    is therefore the unique Stage-1 bottleneck and ``lambda*=3/5``.
    """
    leaf_count = _next_power_of_two(user_count)
    non_source_count = 2 * leaf_count - 2
    nodes = ("s",) + tuple(f"n{idx}" for idx in range(1, non_source_count + 1))

    edges: list[Edge] = []
    for child_idx in range(1, non_source_count + 1):
        parent_idx = (child_idx - 1) // 2
        tail = "s" if parent_idx == 0 else f"n{parent_idx}"
        edges.append(Edge(f"e{child_idx - 1}", tail, f"n{child_idx}"))

    first_leaf = leaf_count - 1
    users = tuple(
        User(f"f{idx}", f"n{first_leaf + idx - 1}", Fraction(1))
        for idx in range(1, user_count + 1)
    )
    periods = ("k1", "k2", "k3", "k4")
    demand = {
        period: {
            user.user_id: Fraction(
                20 + ((7 * user_idx + 11 * period_idx) % 31)
            )
            for user_idx, user in enumerate(users, start=1)
        }
        for period_idx, period in enumerate(periods, start=1)
    }
    period_efficiency = (
        Fraction(99, 100),
        Fraction(49, 50),
        Fraction(97, 100),
        Fraction(24, 25),
    )
    efficiency = {
        period: {edge.edge_id: eta for edge in edges}
        for period, eta in zip(periods, period_efficiency)
    }

    zero_source = {period: Fraction(0) for period in periods}
    zero_edges = {
        period: {edge.edge_id: Fraction(0) for edge in edges}
        for period in periods
    }
    provisional = Benchmark(
        name=f"synthetic_scale_{user_count}u_{len(edges)}e_4p",
        description=(
            "Deterministic complete-binary-tree scale benchmark with exact "
            "rational data and a final-period source bottleneck."
        ),
        nodes=nodes,
        source="s",
        edges=tuple(edges),
        users=users,
        periods=periods,
        demand=demand,
        source_capacity=zero_source,
        edge_capacity=zero_edges,
        efficiency=efficiency,
    )

    full_ratios = {record: Fraction(1) for record in provisional.active_records}
    edge_loads, source_loads = flows_from_node_balance_exact(provisional, full_ratios)
    source_factors = (
        Fraction(9, 10),
        Fraction(4, 5),
        Fraction(7, 10),
        Fraction(3, 5),
    )
    source_capacity = {
        period: factor * source_loads[period]
        for period, factor in zip(periods, source_factors)
    }
    edge_capacity = {
        period: {
            edge.edge_id: (
                Fraction(6, 5) * edge_loads[(period, edge.edge_id)]
                if edge_loads[(period, edge.edge_id)] > 0
                else Fraction(1)
            )
            for edge in edges
        }
        for period in periods
    }
    model = replace(
        provisional,
        source_capacity=source_capacity,
        edge_capacity=edge_capacity,
    )
    validate_benchmark(model)
    return model


def solve_stage1_closed_form_tree(model: Benchmark) -> Stage1ClosedForm:
    """Evaluate the Stage-1 formula using independent node-balance aggregation."""
    full_ratios = {record: Fraction(1) for record in model.active_records}
    edge_loads, source_loads = flows_from_node_balance_exact(model, full_ratios)
    candidates: list[tuple[Fraction, str]] = [(Fraction(1), "demand_upper_bound")]
    for period, load in source_loads.items():
        if load > 0:
            candidates.append((model.source_capacity[period] / load, f"source:{period}"))
    for (period, edge_id), load in edge_loads.items():
        if load > 0:
            candidates.append(
                (model.edge_capacity[period][edge_id] / load, f"edge:{period}:{edge_id}")
            )
    lambda_star = min(value for value, _ in candidates)
    active = tuple(label for value, label in candidates if value == lambda_star)
    return Stage1ClosedForm(lambda_star, source_loads, edge_loads, active)


def solve_stage1_sparse_lp(
    model: Benchmark, feasibility_tolerance: float = 1e-9
) -> Stage1LP:
    """Solve Stage 1 with a path-sparse HiGHS matrix.

    Only route nonzeros are stored, so the 500-user instance avoids a dense
    ``4092 x 2000`` physical matrix while representing the identical LP.
    """
    records = model.active_records
    record_index = {record: idx for idx, record in enumerate(records)}
    paths = user_paths(model)
    edge_position = {edge_id: idx for idx, edge_id in enumerate(model.edge_ids)}
    resources_per_period = 1 + len(model.edges)
    physical_rows = len(model.periods) * resources_per_period
    total_rows = physical_rows + len(records)
    lambda_col = len(records)

    row_ids: list[int] = []
    col_ids: list[int] = []
    values: list[float] = []
    rhs = np.zeros(total_rows, dtype=float)

    for period_idx, period in enumerate(model.periods):
        base_row = period_idx * resources_per_period
        rhs[base_row] = float(model.source_capacity[period])
        for edge_id, edge_idx in edge_position.items():
            rhs[base_row + 1 + edge_idx] = float(
                model.edge_capacity[period][edge_id]
            )

        for user in model.users:
            record = (period, user.user_id)
            if record not in record_index:
                continue
            col = record_index[record]
            gross_per_net = Fraction(1)
            suffix: dict[str, Fraction] = {}
            for edge_id in reversed(paths[user.user_id]):
                gross_per_net /= model.efficiency[period][edge_id]
                suffix[edge_id] = gross_per_net
            demand = model.demand[period][user.user_id]

            row_ids.append(base_row)
            col_ids.append(col)
            values.append(float(gross_per_net * demand))
            for edge_id, coefficient in suffix.items():
                row_ids.append(base_row + 1 + edge_position[edge_id])
                col_ids.append(col)
                values.append(float(coefficient * demand))

    for idx in range(len(records)):
        row = physical_rows + idx
        row_ids.extend((row, row))
        col_ids.extend((idx, lambda_col))
        values.extend((-1.0, 1.0))

    a_ub = csr_matrix(
        (values, (row_ids, col_ids)),
        shape=(total_rows, len(records) + 1),
        dtype=float,
    )
    objective = np.zeros(len(records) + 1, dtype=float)
    objective[lambda_col] = -1.0
    result = linprog(
        objective,
        A_ub=a_ub,
        b_ub=rhs,
        bounds=[(0.0, 1.0)] * (len(records) + 1),
        method="highs",
        options={
            "primal_feasibility_tolerance": feasibility_tolerance,
            "dual_feasibility_tolerance": feasibility_tolerance,
        },
    )
    if not result.success:
        raise RuntimeError(f"Sparse scale Stage 1 failed: {result.message}")
    ratios = {
        record: float(result.x[idx]) for idx, record in enumerate(records)
    }
    return Stage1LP(
        float(result.x[lambda_col]),
        ratios,
        int(result.status),
        str(result.message),
    )


@dataclass(frozen=True, slots=True)
class ScaleVerification:
    users: int
    nodes: int
    edges: int
    periods: int
    active_records: int
    principal_inequalities: int
    lambda_closed_form: Fraction
    lambda_lp: float
    absolute_difference: float
    active_resources: tuple[str, ...]


def verify_scale_suite(
    user_counts: tuple[int, ...] = DEFAULT_SCALE_SIZES,
) -> tuple[ScaleVerification, ...]:
    """Generate and independently verify every prespecified scale instance."""
    rows: list[ScaleVerification] = []
    for user_count in user_counts:
        model = build_scale_benchmark(user_count)
        closed = solve_stage1_closed_form_tree(model)
        lp = solve_stage1_sparse_lp(model)
        m_phys = len(model.periods) * (1 + len(model.edges))
        rows.append(
            ScaleVerification(
                users=len(model.users),
                nodes=len(model.nodes),
                edges=len(model.edges),
                periods=len(model.periods),
                active_records=len(model.active_records),
                principal_inequalities=m_phys + len(model.active_records),
                lambda_closed_form=closed.lambda_star,
                lambda_lp=lp.lambda_star,
                absolute_difference=abs(lp.lambda_star - float(closed.lambda_star)),
                active_resources=closed.active_resources,
            )
        )
    return tuple(rows)
