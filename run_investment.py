"""Generate the inverse-design tables and figures for the conference paper.

Writes everything under ``results/investment/``. The article pipeline in
``run_analysis.py`` neither deletes nor hashes that folder, so the two papers'
outputs and provenance records stay independent.
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from appliedmath_lexflow.investment_reporting import generate_investment_results

if __name__ == "__main__":
    summary = generate_investment_results(PROJECT_ROOT)
    print("Inverse-design conference assets generated successfully.")
    for key, value in summary.items():
        print(f"{key}: {value}")
