"""Randomized robustness suite -- command-line report.

The generator, the checks and the per-family summary live in
:mod:`appliedmath_lexflow.robustness`; ``python run_analysis.py`` writes the
same results as ``results/tables/{csv,excel}/table_A3_robustness_*``. This
script prints them for a quick look.

Ten families are drawn. The first seven (seed 20260916) set every capacity as a
prescribed multiple of the full-demand gross load, so the binding resource and
lambda* are known in advance: they test agreement between implementations.
The last three (seed 20260921) do not. Two of them draw the source allocations
and the reach capacities independently of their own loads and test whether the
closed form identifies a bottleneck that was not planted; the third holds a
constant seasonal supply against period-varying demand. All three record how
often Stage 3 changes the Stage-2 allocation.

Run from the repository root:

    python bench/robustness_suite.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from appliedmath_lexflow.robustness import (  # noqa: E402
    GATES,
    SEED_INDEPENDENT,
    SEED_PRESCRIBED,
    run_suite,
    summarize,
)


def main() -> int:
    rows = run_suite()
    table = summarize(rows)
    print(f"Randomized robustness suite -- seeds {SEED_PRESCRIBED} (prescribed), "
          f"{SEED_INDEPENDENT} (independent)")
    short = [g.split("_", 1)[0] + ("r" if g.endswith("rel") else "") for g in GATES]
    print(f"{'family':58} {'n':>4} " + " ".join(f"{s:>9}" for s in short))
    for s in table:
        print(f"{s['family_label']:58} {s['instances']:>4} "
              + " ".join(f"{s['max_' + g]:9.2e}" for g in GATES))
    print()
    print("Bottleneck: tight = named resources tight at the LP and Stage-3 optima;")
    print("  suff. = LP value unchanged when all other resources are relaxed x10;")
    print("  nec.  = LP value rises when the named resources are relaxed by 0.1%.")
    print(f"{'family':58} {'tight':>8} {'suff.':>8} {'nec.':>8} {'found':>8}")
    for s in table:
        n = s['with_bottleneck']
        print(f"{s['family_label']:58} "
              + " ".join(f"{str(s[c]) + '/' + str(n):>8}" for c in (
                  'bottleneck_tight', 'bottleneck_sufficient',
                  'bottleneck_necessary', 'bottleneck_identified')))
    print()
    print("Stage 3: not det. = the one-sided face probe did not detect")
    print("  multiplicity of the Stage-2 optimum (Stage 3 redundant);")
    print("  active = Stage 3 lowered Omega; vertex = face is not a point but the")
    print("  solver's Stage-2 vertex was already the smoothest.")
    print(f"{'family':58} {'not det.':>8} {'active':>8} {'vertex':>8} {'median red.':>12}")
    for s in table:
        n = s['instances']
        print(f"{s['family_label']:58} "
              f"{str(s['stage2_multiplicity_not_detected']) + '/' + str(n):>8} "
              f"{str(s['stage3_active']) + '/' + str(n):>8} "
              f"{str(s['stage3_inactive_multiplicity_detected']) + '/' + str(n):>8} "
              f"{s['median_relative_reduction_when_active']:12.3f}")
    total = table[-1]
    print()
    print(f"instances generated      {total['instances']}")
    print(f"feasible by construction {total['instances']}  (r = 0 is always admissible)")
    print(f"gate violations          {total['gate_violations']}")
    status = "PASS" if total["gate_violations"] == 0 and (
        total["bottleneck_identified"] == total["with_bottleneck"]) else "FAIL"
    print("status                   " + status)
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
