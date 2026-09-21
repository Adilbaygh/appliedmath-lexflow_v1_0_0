"""Period- and reach-level parameters of the controlled Gone Abat Jap scenario.

Table A2 of the manuscript and the statements of its Appendix A.4 about the
reach capacities are derived from the benchmark data by these two functions,
so that the analysis run regenerates them together with every other table.

* ``period_parameters``: per period the number of active blocks, the net
  demand, the full-demand gross source load, the source allocation and their
  ratio (Table A2).
* ``reach_ratios``: per period and reach the full-demand gross load, the
  capacity and their ratio; pairs without load are listed with an empty ratio,
  because their capacity constraint is vacuous (Appendix A.4).

All quantities are computed exactly in rational arithmetic and reported as
floats.
"""

from __future__ import annotations

from .domain import Benchmark
from .stage1 import full_demand_loads


def period_parameters(model: Benchmark) -> list[dict[str, object]]:
    source_loads, _ = full_demand_loads(model)
    rows = []
    for period in model.periods:
        demand = [model.demand[period][user.user_id] for user in model.users]
        load = source_loads[period]
        allocation = model.source_capacity[period]
        rows.append({
            "period": period,
            "active_blocks": sum(1 for d in demand if d > 0),
            "net_demand": float(sum(demand)),
            "gross_source_load": float(load),
            "source_allocation": float(allocation),
            "source_ratio": float(allocation / load) if load > 0 else None,
        })
    return rows


def reach_ratios(model: Benchmark) -> list[dict[str, object]]:
    _, edge_loads = full_demand_loads(model)
    rows = []
    for period in model.periods:
        for edge_id in model.edge_ids:
            load = edge_loads[(period, edge_id)]
            capacity = model.edge_capacity[period][edge_id]
            rows.append({
                "period": period,
                "edge": edge_id,
                "full_demand_load": float(load),
                "capacity": float(capacity),
                "ratio": float(capacity / load) if load > 0 else None,
            })
    return rows
