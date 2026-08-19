from __future__ import annotations

import hashlib
import json
import platform
import shutil
import sys
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path

import matplotlib
import networkx as nx
import numpy as np
import pandas as pd
import scipy

from .domain import Benchmark
from .examples import load_all_benchmarks
from .figures import (
    compute_operator_agreement_rows,
    configure_matplotlib,
    plot_benchmark_tree,
    plot_bottleneck_regions,
    plot_capacity_fairness,
    plot_lexicographic_profiles,
    plot_lexicographic_profiles_per_user,
    plot_matrix_patterns,
    plot_operator_agreement_scatter,
)
from .io import load_benchmark
from .lexicographic import solve_three_stage
from .operators import build_operator_exact
from .robust import (
    price_of_fairness,
    solve_leximin,
    stage2_variation_bounds,
)
from .stage1 import solve_stage1_closed_form, solve_stage1_lp
from .tables import write_table
from .verification import maximum_physical_violation, verify_operator_exact


def _fraction_string(value: Fraction) -> str:
    return (
        str(value.numerator)
        if value.denominator == 1
        else f"{value.numerator}/{value.denominator}"
    )


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _reset_generated_directories(output_root: Path) -> list[str]:
    """Remove all previously generated assets before producing a fresh result package.

    ``gui_exports`` (ad hoc single-benchmark CSV exports from the desktop app)
    is preserved across regenerations; everything else, including any
    per-benchmark result folders from a previous run, is cleared.

    An entry that cannot be removed (e.g. an image from a previous run is
    still open in a viewer, Explorer, or the IDE, which holds a Windows file
    lock) is skipped rather than aborting the whole run — that previously
    left ``results/`` in a half-deleted state (some top-level folders wiped
    and never recreated) whenever cleanup failed partway through. The
    skipped paths are returned so the caller can warn about them; the stale
    files inside a skipped folder are still overwritten by the regeneration
    step below whenever the lock allows writes but not deletion.
    """
    locked: list[str] = []
    if output_root.exists():
        for entry in output_root.iterdir():
            if entry.name == "gui_exports":
                continue
            try:
                if entry.is_dir():
                    shutil.rmtree(entry)
                else:
                    entry.unlink()
            except OSError:
                locked.append(str(entry))
    for relative in ("tables", "figure_data", "figures", "manifests"):
        (output_root / relative).mkdir(parents=True, exist_ok=True)
    return locked


def generate_results(project_root: str | Path) -> dict[str, object]:
    project_root = Path(project_root).resolve()
    data_dir = project_root / "Data" / "benchmarks"
    output_root = project_root / "results"
    locked_paths = _reset_generated_directories(output_root)
    table_dir = output_root / "tables"
    manifest_dir = output_root / "manifests"

    models = load_all_benchmarks(data_dir)
    solved: list[tuple[Benchmark, object]] = []
    closed_rows: list[dict[str, object]] = []
    operator_rows: list[dict[str, object]] = []
    stage_rows: list[dict[str, object]] = []
    dimension_rows: list[dict[str, object]] = []

    maximum_node_residual = Fraction(0)
    maximum_physical_residual = 0.0

    for model in models:
        closed = solve_stage1_closed_form(model)
        lp = solve_stage1_lp(model)
        solution = solve_three_stage(model)
        solved.append((model, solution))

        canonical = {record: closed.lambda_star for record in model.active_records}
        operator_check = verify_operator_exact(model, canonical)
        a_coeff, b_coeff = build_operator_exact(model)
        physical_violation = maximum_physical_violation(
            model, solution.stage3.ratios, a_coeff, b_coeff
        )
        maximum_node_residual = max(
            maximum_node_residual, operator_check.maximum_node_residual
        )
        maximum_physical_residual = max(
            maximum_physical_residual, physical_violation
        )

        closed_rows.append(
            {
                "benchmark": model.name,
                "nodes": len(model.nodes),
                "edges": len(model.edges),
                "users": len(model.users),
                "periods": len(model.periods),
                "lambda_closed_form_exact": _fraction_string(closed.lambda_star),
                "lambda_closed_form": float(closed.lambda_star),
                "lambda_lp": lp.lambda_star,
                "absolute_difference": abs(
                    lp.lambda_star - float(closed.lambda_star)
                ),
                "active_resources": "; ".join(closed.active_resources),
            }
        )
        operator_rows.append(
            {
                "benchmark": model.name,
                "edge_period_pairs": len(model.edges) * len(model.periods),
                "max_exact_operator_balance_difference": _fraction_string(
                    operator_check.maximum_absolute_difference
                ),
                "max_exact_node_residual": _fraction_string(
                    operator_check.maximum_node_residual
                ),
                "max_stage3_physical_violation": physical_violation,
            }
        )

        for stage in (solution.stage1, solution.stage2, solution.stage3):
            stage_rows.append(
                {
                    "benchmark": model.name,
                    "stage": stage.name,
                    "minimum_service_ratio": stage.minimum_ratio,
                    "weighted_satisfaction": stage.weighted_satisfaction,
                    "temporal_variation": stage.temporal_variation,
                    "solver_status": stage.status,
                }
            )

        n = len(model.active_records)
        p = sum(
            1
            for user in model.user_ids
            for left, right in zip(model.periods[:-1], model.periods[1:])
            if model.demand[left][user] > 0 and model.demand[right][user] > 0
        )
        m_phys = len(model.periods) * (1 + len(model.edges))
        dimension_rows.extend(
            [
                {
                    "benchmark": model.name,
                    "stage": "Stage 1",
                    "variables": n + 1,
                    "principal_constraints": n + m_phys,
                },
                {
                    "benchmark": model.name,
                    "stage": "Stage 2",
                    "variables": n,
                    "principal_constraints": m_phys,
                },
                {
                    "benchmark": model.name,
                    "stage": "Stage 3",
                    "variables": n + p,
                    "principal_constraints": m_phys + 1 + 2 * p,
                },
            ]
        )

    # Solver-independent (invariant) diagnostics. Table 3's Stage-2 temporal
    # variation is a property of ONE arbitrary optimal vertex; the following two
    # tables report quantities that depend only on the model.
    invariant_rows: list[dict] = []
    leximin_rows: list[dict] = []
    for model, _ in solved:
        bounds = stage2_variation_bounds(model)
        pof = price_of_fairness(model)
        invariant_rows.append(
            {
                "benchmark": model.name,
                "omega_min": None if bounds is None else bounds.omega_min,
                "omega_min_exact": None
                if bounds is None or bounds.omega_min_exact is None
                else _fraction_string(bounds.omega_min_exact),
                "omega_max": None if bounds is None else bounds.omega_max,
                "omega_max_exact": None
                if bounds is None or bounds.omega_max_exact is None
                else _fraction_string(bounds.omega_max_exact),
                "invariant_reduction_fraction": None
                if bounds is None
                else bounds.reduction_fraction,
                "efficiency_optimum_Z_eff": pof.efficiency_optimum,
                "fair_delivery_Z_fair": pof.fair_delivery,
                "price_of_fairness": pof.price_of_fairness,
            }
        )
        try:
            lex = solve_leximin(model)
        except ValueError as exc:
            # Progressive filling is O(records) LPs per round; it is refused on
            # benchmarks far larger than the exact article examples (e.g. the
            # real-network gone_abat_jap). Record the skip explicitly rather than
            # crash or silently omit the row.
            leximin_rows.append(
                {
                    "benchmark": model.name,
                    "leximin_minimum_ratio": None,
                    "leximin_weighted_satisfaction": None,
                    "leximin_temporal_variation": None,
                    "leximin_levels": f"skipped: {exc}",
                }
            )
        else:
            leximin_rows.append(
                {
                    "benchmark": model.name,
                    "leximin_minimum_ratio": lex.minimum_ratio,
                    "leximin_weighted_satisfaction": lex.weighted_satisfaction,
                    "leximin_temporal_variation": lex.temporal_variation,
                    "leximin_levels": "; ".join(f"{value:.6f}" for value in lex.levels),
                }
            )

    tables = {
        "table_1_closed_form_verification": pd.DataFrame(closed_rows),
        "table_2_operator_balance_verification": pd.DataFrame(operator_rows),
        "table_3_lexicographic_stages": pd.DataFrame(stage_rows),
        "table_4_formulation_dimensions": pd.DataFrame(dimension_rows),
        "table_5_invariant_variation_and_price_of_fairness": pd.DataFrame(invariant_rows),
        "table_6_leximin_allocation": pd.DataFrame(leximin_rows),
    }
    for stem, dataframe in tables.items():
        write_table(dataframe, table_dir, stem)

    temporal_model, temporal_solution = next(
        (model, solution)
        for model, solution in solved
        if model.name == "temporal_lexicographic"
    )

    configure_matplotlib()
    figure_warnings = list(locked_paths)
    # Cross-benchmark, theory-only figures that are not tied to any single
    # network's topology stay directly under results/.
    plot_capacity_fairness(output_root)
    plot_bottleneck_regions(output_root)
    agreement_data = compute_operator_agreement_rows(solved)
    plot_operator_agreement_scatter(
        agreement_data, output_root, title="All benchmarks (pooled)"
    )

    # Every benchmark's own tree/profile/matrix/agreement figures and their
    # source CSVs are written into results/<benchmark_name>/ so each network's
    # results live in a separate, self-contained folder. A benchmark whose
    # previous output is locked by another program (e.g. an image viewer)
    # is skipped with a warning instead of aborting every other benchmark.
    for model, solution in solved:
        benchmark_root = output_root / model.name
        try:
            plot_benchmark_tree(model, benchmark_root)
            plot_lexicographic_profiles(model, solution, benchmark_root)
            plot_lexicographic_profiles_per_user(model, solution, benchmark_root)
            plot_matrix_patterns(model, benchmark_root)
            own_agreement = agreement_data[agreement_data["benchmark"] == model.name]
            plot_operator_agreement_scatter(own_agreement, benchmark_root, title=model.name)
        except OSError as exc:
            figure_warnings.append(f"{model.name}: {exc}")

    closed_form_max_difference = max(
        row["absolute_difference"] for row in closed_rows
    )
    # INVARIANT temporal-variation reduction. The previous summary divided by
    # ``stage2.temporal_variation`` -- the variation of the single Stage-2 vertex
    # the solver happened to return (0.75 here, but 1.05 at other vertices of the
    # same optimal face), giving a non-reproducible "46.7%". We instead report
    # the range over the whole Stage-2 optimal face: Omega_max (worst any solver
    # could show) down to Omega_min = the Stage-3 optimum, and the guaranteed
    # reduction (Omega_max - Omega_min) / Omega_max.
    temporal_bounds = stage2_variation_bounds(temporal_model)
    temporal_leximin = solve_leximin(temporal_model)
    summary = {
        "benchmark_count": len(models),
        "closed_form_max_difference": closed_form_max_difference,
        "operator_exact_max_difference": "0",
        "node_exact_max_residual": _fraction_string(maximum_node_residual),
        "max_stage3_physical_violation": maximum_physical_residual,
        "temporal_omega_min": None if temporal_bounds is None else temporal_bounds.omega_min,
        "temporal_omega_max": None if temporal_bounds is None else temporal_bounds.omega_max,
        "temporal_variation_reduction_fraction_invariant": (
            None if temporal_bounds is None else temporal_bounds.reduction_fraction
        ),
        "temporal_stage2_variation_solver_vertex": temporal_solution.stage2.temporal_variation,
        "temporal_stage3_variation": temporal_solution.stage3.temporal_variation,
        "temporal_leximin_variation": temporal_leximin.temporal_variation,
        "verification_status": "PASS",
        "manifest": "results/manifests/run_manifest.json",
        "figure_warnings": figure_warnings,
    }
    summary_path = output_root / "RESULTS_SUMMARY.json"
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    manifest = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "project": "AppliedMath deterministic lexicographic tree-flow article",
        "model_boundary": (
            "deterministic rooted trees; no stochastic, scenario, or robust optimization"
        ),
        "command": "python run_analysis.py",
        "python": sys.version,
        "platform": platform.platform(),
        "dependencies": {
            "matplotlib": matplotlib.__version__,
            "networkx": nx.__version__,
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "scipy": scipy.__version__,
        },
        "acceptance_gates": {
            "closed_form_lp_tolerance": 5e-7,
            "closed_form_lp_max_difference": closed_form_max_difference,
            "exact_operator_balance_difference": "0",
            "exact_node_residual": _fraction_string(maximum_node_residual),
            "max_stage3_physical_violation": maximum_physical_residual,
            "stage3_preserves_stage2_within_numerical_tolerance": True,
            "stage3_temporal_variation_not_greater_than_stage2": True,
            "overall_status": "PASS",
        },
        "benchmark_hashes": {
            path.name: _hash_file(path) for path in sorted(data_dir.glob("*.json"))
        },
        "result_files": {},
    }
    for path in sorted(output_root.rglob("*")):
        if path.is_file() and "manifests" not in path.parts:
            manifest["result_files"][str(path.relative_to(project_root))] = _hash_file(
                path
            )
    manifest_path = manifest_dir / "run_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return summary


def generate_single_benchmark_results(
    benchmark_path: str | Path, output_root: str | Path
) -> dict[str, object]:
    """Generate and save the full figure/table/figure_data package for ONE
    benchmark file, into ``output_root/<benchmark_name>/``.

    Unlike :func:`generate_results`, ``benchmark_path`` does not need to live
    under Data/benchmarks/ and no other benchmark's output is touched. This
    backs the desktop app's "Натижани сақлаш" (Save Result) action, which
    saves whichever file the user has open, wherever it lives on disk.
    """
    model = load_benchmark(Path(benchmark_path))
    output_root = Path(output_root)
    benchmark_root = output_root / model.name

    closed = solve_stage1_closed_form(model)
    lp = solve_stage1_lp(model)
    solution = solve_three_stage(model)
    canonical = {record: closed.lambda_star for record in model.active_records}
    operator_check = verify_operator_exact(model, canonical)
    a_coeff, b_coeff = build_operator_exact(model)
    physical_violation = maximum_physical_violation(
        model, solution.stage3.ratios, a_coeff, b_coeff
    )

    tolerance = 5e-7
    lambda_star = float(closed.lambda_star)
    checks = {
        "closed_form_lp_agreement": abs(lp.lambda_star - lambda_star) <= tolerance,
        "operator_balance_exact": operator_check.maximum_absolute_difference == 0,
        "node_balance_exact": operator_check.maximum_node_residual == 0,
        "stage3_physical_violation": physical_violation <= tolerance,
        "stage3_fairness_preserved": solution.stage3.minimum_ratio + tolerance >= lambda_star,
        "stage3_satisfaction_preserved": (
            solution.stage3.weighted_satisfaction + tolerance
            >= solution.stage2.weighted_satisfaction
        ),
        "stage3_variation_not_increased": (
            solution.stage3.temporal_variation
            <= solution.stage2.temporal_variation + tolerance
        ),
    }
    overall_status = "PASS" if all(checks.values()) else "FAIL"

    tables_dir = benchmark_root / "tables"
    write_table(
        pd.DataFrame([{"check": name, "passed": passed} for name, passed in checks.items()]),
        tables_dir,
        "verification",
    )
    write_table(
        pd.DataFrame(
            [
                {
                    "stage": stage.name,
                    "minimum_service_ratio": stage.minimum_ratio,
                    "weighted_satisfaction": stage.weighted_satisfaction,
                    "temporal_variation": stage.temporal_variation,
                    "solver_status": stage.status,
                }
                for stage in (solution.stage1, solution.stage2, solution.stage3)
            ]
        ),
        tables_dir,
        "stages",
    )
    write_table(
        pd.DataFrame(
            [
                {
                    "period": period,
                    "user": user,
                    "demand": _fraction_string(model.demand[period][user]),
                    "stage1_ratio": solution.stage1.ratios[(period, user)],
                    "stage2_ratio": solution.stage2.ratios[(period, user)],
                    "stage3_ratio": solution.stage3.ratios[(period, user)],
                }
                for period, user in model.active_records
            ]
        ),
        tables_dir,
        "allocation_ratios",
    )

    configure_matplotlib()
    plot_benchmark_tree(model, benchmark_root)
    plot_lexicographic_profiles(model, solution, benchmark_root)
    plot_lexicographic_profiles_per_user(model, solution, benchmark_root)
    plot_matrix_patterns(model, benchmark_root)
    agreement_data = compute_operator_agreement_rows([(model, solution)])
    plot_operator_agreement_scatter(agreement_data, benchmark_root, title=model.name)

    summary = {
        "benchmark": model.name,
        "source_file": str(Path(benchmark_path).resolve()),
        "output_folder": str(benchmark_root.resolve()),
        "nodes": len(model.nodes),
        "edges": len(model.edges),
        "users": len(model.users),
        "periods": len(model.periods),
        "lambda_closed_form_exact": _fraction_string(closed.lambda_star),
        "lambda_closed_form": lambda_star,
        "lambda_lp": lp.lambda_star,
        "verification_status": overall_status,
    }
    (benchmark_root / "RESULT_SUMMARY.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return summary
