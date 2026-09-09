"""Publication assets for the inverse design problem (conference paper).

Everything produced here lands under ``results/investment/`` and is kept
entirely separate from the journal-article pipeline in :mod:`reporting`:

* the article's ``generate_results`` preserves ``results/investment`` when it
  clears the output tree, and excludes it from the article run manifest;
* this module writes its own ``run_manifest.json`` and summary, so each paper
  carries its own provenance record.

Outputs
-------

``tables/{csv,excel}/``
    ``table_1_investment_plans`` -- widening, lining and mixed plans;
    ``table_2_critical_resources`` -- the design structure of every instance.
``figure_data/{csv,excel}/``
    one source table per figure.
``figures/``
    three 600 dpi PNG figures sized for a single-column AIP page.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .domain import Benchmark
from .examples import load_all_benchmarks
from .figures import configure_matplotlib
from .investment import (
    apply_lining,
    budget_function,
    critical_resources,
    epsilon_bottleneck_set,
    expansion_plan,
    lambda_star,
    lining_plan,
    mixed_plan,
    resource_table,
)
from .io import load_benchmark
from .tables import write_table

__all__ = ["generate_investment_results"]

_SOFTWARE_LABEL = "AppliedMath LexFlow 0.4.1"

# AIP Conference Proceedings: US Letter with 1 in margins, single column.
AIP_WIDE = (6.5, 3.5)
AIP_NARROW = (6.5, 2.6)
# A single-column conference page cannot spare 6.5 in of width for one figure,
# and shrinking a 6.5 in drawing on the page would leave 4 pt tick labels. The
# compact variant is drawn at the size it is printed at, so its type stays at
# the size it was set.
AIP_COMPACT = (3.6, 2.7)
# The paper prints the panels side by side instead: at 6.4 in the drawing uses
# the whole text column, and at 2 in it is short enough to leave room on the
# page for the table that follows, which AIP asks not to be split.
AIP_SIDE_BY_SIDE = (6.4, 1.95)

# Lining targets studied throughout the paper.
LINING_TARGETS = (Fraction(9, 10), Fraction(23, 25), Fraction(19, 20))
WIDENING_TARGETS = (Fraction(9, 10), Fraction(19, 20), Fraction(1))
REFERENCE = "gone_abat_jap"
NEAR_TIE_EPSILON = Fraction(1, 10**9)


def _save(fig: plt.Figure, stem: str, output_root: Path) -> None:
    target = output_root / "figures" / f"{stem}.png"
    target.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(
        target,
        bbox_inches="tight",
        dpi=600,
        metadata={"Software": _SOFTWARE_LABEL},
    )
    plt.close(fig)


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _fraction_string(value: Fraction) -> str:
    return (
        str(value.numerator)
        if value.denominator == 1
        else f"{value.numerator}/{value.denominator}"
    )


def _season_source_capacity(model: Benchmark) -> Fraction:
    return sum(
        (model.source_capacity[period] for period in model.periods), Fraction(0)
    )


# --------------------------------------------------------------------------
# Tables
# --------------------------------------------------------------------------


def build_plan_rows(models: list[Benchmark]) -> list[dict[str, object]]:
    """Widening, lining and mixed plans for every instance and target."""
    rows: list[dict[str, object]] = []
    for model in models:
        resources = resource_table(model)
        base = lambda_star(resources)
        reference = _season_source_capacity(model)

        for target in WIDENING_TARGETS:
            plan = expansion_plan(model, target, resources=resources)
            rows.append(
                {
                    "benchmark": model.name,
                    "strategy": "widening",
                    "lining_target_eta": "",
                    "target_guarantee": float(target),
                    "lambda_star_before": float(base),
                    "lambda_star_after_lining": "",
                    "upgraded_resources": len(plan.funded),
                    "total_resources": len(resources),
                    "added_capacity": float(plan.cost),
                    "added_capacity_exact": _fraction_string(plan.cost),
                    "share_of_season_source_capacity": (
                        float(plan.cost / reference) if reference > 0 else 0.0
                    ),
                    "saving_vs_widening_only": 0.0,
                }
            )

        widening_only = expansion_plan(model, Fraction(1), resources=resources).cost
        for eta_bar in LINING_TARGETS:
            plan = mixed_plan(model, Fraction(1), eta_bar)
            rows.append(
                {
                    "benchmark": model.name,
                    "strategy": "lining_then_widening",
                    "lining_target_eta": float(eta_bar),
                    "target_guarantee": 1.0,
                    "lambda_star_before": float(base),
                    "lambda_star_after_lining": float(plan.lambda_after_lining),
                    "upgraded_resources": len(plan.expansion.funded),
                    "total_resources": len(resources),
                    "added_capacity": float(plan.expansion.cost),
                    "added_capacity_exact": _fraction_string(plan.expansion.cost),
                    "share_of_season_source_capacity": (
                        float(plan.expansion.cost / reference) if reference > 0 else 0.0
                    ),
                    "saving_vs_widening_only": (
                        float(1 - plan.expansion.cost / widening_only)
                        if widening_only > 0
                        else 0.0
                    ),
                }
            )
    return rows


def build_structure_rows(models: list[Benchmark]) -> list[dict[str, object]]:
    """Design structure: resource count, critical set, tie width, curve shape."""
    rows: list[dict[str, object]] = []
    for model in models:
        resources = resource_table(model)
        base = lambda_star(resources)
        critical = critical_resources(model, resources)
        curve = budget_function(model, resources=resources)
        rows.append(
            {
                "benchmark": model.name,
                "nodes": len(model.nodes),
                "edges": len(model.edges),
                "periods": len(model.periods),
                "resources_m": len(resources),
                "critical_resources": len(critical),
                "critical_share": len(critical) / len(resources),
                "lambda_star": float(base),
                "lambda_star_exact": _fraction_string(base),
                "exact_bottleneck_set": len(
                    epsilon_bottleneck_set(model, Fraction(0), resources)
                ),
                "near_tied_bottleneck_set_1e_9": len(
                    epsilon_bottleneck_set(model, NEAR_TIE_EPSILON, resources)
                ),
                "budget_curve_segments": len(curve.segments),
                "full_service_cost": float(curve.cost(Fraction(1))),
            }
        )
    return rows


# --------------------------------------------------------------------------
# Figure 1: the greedy-lining counterexample
# --------------------------------------------------------------------------


def build_trap_rows(model: Benchmark) -> list[dict[str, object]]:
    base = lambda_star(resource_table(model))
    rows = [
        {
            "lining_decision": "none",
            "lined_edges": "",
            "lambda_star": float(base),
            "lambda_star_exact": _fraction_string(base),
            "gain": 0.0,
        }
    ]
    for edge_id in model.edge_ids:
        value = lambda_star(resource_table(apply_lining(model, {edge_id}, Fraction(1))))
        rows.append(
            {
                "lining_decision": "single edge",
                "lined_edges": edge_id,
                "lambda_star": float(value),
                "lambda_star_exact": _fraction_string(value),
                "gain": float(value - base),
            }
        )
    plan = lining_plan(model, Fraction(1), Fraction(1))
    rows.append(
        {
            "lining_decision": "joint (Algorithm 2)",
            "lined_edges": "+".join(plan.lined),
            "lambda_star": float(plan.lambda_after),
            "lambda_star_exact": _fraction_string(plan.lambda_after),
            "gain": float(plan.lambda_after - base),
        }
    )
    return rows


def plot_trap(rows: list[dict[str, object]], output_root: Path) -> None:
    labels = [
        ("none" if row["lining_decision"] == "none" else str(row["lined_edges"]))
        for row in rows
    ]
    values = [float(row["lambda_star"]) for row in rows]
    joint = [row["lining_decision"] == "joint (Algorithm 2)" for row in rows]

    fig, ax = plt.subplots(figsize=AIP_NARROW)
    colors = ["#0d5b57" if flag else "#9aa8a5" for flag in joint]
    bars = ax.bar(range(len(values)), values, color=colors, width=0.62)
    ax.axhline(values[0], color="#a03f28", linestyle="--", linewidth=1.0)
    ax.text(
        -0.42,
        values[0] + 0.20,
        "no single edge moves the guarantee",
        ha="left",
        va="bottom",
        color="#a03f28",
        fontsize=7.5,
    )
    for rect, value in zip(bars, values):
        ax.text(
            rect.get_x() + rect.get_width() / 2,
            value + 0.015,
            f"{value:.2f}",
            ha="center",
            va="bottom",
            fontsize=7.5,
        )
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels)
    ax.set_ylim(0, 1.15)
    ax.set_ylabel(r"Stage-1 guarantee $\lambda^{*}$")
    ax.set_xlabel("lined edges")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    _save(fig, "figure_1_greedy_lining_trap", output_root)


# --------------------------------------------------------------------------
# Figure 2: guarantee-budget curves
# --------------------------------------------------------------------------


BASELINE_SCENARIO = "widening only"


def build_curve_rows(model: Benchmark) -> list[dict[str, object]]:
    """One row per linear piece of ``B(tau)``, for each rehabilitation scenario."""
    rows: list[dict[str, object]] = []
    scenarios: list[tuple[str, Benchmark]] = [(BASELINE_SCENARIO, model)]
    for eta_bar in (Fraction(9, 10), Fraction(23, 25)):
        scenarios.append(
            (
                f"lined to eta>={float(eta_bar):.2f}",
                apply_lining(model, model.edge_ids, eta_bar),
            )
        )
    for name, variant in scenarios:
        curve = budget_function(variant)
        for segment in curve.segments:
            rows.append(
                {
                    "scenario": name,
                    "tau_low": float(segment.tau_low),
                    "tau_high": float(segment.tau_high),
                    "budget_at_tau_low": float(curve.cost(segment.tau_low)),
                    "budget_at_tau_high": float(curve.cost(segment.tau_high)),
                    "marginal_cost": float(segment.slope),
                    "funded_resources": segment.funded_count,
                }
            )
    return rows


def plot_budget_curves(
    rows: list[dict[str, object]],
    output_root: Path,
    *,
    compact: bool = False,
    wide: bool = False,
) -> None:
    """Panel (a): the convex curves. Panel (b): the nondecreasing marginal cost.

    ``compact`` draws the same figure at single-column conference width with
    type scaled for that size; ``wide`` instead places the two panels side by
    side across the full text column, which is the variant the conference paper
    prints. Each is saved under its own file name.
    """
    frame = pd.DataFrame(rows)
    styles = {
        BASELINE_SCENARIO: ("#a03f28", "-", 1.6),
        "lined to eta>=0.90": ("#0d5b57", "--", 1.4),
        "lined to eta>=0.92": ("#3f8f86", ":", 1.4),
    }
    if wide:
        size, small = AIP_SIDE_BY_SIDE, 6.5
        fig, (top, bottom) = plt.subplots(1, 2, figsize=size, width_ratios=[1.15, 1.0])
    else:
        size = AIP_COMPACT if compact else (6.5, 4.8)
        small = 6.0 if compact else 8.0
        fig, (top, bottom) = plt.subplots(
            2, 1, figsize=size, sharex=True, height_ratios=[2.0, 1.0]
        )
    for axis in (top, bottom):
        axis.tick_params(labelsize=small)

    for name, (color, style, width) in styles.items():
        part = frame[frame["scenario"] == name]
        if part.empty:
            continue
        taus = [*part["tau_low"], part["tau_high"].iloc[-1]]
        costs = [*part["budget_at_tau_low"], part["budget_at_tau_high"].iloc[-1]]
        top.plot(
            taus,
            [value / 1e6 for value in costs],
            color=color,
            linestyle=style,
            linewidth=width,
            label=name.replace("eta>=", r"$\eta \geq$ "),
        )
        top.plot(taus[-1], costs[-1] / 1e6, "o", color=color, markersize=3.5)
        top.annotate(
            f"{costs[-1] / 1e6:.3f}",
            (taus[-1], costs[-1] / 1e6),
            textcoords="offset points",
            xytext=(-5, 4),
            ha="right",
            fontsize=small - 0.5,
            color=color,
        )
    if wide:  # side by side, so panel (a) carries its own x axis
        top.set_xlabel(r"target service guarantee $\tau$", fontsize=small)
    top.set_ylabel(r"added capacity  ($10^{6}$ m$^{3}$)", fontsize=small)
    top.legend(frameon=False, loc="upper left", fontsize=small - 0.5,
               handlelength=1.6, borderpad=0.2, labelspacing=0.25)
    top.grid(True, linewidth=0.4, alpha=0.35)
    top.set_axisbelow(True)
    top.spines[["top", "right"]].set_visible(False)
    top.set_title("(a) guarantee–capacity curve", fontsize=small + 0.5, loc="left")

    base = frame[frame["scenario"] == BASELINE_SCENARIO].sort_values("tau_low")
    color = styles[BASELINE_SCENARIO][0]
    span = float(base["tau_high"].max() - base["tau_low"].min())
    # Near-tied resources produce many kinks within a few 1e-10 of one another.
    # They are genuine pieces of B, but at page scale they are one vertical
    # smear, so the step plot draws only the pieces that are actually wide
    # enough to see; the full segment list stays in the figure-source table.
    visible = base[base["tau_high"] - base["tau_low"] > span / 1000]
    previous_level: float | None = None
    for piece in visible.itertuples():
        level = piece.marginal_cost / 1e6
        bottom.plot(
            [piece.tau_low, piece.tau_high],
            [level, level],
            color=color,
            linewidth=1.6,
            solid_capstyle="butt",
        )
        if previous_level is not None:
            bottom.plot(
                [piece.tau_low] * 2,
                [previous_level, level],
                color=color,
                linewidth=0.9,
            )
        previous_level = level
    levels = [piece.marginal_cost / 1e6 for piece in visible.itertuples()]
    if levels:
        low, high = min(levels), max(levels)
        margin = max((high - low) * 0.6, high * 0.01)
        bottom.set_ylim(low - margin, high + margin)
    bottom.set_xlabel(r"target service guarantee $\tau$", fontsize=small)
    bottom.set_ylabel(r"$B'(\tau)$  ($10^{6}$ m$^{3}$)", fontsize=small)
    bottom.grid(True, linewidth=0.4, alpha=0.35)
    bottom.set_axisbelow(True)
    bottom.spines[["top", "right"]].set_visible(False)
    bottom.set_title(
        "(b) marginal capacity requirement, widening only",
        fontsize=small + 0.5,
        loc="left",
    )
    fig.tight_layout(pad=0.4, w_pad=1.4 if wide else None)
    stem = "figure_2_guarantee_budget_curves"
    suffix = "_wide" if wide else "_compact" if compact else ""
    _save(fig, stem + suffix, output_root)


# --------------------------------------------------------------------------
# Figure 3: headroom map over periods and resources
# --------------------------------------------------------------------------


def build_headroom_rows(model: Benchmark) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for item in resource_table(model):
        rows.append(
            {
                "period": item.period,
                "resource": "source" if item.kind == "source" else item.edge_id,
                "kind": item.kind,
                "capacity": float(item.capacity),
                "full_demand_load": float(item.load),
                "headroom_xi": float(item.headroom),
                "critical": bool(item.capacity < item.load),
            }
        )
    return rows


def plot_headroom_map(
    model: Benchmark, rows: list[dict[str, object]], output_root: Path
) -> None:
    frame = pd.DataFrame(rows)
    periods = list(model.periods)
    resources = ["source", *model.edge_ids]
    grid = np.full((len(resources), len(periods)), np.nan)
    row_index = {name: i for i, name in enumerate(resources)}
    col_index = {name: i for i, name in enumerate(periods)}
    for record in rows:
        grid[row_index[record["resource"]], col_index[record["period"]]] = record[
            "headroom_xi"
        ]

    fig, ax = plt.subplots(figsize=(6.5, 4.6))
    palette = plt.get_cmap("BrBG").copy()
    # Zero-load cells impose no bound at all; give them their own flat grey so
    # they are not mistaken for the near-white middle of the colour scale.
    palette.set_bad("#aab4b1")
    image = ax.imshow(
        np.clip(grid, 0.8, 1.6),
        aspect="auto",
        cmap=palette,
        vmin=0.8,
        vmax=1.6,
        interpolation="nearest",
    )
    critical = frame[frame["critical"]]
    ax.scatter(
        [col_index[p] for p in critical["period"]],
        [row_index[r] for r in critical["resource"]],
        s=14,
        facecolors="none",
        edgecolors="#a03f28",
        linewidths=0.9,
    )
    ax.set_xticks(range(len(periods)))
    ax.set_xticklabels(periods, fontsize=6.5)
    ax.set_yticks(range(len(resources)))
    ax.set_yticklabels(resources, fontsize=5.2)
    ax.set_xlabel("ten-day period")
    ax.set_ylabel("resource")
    bar = fig.colorbar(image, ax=ax, fraction=0.035, pad=0.02, extend="both")
    bar.set_label(r"headroom $\xi_j = c_j / L_j$", fontsize=8)
    bar.ax.tick_params(labelsize=7)
    ax.set_title(
        f"{len(critical)} of {len(rows)} resources can ever bind "
        r"(circled: $\xi_j < 1$; grey: no load)",
        fontsize=8.5,
    )
    fig.tight_layout()
    _save(fig, "figure_3_headroom_map", output_root)


# --------------------------------------------------------------------------
# Orchestrator
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class InvestmentAssets:
    output_root: Path
    summary: dict[str, object]


def generate_investment_results(project_root: str | Path) -> dict[str, object]:
    """Build every table and figure for the inverse-design conference paper."""
    project_root = Path(project_root).resolve()
    data_dir = project_root / "Data" / "benchmarks"
    design_path = project_root / "Data" / "design" / "greedy_lining_trap.json"
    output_root = project_root / "results" / "investment"
    for relative in ("tables", "figure_data", "figures"):
        (output_root / relative).mkdir(parents=True, exist_ok=True)

    models = load_all_benchmarks(data_dir)
    reference_model = next(model for model in models if model.name == REFERENCE)
    trap_model = load_benchmark(design_path)

    plan_rows = build_plan_rows(models)
    structure_rows = build_structure_rows(models)
    write_table(pd.DataFrame(plan_rows), output_root / "tables", "table_1_investment_plans")
    write_table(
        pd.DataFrame(structure_rows), output_root / "tables", "table_2_critical_resources"
    )

    trap_rows = build_trap_rows(trap_model)
    curve_rows = build_curve_rows(reference_model)
    headroom_rows = build_headroom_rows(reference_model)
    figure_data = output_root / "figure_data"
    write_table(pd.DataFrame(trap_rows), figure_data, "figure_1_greedy_lining_trap")
    write_table(pd.DataFrame(curve_rows), figure_data, "figure_2_guarantee_budget_curves")
    write_table(pd.DataFrame(headroom_rows), figure_data, "figure_3_headroom_map")

    configure_matplotlib()
    plot_trap(trap_rows, output_root)
    plot_budget_curves(curve_rows, output_root)
    plot_budget_curves(curve_rows, output_root, compact=True)
    plot_budget_curves(curve_rows, output_root, wide=True)
    plot_headroom_map(reference_model, headroom_rows, output_root)

    reference_resources = resource_table(reference_model)
    reference_curve = budget_function(reference_model, resources=reference_resources)
    trap_plan = lining_plan(trap_model, Fraction(1), Fraction(1))
    summary: dict[str, object] = {
        "paper": "Bottleneck-targeted rehabilitation planning (conference paper)",
        "reference_instance": REFERENCE,
        "resources_m": len(reference_resources),
        "critical_resources": len(critical_resources(reference_model, reference_resources)),
        "lambda_star": float(lambda_star(reference_resources)),
        "exact_bottleneck_set": len(
            epsilon_bottleneck_set(reference_model, Fraction(0), reference_resources)
        ),
        "near_tied_bottleneck_set_1e_9": len(
            epsilon_bottleneck_set(reference_model, NEAR_TIE_EPSILON, reference_resources)
        ),
        "widening_only_full_service_cost": float(reference_curve.cost(Fraction(1))),
        "mixed_plan_savings": {
            f"{float(eta):.2f}": float(
                mixed_plan(reference_model, Fraction(1), eta).saving_fraction
            )
            for eta in LINING_TARGETS
        },
        "counterexample": {
            "instance": trap_model.name,
            "lambda_star_before": _fraction_string(trap_plan.lambda_before),
            "lambda_star_after_joint_step": _fraction_string(trap_plan.lambda_after),
            "single_edge_gain": 0.0,
            "lined_edges": list(trap_plan.lined),
            "transversal_is_exact": trap_plan.exact_transversals,
        },
        "tables": 2,
        "figures": 4,
    }
    (output_root / "INVESTMENT_SUMMARY.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    manifest = {
        "paper": summary["paper"],
        "command": "python run_investment.py",
        "inputs": {
            path.name: _hash_file(path)
            for path in [*sorted(data_dir.glob("*.json")), design_path]
        },
        "outputs": {
            str(path.relative_to(project_root)): _hash_file(path)
            for path in sorted(output_root.rglob("*"))
            if path.is_file() and path.name != "run_manifest.json"
        },
    }
    (output_root / "run_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return summary
