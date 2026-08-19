"""Primary entry point for the AppliedMath LexFlow project.

Without a subcommand this file opens the desktop GUI.  It can also run the
terminal demo or regenerate all article assets from the same main entry point.
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from appliedmath_lexflow.app import main  # noqa: E402


if __name__ == "__main__":
    if "--project-root" not in sys.argv:
        sys.argv[1:1] = ["--project-root", str(PROJECT_ROOT)]
    raise SystemExit(main())
