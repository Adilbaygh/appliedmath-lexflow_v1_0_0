"""Generate all deterministic article tables, figures, and manifests.

This entry point supports direct execution from an unpacked source tree. An
editable installation is still recommended for normal VS Code development.
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from appliedmath_lexflow.reporting import generate_results


if __name__ == "__main__":
    summary = generate_results(PROJECT_ROOT)
    print("AppliedMath article assets generated successfully.")
    for key, value in summary.items():
        print(f"{key}: {value}")
