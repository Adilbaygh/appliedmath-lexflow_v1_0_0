#!/usr/bin/env python3
"""Generate the synthetic scale benchmark ``synthetic_scale_500u_1022e_4p.json``.

The file is a *synthetic* instance: none of its numbers come from any
irrigation system.  Its only purpose is to measure how the three-stage
procedure scales on the largest instance reported in the manuscript
(1023 nodes, 1022 reaches, 500 users, 4 periods).  It is deliberately
**not** used as evidence about the behaviour of the method under realistic
capacity structures; the instance families with capacities drawn
independently of their own loads (Section 4.10, Table 8, Appendix A.5) serve that
purpose.

Construction rule (fully deterministic; no random number generator)
-------------------------------------------------------------------
Topology
    Complete binary rooted tree.  The root is ``s``; the remaining nodes are
    ``n1`` ... ``n1022``.  Node ``n_k`` has parent ``s`` when ``(k - 1) // 2 == 0``
    and ``n_{(k-1)//2}`` otherwise, so ``n_m`` has children ``n_{2m+1}`` and
    ``n_{2m+2}``.  The reach feeding ``n_k`` is ``e_{k-1}``.

Users
    ``f1`` ... ``f500`` are attached to the terminals ``n511`` ... ``n1010``,
    each with weight 1.  The remaining 12 leaves carry no user, which is why
    22 reaches carry no load.

Periods
    ``k1`` ... ``k4``.

Efficiency
    Uniform within a period: ``eta(k_j) = (100 - j) / 100``, that is
    0.99, 0.98, 0.97 and 0.96.

Demand
    ``d(f_i, k_j) = 20 + ((7 i + 11 j) mod 31)``, an integer in [20, 50].
    The two coprime strides 7 and 11 against the modulus 31 spread the
    demands over the tree and over time without any random draw.

Reach capacity
    ``c(e, k_j) = 6/5 * L(e, k_j)`` for every reach that carries load, where
    ``L(e, k_j)`` is the inflow required to meet the full demand of the
    subtree below ``e``.  Reaches with no user downstream get capacity 1.
    The factor 6/5 keeps every reach slack, so that the source is the only
    binding resource; this is a deliberate simplification for a timing
    benchmark and is the reason the instance must not be read as evidence
    about capacity-limited behaviour.

Source capacity
    ``C(k_j) = (10 - j) / 10 * L(s, k_j)``, that is 0.9, 0.8, 0.7 and 0.6 of
    the full-supply requirement, so period ``k4`` is the Stage-1 bottleneck.

All parameters are stored as exact rational strings and all arithmetic here
is exact (``fractions.Fraction``), so the file is bit-for-bit reproducible
on any platform.

Usage
-----
    python Data/design/build_synthetic_scale.py           # verify
    python Data/design/build_synthetic_scale.py --write   # regenerate

Exit status is 0 when the generated instance matches the stored file and 1
otherwise.
"""

from __future__ import annotations

import argparse
import json
import sys
from fractions import Fraction
from pathlib import Path

TARGET = Path(__file__).resolve().parents[1] / "synthetic_scale_500u_1022e_4p.json"

N_NODES = 1023          # s plus n1 ... n1022
N_USERS = 500
FIRST_TERMINAL = 511    # user f_i sits on node n_{510 + i}
N_PERIODS = 4

DEMAND_BASE = 20
DEMAND_MODULUS = 31
DEMAND_USER_STRIDE = 7
DEMAND_PERIOD_STRIDE = 11

CAPACITY_HEADROOM = Fraction(6, 5)   # reach capacity / full-supply load
IDLE_REACH_CAPACITY = Fraction(1)    # reaches with no user downstream

NAME = "synthetic_scale_500u_1022e_4p"
DESCRIPTION = (
    "Maximum-size deterministic synthetic scale benchmark: complete binary "
    "rooted tree, 500 users, 1022 edges, 4 periods, and 2000 active "
    "period-user records. All parameters are rational strings; k4 source "
    "capacity is the Stage-1 bottleneck."
)


def _parent(k: int) -> str:
    index = (k - 1) // 2
    return "s" if index == 0 else f"n{index}"


def build() -> dict:
    nodes = ["s"] + [f"n{k}" for k in range(1, N_NODES)]
    edges = [{"id": f"e{k - 1}", "tail": _parent(k), "head": f"n{k}"}
             for k in range(1, N_NODES)]
    users = [{"id": f"f{i}", "terminal": f"n{FIRST_TERMINAL - 1 + i}", "weight": "1"}
             for i in range(1, N_USERS + 1)]
    periods = [f"k{j}" for j in range(1, N_PERIODS + 1)]

    children: dict[str, list[dict]] = {}
    for edge in edges:
        children.setdefault(edge["tail"], []).append(edge)
    terminal_of: dict[str, list[str]] = {}
    for user in users:
        terminal_of.setdefault(user["terminal"], []).append(user["id"])

    demand: dict[str, dict[str, str]] = {}
    efficiency: dict[str, dict[str, str]] = {}
    edge_capacity: dict[str, dict[str, str]] = {}
    source_capacity: dict[str, str] = {}

    for j, period in enumerate(periods, start=1):
        eta = Fraction(100 - j, 100)
        efficiency[period] = {edge["id"]: str(eta) for edge in edges}
        demand[period] = {
            f"f{i}": str(DEMAND_BASE + ((DEMAND_USER_STRIDE * i
                                         + DEMAND_PERIOD_STRIDE * j) % DEMAND_MODULUS))
            for i in range(1, N_USERS + 1)
        }

        loads: dict[str, Fraction] = {}

        def need_at(node: str) -> Fraction:
            total = Fraction(0)
            for uid in terminal_of.get(node, ()):
                total += Fraction(demand[period][uid])
            for edge in children.get(node, ()):
                inflow = need_at(edge["head"]) / eta
                loads[edge["id"]] = inflow
                total += inflow
            return total

        sys.setrecursionlimit(10000)
        source_load = need_at("s")

        edge_capacity[period] = {
            edge["id"]: str(CAPACITY_HEADROOM * loads[edge["id"]]
                            if loads[edge["id"]] else IDLE_REACH_CAPACITY)
            for edge in edges
        }
        source_capacity[period] = str(Fraction(10 - j, 10) * source_load)

    return {
        "name": NAME,
        "description": DESCRIPTION,
        "nodes": nodes,
        "source": "s",
        "edges": edges,
        "users": users,
        "periods": periods,
        "demand": demand,
        "source_capacity": source_capacity,
        "edge_capacity": edge_capacity,
        "efficiency": efficiency,
    }


def render(instance: dict) -> str:
    return json.dumps(instance, indent=2, ensure_ascii=False)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--write", action="store_true",
                        help="rewrite the benchmark file from the rule")
    parser.add_argument("--path", type=Path, default=TARGET,
                        help="benchmark file to check (default: %(default)s)")
    args = parser.parse_args(argv)

    instance = build()

    if args.write:
        args.path.write_text(render(instance), encoding="utf-8")
        print(f"wrote {args.path}")
        return 0

    stored = json.loads(args.path.read_text(encoding="utf-8"))
    if stored != instance:
        differing = [key for key in instance if stored.get(key) != instance[key]]
        print(f"MISMATCH: generated instance differs from {args.path.name}")
        print(f"  differing top-level keys: {differing}")
        return 1

    print(f"OK: {args.path.name} is reproduced exactly by the documented rule")
    print(f"    {len(instance['nodes'])} nodes, {len(instance['edges'])} reaches, "
          f"{len(instance['users'])} users, {len(instance['periods'])} periods, "
          f"no random number generator")
    return 0


if __name__ == "__main__":
    sys.exit(main())
