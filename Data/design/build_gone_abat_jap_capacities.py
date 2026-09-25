#!/usr/bin/env python3
"""Derive the conveyance capacities of the Gone Abat Jap benchmark.

This script makes the provenance of ``Data/benchmarks/gone_abat_jap.json``
auditable.  The benchmark mixes two kinds of parameters:

*Published parameters* -- network topology, reach efficiencies and per-period
user demands -- are taken from the Gone Abat Jap irrigation-system dataset
deposited at Mendeley Data (doi:10.17632/xt3gsf89n9.1, reference [39] of the
manuscript).  This script never modifies them.

*Imposed parameters* -- the per-period source allocation and the per-period
conveyance capacity of every reach -- are **set by the authors**, because the
published dataset contains no measured reach-by-reach capacity record and the
scarcity of the scenario is constructed rather than observed.  They are
produced by the rules stated in Appendix A.4 of the manuscript and
reimplemented here.

Reach capacities:

  1.  Nominal design capacities.  The thirty structural reaches keep the
      design discharge of the physical canal, converted to a volume per
      period by multiplying it by the length of the period.  The discharges
      are 7 m^3/s on the main-canal reaches, 3 m^3/s on K3 and 2 m^3/s on the
      distributor reaches; over a ten-day period these give 6 048 000 m^3,
      2 592 000 m^3 and 1 728 000 m^3 respectively.  They are far above any
      load and never bind.

  2.  Five instrumented reaches.  For K5, K6, K8, K11 and K12 no design
      figure is available, so one constant per reach is imposed:

          base(e) = 21/20 * max_p L(e, p),

      where L(e, p) is the inflow that reach e must carry in period p when
      every demand of its downstream subtree is met in full (computed from
      the published demands and efficiencies alone).  The factor 21/20 makes
      the *smallest* capacity-to-load ratio outside the scarcity pairs of
      step 4 equal to exactly 1.05.

  3.  Eleven-day periods.  Periods 15, 20 and 25 are eleven days long
      rather than ten, so every capacity of steps 1 and 2 is multiplied by
      11/10 there.  The same volume per second is carried for one day more.

  4.  Scarcity pairs.  In nine designated (reach, period) pairs the capacity
      is overridden by

          cap(e, p) = 9/10 * L(e, p),

      i.e. the reach can carry only 90% of the load, which is what makes the
      instance a scarcity instance at all.  These nine pairs are the
      constructed part of the experiment and are listed explicitly below.

Source allocations:

  5.  The allocation of period k is a prescribed multiple of the full-demand
      gross load at the head gate,

          Q(k) = xi(k) * L_src(k),

      with xi = 21/20 in the pre-peak periods 11-17, 17/20 in the peak
      periods 18-24 and 9/10 in the tail periods 25-26.  The peak value is
      what makes the source the binding resource and fixes lambda* = 0.85.

All arithmetic in this script is exact (``fractions.Fraction``); each result
is rounded half-up to six decimal places, which is the precision stored in
the JSON file.  That rounding, and not the published data, is the origin of
the differences of order 1e-13 between the seven peak-period source ratios.

Usage
-----
    python Data/design/build_gone_abat_jap_capacities.py            # verify
    python Data/design/build_gone_abat_jap_capacities.py --write    # rewrite
    python Data/design/build_gone_abat_jap_capacities.py --table    # print table

Exit status is 0 when the derived capacities reproduce the stored ones and
1 otherwise.
"""

from __future__ import annotations

import argparse
import json
import sys
from decimal import Decimal, ROUND_HALF_UP
from fractions import Fraction
from pathlib import Path

BENCHMARK = Path(__file__).resolve().parents[1] / "benchmarks" / "gone_abat_jap.json"

#: Reaches whose capacity is imposed by rule rather than taken from a design table.
INSTRUMENTED_REACHES = ("K5", "K6", "K8", "K11", "K12")

#: Nominal design capacity (m^3 per ten-day period) of the structural reaches:
#: the design discharge of the reach times 86400 s x 10 days.
DESIGN_CAPACITY = {
    "K3": Fraction(2592000),
    **{e: Fraction(6048000) for e in
       ("K1", "K2", "K4", "K7", "K9", "K10", "K13", "K15", "K17",
        "K24", "K26", "K27", "K28", "K29", "K30")},
    **{e: Fraction(1728000) for e in
       ("K14", "K16", "K18", "K19", "K20", "K21", "K22", "K23", "K25",
        "K31", "K32", "K33", "K34", "K35")},
}

#: The eleven-day periods, in which all capacities are multiplied by
#: RELAXED_FACTOR because the same discharge is carried for one day more.
RELAXED_PERIODS = ("15", "20", "25")
RELAXED_FACTOR = Fraction(11, 10)

#: Prescribed source ratio xi(k) = Q(k) / L_src(k) by period, Appendix A.4.
SOURCE_RATIOS = {
    **{str(k): Fraction(21, 20) for k in range(11, 18)},
    **{str(k): Fraction(17, 20) for k in range(18, 25)},
    **{str(k): Fraction(9, 10) for k in (25, 26)},
}

#: Headroom factor defining the imposed constant of an instrumented reach.
HEADROOM_FACTOR = Fraction(21, 20)

#: Binding factor applied in the nine constructed scarcity pairs.
SCARCITY_FACTOR = Fraction(9, 10)

#: The nine (reach, period) pairs in which scarcity is imposed.
SCARCITY_PAIRS = (
    ("K6", "11"),
    ("K5", "12"),
    ("K8", "13"),
    ("K12", "14"),
    ("K5", "15"),
    ("K5", "16"),
    ("K8", "17"),
    ("K6", "25"),
    ("K6", "26"),
)

DECIMALS = Decimal("1e-6")


def _round6(value: Fraction) -> str:
    """Round an exact rational half-up to six decimals and strip trailing zeros."""
    exact = Decimal(value.numerator) / Decimal(value.denominator)
    quantized = exact.quantize(DECIMALS, rounding=ROUND_HALF_UP)
    text = format(quantized, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


def full_supply_loads(data: dict) -> dict:
    """Inflow each reach must carry when every downstream demand is met in full.

    Uses only published quantities: topology, efficiencies and demands.
    """
    efficiency = data["efficiency"]
    children: dict[str, list[dict]] = {}
    for edge in data["edges"]:
        children.setdefault(edge["tail"], []).append(edge)
    terminals: dict[str, list[str]] = {}
    for user in data["users"]:
        terminals.setdefault(user["terminal"], []).append(user["id"])

    def need_at(node: str, period: str) -> Fraction:
        total = Fraction(0)
        for uid in terminals.get(node, ()):
            total += Fraction(data["demand"][period][uid])
        for edge in children.get(node, ()):
            total += need_at(edge["head"], period) / Fraction(efficiency[period][edge["id"]])
        return total

    loads: dict[tuple[str, str], Fraction] = {}
    for period in data["periods"]:
        for edge in data["edges"]:
            eta = Fraction(efficiency[period][edge["id"]])
            loads[(edge["id"], period)] = need_at(edge["head"], period) / eta
    return loads


def full_source_loads(data: dict) -> dict:
    """Gross volume the head gate must release when every demand is met in full.

    It is the sum of the full-demand loads of the reaches leaving the source,
    so it uses only published quantities.
    """
    loads = full_supply_loads(data)
    source = data["source"]
    outgoing = [edge["id"] for edge in data["edges"] if edge["tail"] == source]
    return {period: sum((loads[(e, period)] for e in outgoing), Fraction(0))
            for period in data["periods"]}


def derive_source_capacity(data: dict) -> dict:
    """Return the source_capacity mapping implied by the Appendix A.4 rule."""
    loads = full_source_loads(data)
    missing = [p for p in data["periods"] if p not in SOURCE_RATIOS]
    if missing:
        raise KeyError(f"no source ratio for periods: {missing}")
    return {p: _round6(SOURCE_RATIOS[p] * loads[p]) for p in data["periods"]}


def compare_source(data: dict, derived: dict) -> list[tuple[str, str, str]]:
    """Return the list of (period, stored, derived) disagreements."""
    stored = data["source_capacity"]
    return [(p, stored[p], v) for p, v in derived.items()
            if Decimal(stored[p]) != Decimal(v)]


def derive_capacities(data: dict) -> dict:
    """Return the edge_capacity mapping implied by the Appendix A.4 rule."""
    loads = full_supply_loads(data)
    periods = list(data["periods"])
    edge_ids = [edge["id"] for edge in data["edges"]]

    base: dict[str, Fraction] = dict(DESIGN_CAPACITY)
    for reach in INSTRUMENTED_REACHES:
        base[reach] = HEADROOM_FACTOR * max(loads[(reach, p)] for p in periods)

    missing = [e for e in edge_ids if e not in base]
    if missing:
        raise KeyError(f"no capacity rule for reaches: {missing}")

    scarcity = set(SCARCITY_PAIRS)
    capacities: dict[str, dict[str, str]] = {}
    for period in periods:
        factor = RELAXED_FACTOR if period in RELAXED_PERIODS else Fraction(1)
        row: dict[str, str] = {}
        for edge_id in edge_ids:
            if (edge_id, period) in scarcity:
                value = SCARCITY_FACTOR * loads[(edge_id, period)]
            else:
                value = factor * base[edge_id]
            row[edge_id] = _round6(value)
        capacities[period] = row
    return capacities


def compare(data: dict, derived: dict) -> list[tuple[str, str, str, str]]:
    """Return the list of (edge, period, stored, derived) disagreements."""
    stored = data["edge_capacity"]
    diffs = []
    for period, row in derived.items():
        for edge_id, value in row.items():
            have = stored[period][edge_id]
            if Decimal(have) != Decimal(value):
                diffs.append((edge_id, period, have, value))
    return diffs


def print_table(data: dict) -> None:
    loads = full_supply_loads(data)
    stored = data["edge_capacity"]
    scarcity = set(SCARCITY_PAIRS)
    print(f"{'reach':>6} {'period':>7} {'capacity':>16} {'load':>16} {'ratio':>8}  role")
    for reach in INSTRUMENTED_REACHES:
        for period in data["periods"]:
            cap = Fraction(stored[period][reach])
            load = loads[(reach, period)]
            ratio = f"{float(cap / load):.4f}" if load else "-"
            role = "scarcity" if (reach, period) in scarcity else (
                "relaxed" if period in RELAXED_PERIODS else "nominal")
            print(f"{reach:>6} {period:>7} {float(cap):16.6f} {float(load):16.6f} {ratio:>8}  {role}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--write", action="store_true",
                        help="rewrite the benchmark file with the derived capacities")
    parser.add_argument("--table", action="store_true",
                        help="print the capacity/load table of the instrumented reaches")
    parser.add_argument("--path", type=Path, default=BENCHMARK,
                        help="benchmark file to check (default: %(default)s)")
    args = parser.parse_args(argv)

    data = json.loads(args.path.read_text(encoding="utf-8"))
    derived = derive_capacities(data)
    diffs = compare(data, derived)
    derived_source = derive_source_capacity(data)
    source_diffs = compare_source(data, derived_source)

    if args.table:
        print_table(data)
        print()

    if args.write:
        data["source_capacity"] = derived_source
        data["edge_capacity"] = derived
        args.path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n",
                             encoding="utf-8")
        print(f"wrote {args.path}")
        return 0

    if diffs or source_diffs:
        print(f"MISMATCH: {len(diffs)} capacity value(s) and "
              f"{len(source_diffs)} source allocation(s) differ from the A.4 rule")
        for edge_id, period, have, want in diffs[:20]:
            print(f"  {edge_id:>5} period {period:>3}: stored {have} != derived {want}")
        for period, have, want in source_diffs[:20]:
            print(f"  source period {period:>3}: stored {have} != derived {want}")
        return 1

    n = len(data["edges"]) * len(data["periods"])
    print(f"OK: all {n} conveyance capacities and all "
          f"{len(data['periods'])} source allocations of {args.path.name} "
          f"reproduce the Appendix A.4 rules exactly")
    print(f"    {len(DESIGN_CAPACITY)} design reaches, "
          f"{len(INSTRUMENTED_REACHES)} imposed reaches, "
          f"{len(SCARCITY_PAIRS)} scarcity pairs, "
          f"{len(RELAXED_PERIODS)} relaxed periods")
    return 0


if __name__ == "__main__":
    sys.exit(main())
