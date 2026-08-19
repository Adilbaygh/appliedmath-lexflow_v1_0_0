"""Backward-compatible launcher for the desktop GUI.

The preferred entry point is ``python main.py``.
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from appliedmath_lexflow.desktop_gui import main


if __name__ == "__main__":
    raise SystemExit(main(PROJECT_ROOT))
