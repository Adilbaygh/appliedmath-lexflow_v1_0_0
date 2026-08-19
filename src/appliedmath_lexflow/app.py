from __future__ import annotations

import argparse
import json
from pathlib import Path

from .demo import run_demo
from .reporting import generate_results, generate_single_benchmark_results


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="AppliedMath deterministic lexicographic flow project entry point."
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path.cwd(),
        help="Repository root (default: current working directory).",
    )
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("gui", help="Desktop GUI'ни ишга тушириш.")

    demo_parser = subparsers.add_parser(
        "demo", help="Битта benchmark'ни терминалда босқичма-босқич ечиш."
    )
    demo_parser.add_argument(
        "--benchmark",
        default="temporal_lexicographic",
        help="Benchmark номи.",
    )

    subparsers.add_parser(
        "analysis", help="Мақола учун барча жадвал ва расмларни яратиш."
    )

    save_result_parser = subparsers.add_parser(
        "save-result",
        help="Битта benchmark файлининг натижаларини берилган папкага сақлаш.",
    )
    save_result_parser.add_argument(
        "--benchmark-path", required=True, help="Benchmark JSON файлининг йўли."
    )
    save_result_parser.add_argument(
        "--output-dir", required=True, help="Натижалар сақланадиган папка."
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    project_root = args.project_root.resolve()
    command = args.command or "gui"

    if command == "gui":
        from .desktop_gui import main as gui_main

        return gui_main(project_root)
    if command == "demo":
        run_demo(project_root, args.benchmark)
        return 0
    if command == "analysis":
        summary = generate_results(project_root)
        print("AppliedMath article assets generated successfully.")
        for key, value in summary.items():
            print(f"{key}: {value}")
        return 0
    if command == "save-result":
        summary = generate_single_benchmark_results(args.benchmark_path, args.output_dir)
        # Emitted as the sole stdout line so desktop_backend.save_benchmark_result
        # can parse it directly instead of re-reading a file from disk.
        print(json.dumps(summary, ensure_ascii=False, default=str))
        return 0
    raise RuntimeError(f"Unknown command: {command}")


if __name__ == "__main__":
    raise SystemExit(main())
