from __future__ import annotations

import argparse
import json
from pathlib import Path

from .reporting import generate_results


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate exact tables and publication figures for the AppliedMath article."
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path.cwd(),
        help="Repository root (default: current working directory).",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    summary = generate_results(args.project_root)
    print(json.dumps(summary, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
