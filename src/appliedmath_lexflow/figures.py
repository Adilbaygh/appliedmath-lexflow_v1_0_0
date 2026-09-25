from __future__ import annotations

from collections.abc import Iterable
from fractions import Fraction
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle

from .domain import Benchmark
from .figure_style import (
    GUARANTEE_COLOR,
    NEGATIVE_COLOR,
    POSITIVE_COLOR,
    draw_tree,
    draw_user_profile,
    is_small_network,
    math_label,
    tree_layout,
    user_colors,
)
from .lexicographic import ThreeStageSolution
from .operators import (
    build_balance_matrices,
    build_graph,
    flows_from_node_balance_exact,
    flows_from_operator_exact,
    matrix_operator,
)
from .tables import write_table

SINGLE_COLUMN = (3.5, 2.6)
DOUBLE_COLUMN = (7.2, 4.3)
_SOFTWARE_LABEL = "AppliedMath LexFlow 0.5.2"

# The colour code itself lives in figure_style.py, which the desktop GUI shares,
# so an interactively displayed plot matches the published figure exactly.
_POSITIVE_COLOR = POSITIVE_COLOR
_NEGATIVE_COLOR = NEGATIVE_COLOR
_math_label = math_label


def configure_matplotlib() -> None:
    """Configure journal-sized, reproducible publication graphics."""
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 8.5,
            "axes.labelsize": 8.5,
            "axes.titlesize": 9.0,
            "legend.fontsize": 8.0,
            "xtick.labelsize": 8.0,
            "ytick.labelsize": 8.0,
            "lines.linewidth": 1.3,
            "figure.dpi": 150,
            "savefig.dpi": 600,
        }
    )


def _save(fig: plt.Figure, stem: str, output_root: Path) -> None:
    """Save one figure as a deterministic 600 dpi PNG.

    ``stem`` may include subfolders (e.g. ``"profiles_by_user/f1"``); the
    full parent directory is created as needed.
    """
    target_path = output_root / "figures" / f"{stem}.png"
    target_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(
        target_path,
        bbox_inches="tight",
        dpi=600,
        metadata={"Software": _SOFTWARE_LABEL},
    )
    plt.close(fig)


def plot_benchmark_tree(model: Benchmark, output_root: Path) -> None:
    """Render the rooted canal tree for one benchmark into its own output folder."""
    graph = build_graph(model)
    positions, levels = tree_layout(model, graph)

    node_rows = [
        {
            "node": node,
            "x": positions[node][0],
            "y": positions[node][1],
            "topological_level": levels[node],
            "is_source": node == model.source,
        }
        for node in model.nodes
    ]
    edge_rows = [
        {"edge": edge.edge_id, "tail": edge.tail, "head": edge.head}
        for edge in model.edges
    ]
    figure_data_dir = output_root / "figure_data"
    write_table(pd.DataFrame(node_rows), figure_data_dir, "figure_1_tree_nodes")
    write_table(pd.DataFrame(edge_rows), figure_data_dir, "figure_1_tree_edges")

    # Small benchmarks keep the journal double-column size. A large network is
    # drawn at the full text width instead of on an oversized canvas, so that the
    # figure is placed on the page at its native scale and the node and reach
    # labels reach the reader at the size they were drawn.
    small = is_small_network(model)
    figsize = DOUBLE_COLUMN if small else (7.2, 4.1)
    fig, ax = plt.subplots(figsize=figsize)
    draw_tree(model, graph, positions, ax, small=small)
    _save(fig, "figure_1_tree", output_root)


def plot_capacity_fairness(output_root: Path) -> None:
    capacity = np.linspace(0.0, 130.0, 261)
    source_ratio = capacity / 100.0
    fixed_edge_ratio = np.full_like(capacity, 0.75)
    lambda_values = np.minimum(1.0, np.minimum(source_ratio, fixed_edge_ratio))
    data = pd.DataFrame(
        {
            "varied_capacity": capacity,
            "source_ratio": source_ratio,
            "fixed_edge_ratio": fixed_edge_ratio,
            "lambda_star": lambda_values,
        }
    )
    write_table(data, output_root / "figure_data", "figure_2_capacity_fairness")

    fig, ax = plt.subplots(figsize=SINGLE_COLUMN)
    ax.plot(capacity, lambda_values, label=r"$\lambda^*$")
    ax.axvline(75.0, linestyle="--", linewidth=1.0, label="bottleneck switch")
    ax.set_xlabel("Varied resource capacity")
    ax.set_ylabel("Optimal fairness guarantee")
    ax.set_ylim(-0.02, 1.02)
    ax.legend(frameon=False)
    ax.grid(True, linewidth=0.4, alpha=0.5)
    _save(fig, "figure_2_capacity_fairness", output_root)


def plot_bottleneck_regions(output_root: Path) -> None:
    x = np.linspace(0.0, 1.25, 251)
    y = np.linspace(0.0, 1.25, 251)
    xx, yy = np.meshgrid(x, y)
    values = np.minimum(1.0, np.minimum(xx, yy))
    active = np.where(
        (xx <= yy) & (xx <= 1.0),
        0,
        np.where((yy < xx) & (yy <= 1.0), 1, 2),
    )
    # Store every plotted grid cell, not a sample, so the figure is fully reproducible.
    data = pd.DataFrame(
        {
            "normalized_capacity_1": xx.ravel(),
            "normalized_capacity_2": yy.ravel(),
            "lambda_star": values.ravel(),
            "active_region": active.ravel(),
        }
    )
    write_table(data, output_root / "figure_data", "figure_3_bottleneck_regions")

    fig, ax = plt.subplots(figsize=SINGLE_COLUMN)
    mesh = ax.pcolormesh(xx, yy, active, shading="auto", rasterized=True)
    ax.plot([0, 1.25], [0, 1.25], linestyle="--", linewidth=1.0)
    ax.axvline(1.0, linestyle=":", linewidth=0.9)
    ax.axhline(1.0, linestyle=":", linewidth=0.9)
    ax.set_xlabel(r"Normalized capacity $c_1/L_1$")
    ax.set_ylabel(r"Normalized capacity $c_2/L_2$")
    ax.set_title("Active-bottleneck regions")
    cbar = fig.colorbar(mesh, ax=ax, ticks=[0, 1, 2])
    cbar.ax.set_yticklabels(["resource 1", "resource 2", "full service"])
    _save(fig, "figure_3_bottleneck_regions", output_root)


def compute_operator_agreement_rows(
    benchmark_solutions: Iterable[tuple[Benchmark, ThreeStageSolution]],
) -> pd.DataFrame:
    """Cross-check the closed-form graph operator against direct node-balance flows.

    Returns one row per (benchmark, period, edge) so the result can be plotted
    either pooled across every benchmark or filtered down to a single one.
    """
    rows: list[dict[str, float | str]] = []
    for model, solution in benchmark_solutions:
        # Convert the numerical Stage-3 vector to declared decimal rationals, then
        # evaluate both independent flow formulations in exact arithmetic.
        ratios = {
            record: Fraction(str(round(value, 12)))
            for record, value in solution.stage3.ratios.items()
        }
        operator_flows, _ = flows_from_operator_exact(model, ratios)
        balance_flows, _ = flows_from_node_balance_exact(model, ratios)
        for key in operator_flows:
            rows.append(
                {
                    "benchmark": model.name,
                    "period": key[0],
                    "edge": key[1],
                    "operator_flow": float(operator_flows[key]),
                    "node_balance_flow": float(balance_flows[key]),
                    "exact_difference": str(operator_flows[key] - balance_flows[key]),
                }
            )
    return pd.DataFrame(rows)


def plot_operator_agreement_scatter(
    data: pd.DataFrame,
    output_root: Path,
    *,
    title: str | None = None,
    stem: str = "figure_4_operator_balance_agreement",
) -> None:
    """Render the node-balance-vs-operator-flow scatter for the given rows.

    ``stem`` names both the PNG and its source table, so several pooled
    variants can coexist in one output folder.
    """
    write_table(data, output_root / "figure_data", stem)

    upper = max(
        float(data["operator_flow"].max()),
        float(data["node_balance_flow"].max()),
        1.0,
    )
    fig, ax = plt.subplots(figsize=SINGLE_COLUMN)
    ax.scatter(data["node_balance_flow"], data["operator_flow"], s=13)
    ax.plot([0, upper], [0, upper], linestyle="--", linewidth=1.0, label=r"$y=x$")
    ax.set_xlabel("Node-balance flow")
    ax.set_ylabel("Graph-operator flow")
    if title is not None:
        ax.set_title(title)
    ax.legend(frameon=False)
    ax.grid(True, linewidth=0.4, alpha=0.5)
    _save(fig, stem, output_root)


def plot_lexicographic_profiles(
    model: Benchmark, solution: ThreeStageSolution, output_root: Path
) -> None:
    """Render Stage-2 vs. Stage-3 service-ratio profiles for one benchmark.

    Two layouts are used. Benchmarks with a handful of users are drawn on one
    axis, with Stage 2 dashed and Stage 3 solid; Stage-3 line widths decrease
    from user to user so that profiles which coincide exactly (Stage 3 often
    assigns the *same* vector to several users) all remain visible instead of
    the last one hiding the others. Benchmarks with many users are drawn as two
    panels, Stage 2 and Stage 3 side by side, with one colour legend naming
    every service block.
    """
    rows: list[dict[str, float | str]] = []
    period_index = {period: idx + 1 for idx, period in enumerate(model.periods)}
    guarantee = float(solution.lambda_closed_form)

    active: dict[str, tuple[list[int], list[float], list[float]]] = {}
    for user in model.user_ids:
        # Periods with zero demand for this user are excluded from the
        # optimization records entirely (no ratio is defined), so only plot
        # the periods where the user actually has an active record.
        periods = [
            period for period in model.periods if (period, user) in solution.stage2.ratios
        ]
        if not periods:
            continue
        stage2_values = [solution.stage2.ratios[(period, user)] for period in periods]
        stage3_values = [solution.stage3.ratios[(period, user)] for period in periods]
        active[user] = (
            [period_index[period] for period in periods],
            stage2_values,
            stage3_values,
        )
        for period, s2, s3 in zip(periods, stage2_values, stage3_values):
            rows.append(
                {"period": period, "user": user, "stage2_ratio": s2, "stage3_ratio": s3}
            )
    write_table(pd.DataFrame(rows), output_root / "figure_data", "figure_5_profiles")
    if not active:
        return

    users = list(active)
    colors = user_colors(users)
    ticks = list(period_index.values())

    if len(users) <= 6:
        fig, ax = plt.subplots(figsize=DOUBLE_COLUMN)
        for user in users:
            numbers, stage2_values, _ = active[user]
            ax.plot(
                numbers, stage2_values, marker="o", markersize=4, linestyle="--",
                linewidth=1.2, color=colors[user], label=f"{_math_label(user)}, Stage 2",
            )
        # Widest line first: coincident Stage-3 profiles stay visible because
        # each later user is drawn narrower on top of the earlier ones.
        widths = [3.4 - 0.9 * idx for idx in range(len(users))]
        for user, width in zip(users, widths):
            numbers, _, stage3_values = active[user]
            ax.plot(
                numbers, stage3_values, marker="s", markersize=4, linestyle="-",
                linewidth=max(width, 1.0), color=colors[user], alpha=0.95,
                label=f"{_math_label(user)}, Stage 3",
            )
        ax.axhline(
            guarantee, linestyle=":", linewidth=1.0, color=GUARANTEE_COLOR,
            label=rf"guarantee $\lambda^*={guarantee:g}$",
        )
        ax.set_xlabel("Planning period")
        ax.set_ylabel("Service ratio")
        ax.set_xticks(ticks, [_math_label(period) for period in model.periods])
        ax.set_ylim(0.5, 1.02)
        ax.grid(True, linewidth=0.4, alpha=0.5)
        ax.legend(frameon=False, ncol=2, fontsize=7.0)
        _save(fig, "figure_5_profiles", output_root)
        return

    # Reviewer request (round 7): with twenty blocks in two small panels the
    # profiles overlap and a twenty-entry legend is unreadable. Only the blocks
    # that Stage 3 actually moves carry information about the third stage, so
    # those are drawn in colour and named in the legend, and the rest are drawn
    # once, thin and grey, as the background they are. Every profile of every
    # block stays in figure_data/figure_5_profiles.csv of the archived package.
    MOVED = 1e-9
    moved = [
        user for user in users
        if max(abs(s3 - s2) for _, s2v, s3v in [active[user]]
               for s2, s3 in zip(s2v, s3v)) > MOVED
    ]
    background = [user for user in users if user not in moved]
    fig, axes = plt.subplots(1, 2, figsize=(7.6, 3.6), sharey=True)
    for ax, (index, title) in zip(axes, ((1, "(a) Stage 2"), (2, "(b) Stage 3"))):
        for user in background:
            numbers, stage2_values, stage3_values = active[user]
            ax.plot(
                numbers, stage2_values if index == 1 else stage3_values,
                linewidth=0.7, color="0.72", alpha=0.85, zorder=1,
            )
        for user in moved:
            numbers, stage2_values, stage3_values = active[user]
            ax.plot(
                numbers, stage2_values if index == 1 else stage3_values,
                marker="o", markersize=3.2, linewidth=1.4,
                color=colors[user], alpha=0.95, zorder=3,
            )
        ax.axhline(guarantee, linestyle=":", linewidth=1.0, color=GUARANTEE_COLOR,
                   zorder=2)
        ax.set_title(title, fontsize=10.0)
        ax.set_xlabel("Planning period", fontsize=9.5)
        ax.set_xticks(ticks, model.periods, fontsize=8.0)
        ax.tick_params(axis="y", labelsize=8.0)
        ax.grid(True, linewidth=0.4, alpha=0.5)
    axes[0].set_ylabel("Service ratio", fontsize=9.5)
    lowest = min(
        min(min(stage2_values), min(stage3_values))
        for _, stage2_values, stage3_values in active.values()
    )
    axes[0].set_ylim(max(0.0, min(lowest, guarantee) - 0.03), 1.02)
    handles = [
        Line2D([], [], color=colors[user], marker="o", markersize=3.2,
               linewidth=1.4, label=_math_label(user))
        for user in moved
    ]
    if background:
        handles.append(
            Line2D([], [], color="0.72", linewidth=0.7,
                   label=f"the other {len(background)} blocks, unchanged by Stage 3")
        )
    handles.append(
        Line2D([], [], color=GUARANTEE_COLOR, linestyle=":", linewidth=1.0,
               label=rf"guarantee $\lambda^*={guarantee:g}$")
    )
    fig.legend(
        handles=handles, loc="lower center", ncol=min(5, len(handles)),
        frameon=False, fontsize=9.0, bbox_to_anchor=(0.5, -0.06),
    )
    _save(fig, "figure_5_profiles", output_root)


def plot_lexicographic_profiles_per_user(
    model: Benchmark,
    solution: ThreeStageSolution,
    output_root: Path,
    *,
    max_users: int = 50,
) -> None:
    """Render one Stage-1/2/3 profile PNG per user, matching the desktop
    GUI's per-user "Тақсимотлар" view (which shows all three stages for one
    user at a time), as a complement to the combined, Stage-2-vs-Stage-3-only
    ``figure_5_profiles.png``.

    Skipped when a benchmark has more than ``max_users`` active users —
    rendering hundreds of individual PNGs (e.g. a 500-user synthetic
    benchmark) would be slow and produce an unwieldy number of files; the
    combined figure remains available regardless.
    """
    active_users = [
        user
        for user in model.user_ids
        if any((period, user) in solution.stage2.ratios for period in model.periods)
    ]
    if len(active_users) > max_users:
        return

    for user in active_users:
        active_periods = [
            period for period in model.periods if (period, user) in solution.stage2.ratios
        ]
        period_numbers = list(range(1, len(active_periods) + 1))
        stage1_values = [solution.stage1.ratios[(period, user)] for period in active_periods]
        stage2_values = [solution.stage2.ratios[(period, user)] for period in active_periods]
        stage3_values = [solution.stage3.ratios[(period, user)] for period in active_periods]

        fig, ax = plt.subplots(figsize=SINGLE_COLUMN)
        draw_user_profile(
            ax,
            period_numbers,
            active_periods,
            (stage1_values, stage2_values, stage3_values),
            ("Stage 1", "Stage 2", "Stage 3"),
            xlabel="Planning period",
            ylabel="Service ratio",
            title=f"{model.name} — {user}: lexicographic profile",
        )
        _save(fig, f"profiles_by_user/{user}", output_root)


def plot_matrix_patterns(model: Benchmark, output_root: Path) -> None:
    """Render the balance- and operator-matrix sparsity patterns for one benchmark."""
    period = model.periods[0]
    small = len(model.nodes) <= 15
    m, _, node_order, edge_order = build_balance_matrices(model, period)
    a_matrix, operator_edge_order = matrix_operator(model, period)
    if operator_edge_order != edge_order:
        raise AssertionError("Matrix edge orders do not agree.")

    figure_data_dir = output_root / "figure_data"
    write_table(
        pd.DataFrame(m, index=node_order, columns=edge_order),
        figure_data_dir,
        "figure_6_balance_matrix",
        index=True,
        index_label="node",
    )
    write_table(
        pd.DataFrame(a_matrix, index=edge_order, columns=model.user_ids),
        figure_data_dir,
        "figure_7_graph_operator_matrix",
        index=True,
        index_label="edge",
    )

    _spy_panel(
        m, node_order, edge_order, "Edge variables", "Non-source nodes",
        "figure_6_matrix", output_root, small,
    )
    _spy_panel(
        a_matrix, edge_order, list(model.user_ids), "Users", "Edges",
        "figure_7_matrix", output_root, small,
    )


_CELL_INCHES = 0.30  # identical cell size in Figures 6 and 7


def _spy_panel(
    matrix: np.ndarray,
    row_labels: list[str],
    column_labels: list[str],
    xlabel: str,
    ylabel: str,
    stem: str,
    output_root: Path,
    mathify: bool,
) -> None:
    """Draw one sparsity panel.

    Figures 6 and 7 are produced by this single routine so that the two panels
    keep the same cell size, marker geometry, typography and colour code, as
    requested in review; blue marks a positive entry and red a negative one,
    which makes the lower-triangular structure of the balance matrix visible.
    """
    rows, columns = matrix.shape
    fig, ax = plt.subplots(
        figsize=(_CELL_INCHES * columns + 1.5, _CELL_INCHES * rows + 1.4)
    )
    for i in range(rows):
        for j in range(columns):
            value = matrix[i, j]
            if abs(value) <= 1e-14:
                continue
            ax.add_patch(
                Rectangle(
                    (j - 0.34, i - 0.34), 0.68, 0.68,
                    facecolor=_POSITIVE_COLOR if value > 0 else _NEGATIVE_COLOR,
                    edgecolor="black", linewidth=0.4,
                )
            )
    ax.set_xlim(-0.6, columns - 0.4)
    ax.set_ylim(rows - 0.4, -0.6)
    ax.set_aspect("equal")
    labeller = _math_label if mathify else (lambda name: name)
    ax.set_xticks(range(columns), [labeller(name) for name in column_labels])
    ax.set_yticks(range(rows), [labeller(name) for name in row_labels])
    ax.xaxis.set_ticks_position("top")
    ax.xaxis.set_label_position("top")
    ax.set_xlabel(xlabel, labelpad=6)
    ax.set_ylabel(ylabel)
    handles = [
        Rectangle((0, 0), 1, 1, facecolor=_POSITIVE_COLOR, edgecolor="black",
                  linewidth=0.4, label="positive entry")
    ]
    if bool((matrix < -1e-14).any()):
        handles.append(
            Rectangle((0, 0), 1, 1, facecolor=_NEGATIVE_COLOR, edgecolor="black",
                      linewidth=0.4, label="negative entry")
        )
    ax.legend(
        handles=handles, loc="upper center", bbox_to_anchor=(0.5, -0.04),
        ncol=len(handles), frameon=False, fontsize=7.0,
    )
    _save(fig, stem, output_root)
