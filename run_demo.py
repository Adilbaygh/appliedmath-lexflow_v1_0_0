"""Run one deterministic benchmark from a source checkout.

The small bootstrap below makes ``src/appliedmath_lexflow`` importable even when
an editable package installation has not yet been performed. Installing the
project with ``python -m pip install -e \".[dev]\"`` remains the recommended
workflow for development and testing.
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from appliedmath_lexflow.demo import main

if __name__ == "__main__":
    raise SystemExit(main())
