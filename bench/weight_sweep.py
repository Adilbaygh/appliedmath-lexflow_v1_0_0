"""Stage-2 service-weight sensitivity -- command-line report.

The computations live in :mod:`appliedmath_lexflow.weights`; ``python
run_analysis.py`` writes them as ``results/tables/{csv,excel}/
table_A4_weight_ratio_sweep`` and ``table_A5_weighting_rules``. The weights of
Table A5 are synthetic illustrations of auditable rules, not observed
licensed-area or priority data.

    python bench/weight_sweep.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from appliedmath_lexflow.io import load_benchmark                    # noqa: E402
from appliedmath_lexflow.weights import (  # noqa: E402
    weight_ratio_sweep,
    weighting_rules,
    weighting_rules_summary,
)


def main() -> int:
    data = ROOT / "Data" / "benchmarks"
    print("Three-period benchmark -- geometric weight sweep (Table A4)")
    print(f"{'w1:w2':>8} {'lambda*':>10} {'S*':>12} {'X1':>8} {'X2':>8} "
          f"{'Om(S2)':>9} {'Om(S3)':>9}")
    for r in weight_ratio_sweep(load_benchmark(data / "temporal_lexicographic.json")):
        print(f"{str(r['w1']) + ':' + str(r['w2']):>8} {r['lambda_star']:10.4f} "
              f"{r['stage2_weighted_satisfaction']:12.6f} {r['X1_stage3']:8.2f} "
              f"{r['X2_stage3']:8.2f} {r['omega_stage2']:9.4f} {r['omega_stage3']:9.4f}")
    print()
    print("Controlled Gone Abat Jap scenario -- weighting rules (Table A5; synthetic weights)")
    print(f"{'rule':34} {'lambda*':>10} {'min r':>10} {'S*':>12} {'Omega*':>12}")
    for r in weighting_rules(load_benchmark(data / "gone_abat_jap.json")):
        print(f"{r['rule']:34} {r['lambda_star']:10.6f} {r['minimum_ratio_stage3']:10.6f} "
              f"{r['stage2_weighted_satisfaction']:12.6f} {r['omega_stage3']:12.6f}")
    print()
    print("Winners and losers against uniform weights (per block)")
    print(f"{'rule':34} {'gain':>5} {'lose':>5} {'max gain':>9} {'max loss':>9} {'lowest r':>9}")
    for r in weighting_rules_summary(load_benchmark(data / "gone_abat_jap.json")):
        print(f"{r['rule']:34} {r['blocks_gaining']:>5} {r['blocks_losing']:>5} "
              f"{r['largest_relative_gain']:9.4f} {r['largest_relative_loss']:9.4f} "
              f"{r['lowest_ratio_any_block']:9.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
