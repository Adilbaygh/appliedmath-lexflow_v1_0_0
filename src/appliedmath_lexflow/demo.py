from __future__ import annotations

import argparse
from fractions import Fraction
from pathlib import Path

from .examples import load_all_benchmarks
from .lexicographic import solve_three_stage
from .stage1 import solve_stage1_closed_form, solve_stage1_lp
from .verification import verify_operator_exact


def _fraction(value: Fraction) -> str:
    return str(value.numerator) if value.denominator == 1 else f"{value.numerator}/{value.denominator}"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run one deterministic benchmark step by step and print the exact and "
            "numerical verification results."
        )
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path.cwd(),
        help="Repository root (default: current working directory).",
    )
    parser.add_argument(
        "--benchmark",
        default="temporal_lexicographic",
        help="Benchmark name (default: temporal_lexicographic).",
    )
    return parser


def run_demo(project_root: Path, benchmark_name: str) -> None:
    data_dir = project_root.resolve() / "Data" / "benchmarks"
    models = {model.name: model for model in load_all_benchmarks(data_dir)}
    if benchmark_name not in models:
        available = ", ".join(sorted(models))
        raise SystemExit(
            f"Unknown benchmark {benchmark_name!r}. Available benchmarks: {available}"
        )

    model = models[benchmark_name]
    closed = solve_stage1_closed_form(model)
    stage1_lp = solve_stage1_lp(model)
    canonical = {record: closed.lambda_star for record in model.active_records}
    operator_check = verify_operator_exact(model, canonical)
    solution = solve_three_stage(model)

    print("=" * 72)
    print(f"Benchmark: {model.name}")
    print(model.description)
    print("=" * 72)
    print(f"Nodes / edges / users / periods: {len(model.nodes)} / {len(model.edges)} / "
          f"{len(model.users)} / {len(model.periods)}")
    print("\nStage 1 analytical verification")
    print(f"  closed-form lambda*: {_fraction(closed.lambda_star)} "
          f"({float(closed.lambda_star):.12g})")
    print(f"  HiGHS LP lambda*:    {stage1_lp.lambda_star:.12g}")
    print(f"  absolute difference: {abs(stage1_lp.lambda_star - float(closed.lambda_star)):.3e}")
    print(f"  active resources:    {', '.join(closed.active_resources)}")

    print("\nIndependent flow verification")
    print(f"  exact operator-balance difference: "
          f"{_fraction(operator_check.maximum_absolute_difference)}")
    print(f"  exact node-balance residual:       "
          f"{_fraction(operator_check.maximum_node_residual)}")

    print("\nThree lexicographic stages")
    print("  stage      min ratio    weighted satisfaction    temporal variation")
    for stage in (solution.stage1, solution.stage2, solution.stage3):
        print(
            f"  {stage.name:<8}  {stage.minimum_ratio:>9.6f}    "
            f"{stage.weighted_satisfaction:>21.12f}    "
            f"{stage.temporal_variation:>18.12f}"
        )

    print("\nStage-3 allocation ratios")
    for period in model.periods:
        values = [
            f"{user}={solution.stage3.ratios[(period, user)]:.9f}"
            for user in model.user_ids
            if (period, user) in solution.stage3.ratios
        ]
        print(f"  {period}: " + ", ".join(values))

    print("\nVerification status: PASS")


def main() -> int:
    args = build_parser().parse_args()
    run_demo(args.project_root, args.benchmark)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
