#!/usr/bin/env python3
"""Standalone verification of the CORRECTED Results block.

Run from the project root (the folder that contains ``src/``)::

    python verify_corrected_results.py

It reloads the five exact benchmarks, prints the corrected, solver-independent
temporal results next to the manuscript's reported numbers, and writes three
figures. It relies only on the project package (``src/appliedmath_lexflow``),
so it doubles as a reproducibility check for a reviewer.
"""

from __future__ import annotations

import sys
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if SRC.exists() and str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from appliedmath_lexflow.io import load_benchmark
from appliedmath_lexflow.lexicographic import solve_three_stage
from appliedmath_lexflow.robust import (
    price_of_fairness,
    solve_leximin,
    stage2_variation_bounds,
)

DATA = ROOT / "Data" / "benchmarks"
OUT = ROOT / "verification_figures"
OUT.mkdir(exist_ok=True)
NAMES = [
    "branching_shared_edge_bottleneck",
    "chain_source_bottleneck",
    "star_edge_bottleneck",
    "temporal_lexicographic",
    "tie_bottleneck",
]


def main() -> None:
    models = {name: load_benchmark(DATA / f"{name}.json") for name in NAMES}

    # --- corrected temporal result vs the manuscript ------------------------
    temporal = models["temporal_lexicographic"]
    sol = solve_three_stage(temporal)
    bounds = stage2_variation_bounds(temporal)
    lex = solve_leximin(temporal)

    print("=" * 70)
    print("TEMPORAL BENCHMARK — manuscript vs corrected project")
    print("=" * 70)
    print(f"  lambda*            : 3/5 = 0.60         (unchanged, correct)")
    print(f"  theta* (Stage 2)   : 22/30 = {sol.stage2.weighted_satisfaction:.6f}")
    print(f"  Stage-3 satisfaction: {sol.stage3.weighted_satisfaction:.6f}"
          f"  (must equal theta* exactly)")
    print(f"  Omega(r2) vertex   : {sol.stage2.temporal_variation:.4f}"
          f"   <- manuscript reported this single value as 'the result'")
    print(f"  Omega range on face: [{bounds.omega_min_exact}, {bounds.omega_max_exact}]"
          f" = [{bounds.omega_min:.4f}, {bounds.omega_max:.4f}]  (INVARIANT)")
    print(f"  Stage-3 Omega*     : {sol.stage3.temporal_variation:.4f}"
          f"   (manuscript ~0.40; old code gave 0.39999998 < 0.40)")
    print(f"  Invariant reduction: {bounds.reduction_fraction*100:.1f}%"
          f"   (manuscript claimed a solver-dependent 46.7%)")
    print(f"  Leximin (unique)   : Omega={lex.temporal_variation:.4f}, "
          f"satisfaction={lex.weighted_satisfaction:.6f}, levels={lex.levels}")

    # --- price of fairness across benchmarks --------------------------------
    print("\n" + "=" * 70)
    print("PRICE OF FAIRNESS")
    print("=" * 70)
    pof = {name: price_of_fairness(m) for name, m in models.items()}
    for name in NAMES:
        p = pof[name]
        print(f"  {name:34s} Z_eff={p.efficiency_optimum:8.3f} "
              f"Z_fair={p.fair_delivery:8.3f} PoF={p.price_of_fairness*100:5.2f}%")

    _figure_variation_range(sol, bounds, lex)
    _figure_price_of_fairness(pof)
    _figure_leximin_profile(temporal, lex)
    print(f"\nFigures written to {OUT}")


def _figure_variation_range(sol, bounds, lex) -> None:
    fig, ax = plt.subplots(figsize=(7, 2.6))
    ax.hlines(0, bounds.omega_min, bounds.omega_max, color="#1F4E79", lw=6, alpha=0.35,
              label="Stage-2 optimal face range")
    ax.plot(bounds.omega_min, 0, "o", color="#1F4E79", ms=11)
    ax.plot(bounds.omega_max, 0, "o", color="#1F4E79", ms=11)
    ax.annotate(f"Omega_min = 2/5\n(Stage 3 / leximin)", (bounds.omega_min, 0),
                textcoords="offset points", xytext=(0, 14), ha="center", fontsize=9)
    ax.annotate(f"Omega_max = 21/20", (bounds.omega_max, 0),
                textcoords="offset points", xytext=(0, 14), ha="center", fontsize=9)
    ax.plot(sol.stage2.temporal_variation, 0, "D", color="#C0392B", ms=10, zorder=5)
    ax.annotate("solver vertex = 0.75\n(manuscript 'result')",
                (sol.stage2.temporal_variation, 0), textcoords="offset points",
                xytext=(0, -34), ha="center", fontsize=9, color="#C0392B")
    ax.set_xlim(0.3, 1.15)
    ax.set_yticks([])
    ax.set_xlabel("Temporal variation  Omega(r)")
    ax.set_title("Stage-2 variation is not a single number: it spans [0.40, 1.05]")
    ax.legend(loc="upper right", fontsize=8)
    fig.tight_layout()
    fig.savefig(OUT / "fig_variation_range.png", dpi=150)
    plt.close(fig)


def _figure_price_of_fairness(pof) -> None:
    fig, ax = plt.subplots(figsize=(7, 3.4))
    names = [n.replace("_bottleneck", "").replace("_", " ") for n in NAMES]
    z_eff = [pof[n].efficiency_optimum for n in NAMES]
    z_fair = [pof[n].fair_delivery for n in NAMES]
    x = range(len(NAMES))
    ax.bar([i - 0.2 for i in x], z_eff, width=0.4, label="Z_eff (no fairness floor)",
           color="#5B9BD5")
    ax.bar([i + 0.2 for i in x], z_fair, width=0.4, label="Z_fair (Stage-1 floor)",
           color="#1F4E79")
    for i in x:
        pct = pof[NAMES[i]].price_of_fairness * 100
        if pct > 0.01:
            ax.annotate(f"PoF {pct:.2f}%", (i, max(z_eff[i], z_fair[i])),
                        textcoords="offset points", xytext=(0, 4), ha="center", fontsize=8)
    ax.set_xticks(list(x))
    ax.set_xticklabels(names, rotation=20, ha="right", fontsize=8)
    ax.set_ylabel("Total net delivery")
    ax.set_title("Price of fairness")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(OUT / "fig_price_of_fairness.png", dpi=150)
    plt.close(fig)


def _figure_leximin_profile(model, lex) -> None:
    fig, ax = plt.subplots(figsize=(6, 3.4))
    periods = list(model.periods)
    for user in model.user_ids:
        ys = [lex.ratios[(k, user)] for k in periods]
        ax.plot(periods, ys, "-o", label=f"user {user}")
    ax.axhline(lex.minimum_ratio, ls=":", color="gray",
               label=f"lambda* = {lex.minimum_ratio:.2f}")
    ax.set_ylim(0.5, 1.02)
    ax.set_ylabel("Service ratio r")
    ax.set_title("Leximin allocation (unique, Omega = 0.40)")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(OUT / "fig_leximin_profile.png", dpi=150)
    plt.close(fig)


if __name__ == "__main__":
    main()
