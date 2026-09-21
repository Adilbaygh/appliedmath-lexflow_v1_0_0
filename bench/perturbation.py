"""Parameter perturbation of the controlled Gone Abat Jap scenario.

See :mod:`appliedmath_lexflow.perturbation` for the five scenarios. Writes

    results/perturbation/{csv,excel}/perturbation_summary.*   one row per scenario
    results/perturbation/{csv,excel}/perturbation_draws.*     one row per draw

The results are deterministic (fixed seed, exact rational perturbations); the
run takes a few minutes, so it is kept out of ``run_analysis.py``, which
preserves the folder and records its hashes in the manifest.

    python bench/perturbation.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

import pandas as pd  # noqa: E402

from appliedmath_lexflow.io import load_benchmark                    # noqa: E402
from appliedmath_lexflow.perturbation import DRAWS, SEED, run, summarize  # noqa: E402
from appliedmath_lexflow.tables import write_table                  # noqa: E402

OUT = ROOT / "results" / "perturbation"


def main() -> int:
    model = load_benchmark(ROOT / "Data" / "benchmarks" / "gone_abat_jap.json")
    base, rows = run(model)
    summary = summarize(base, rows)
    write_table(pd.DataFrame([{"scenario": "baseline", **base}] + rows), OUT,
                "perturbation_draws")
    write_table(pd.DataFrame(summary), OUT, "perturbation_summary")
    print(f"Gone Abat Jap perturbation -- seed {SEED}, {DRAWS} draws per scenario")
    print(f"baseline: lambda* {base['lambda_star']:.6f}  bottleneck {base['bottleneck_argmin']}"
          f" (near set of {base['near_set_size']})  S* {base['stage2_satisfaction']:.6f}"
          f"  Omega* {base['stage3_variation']:.6f}")
    cols = ["lambda_star_p05", "lambda_star_median", "lambda_star_p95",
            "bottleneck_class_same", "argmin_within_baseline_near_set",
            "near_tie_draws_margin_below_1pct", "stage2_satisfaction_median",
            "stage3_variation_median", "draws_solved_at_1e-9"]
    print(pd.DataFrame(summary).set_index("scenario")[cols].to_string())
    print(f"written: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
