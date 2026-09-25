"""Computation time of the alternative allocation rules.

The allocations and their quality measures are part of the deterministic
results (``results/tables/*/table_9_rule_comparison*``). This script adds the
wall-clock time of every rule, which is machine dependent:

* on each of the six benchmarks, every rule is run REPEATS times after one
  warm-up and the median and interquartile range are reported;
* on the 200 randomized instances of the second seed group, every rule is
  run once per instance and the median over instances is reported.

Output: results/timing/rule_comparison_timing.csv (and environment.json).

    python bench/compare_rules.py
"""

from __future__ import annotations

import csv
import json
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "bench"))

from appliedmath_lexflow.comparison import RULE_LABELS, rules  # noqa: E402
from appliedmath_lexflow.examples import load_all_benchmarks    # noqa: E402
from appliedmath_lexflow.robustness import generate_instances   # noqa: E402
from scale_timing import environment                             # noqa: E402

OUT = ROOT / "results" / "timing"
REPEATS = 10


def _ms(fn, model) -> float:
    t = time.perf_counter()
    fn(model)
    return (time.perf_counter() - t) * 1000.0


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "environment.json").write_text(json.dumps(environment(), indent=2),
                                          encoding="utf-8")
    table = []
    for model in load_all_benchmarks(ROOT / "Data" / "benchmarks"):
        for key, fn in rules().items():
            fn(model)  # warm-up
            times = [_ms(fn, model) for _ in range(REPEATS)]
            q = statistics.quantiles(times, n=4, method="inclusive")
            table.append({
                "set": model.name, "rule": key, "rule_label": RULE_LABELS[key],
                "runs": REPEATS, "median_ms": statistics.median(times),
                "q1_ms": q[0], "q3_ms": q[2], "min_ms": min(times),
            })
            print(f"{model.name:34} {key:26} {statistics.median(times):10.2f} ms")
    # Same selection as reporting.py: the second seed group, i.e. every family
    # whose capacities are not prescribed multiples of their own loads.
    random_models = [m for fam, m in generate_instances()
                     if fam.capacity_rule != "prescribed"]
    for key, fn in rules().items():
        times = [_ms(fn, m) for m in random_models]
        q = statistics.quantiles(times, n=4, method="inclusive")
        table.append({
            "set": f"randomized independent capacities ({len(random_models)} instances)",
            "rule": key, "rule_label": RULE_LABELS[key], "runs": len(random_models),
            "median_ms": statistics.median(times), "q1_ms": q[0], "q3_ms": q[2],
            "min_ms": min(times),
        })
        print(f"{'randomized (200)':34} {key:26} {statistics.median(times):10.2f} ms")
    with open(OUT / "rule_comparison_timing.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(table[0]))
        w.writeheader()
        w.writerows(table)
    print(f"written: {OUT / 'rule_comparison_timing.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
