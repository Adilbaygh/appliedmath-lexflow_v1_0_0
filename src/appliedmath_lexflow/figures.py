from __future__ import annotations

from collections.abc import Iterable
from fractions import Fraction
from pathlib import Path

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd

from .domain import Benchmark
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
_SOFTWARE_LABEL = "AppliedMath LexFlow 0.3.0"


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
    levels = nx.single_source_shortest_path_length(graph, model.source)
    if model.node_positions is not None:
        # Use the real canal-system geometry when the benchmark ships one,
        # instead of a generic depth-level layout that does not reflect the
        # actual physical network.
        positions = {node: model.node_positions[node] for node in graph.nodes}
    else:
        layer_nodes: dict[int, list[str]] = {}
        for node, level in levels.items():
            layer_nodes.setdefault(level, []).append(node)
        positions = {}
        for level, nodes in sorted(layer_nodes.items()):
            count = len(nodes)
            for idx, node in enumerate(sorted(nodes)):
                x = (idx + 1) / (count + 1)
                positions[node] = (x, -float(level))

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

    # Larger trees need more canvas to stay legible; small benchmarks keep the
    # original journal double-column size.
    figsize = DOUBLE_COLUMN if len(model.nodes) <= 15 else (12.0, 6.5)
    fig, ax = plt.subplots(figsize=figsize)
    node_size = 900 if len(model.nodes) <= 15 else 260
    label_size = 8 if len(model.nodes) <= 15 else 6
    nx.draw_networkx_nodes(graph, positions, node_size=node_size, ax=ax)
    nx.draw_networkx_edges(graph, positions, arrows=True, arrowsize=14, ax=ax)
    nx.draw_networkx_labels(graph, positions, font_size=label_size, ax=ax)
    edge_labels = {(edge.tail, edge.head): edge.edge_id for edge in model.edges}
    nx.draw_networkx_edge_labels(
        graph, positions, edge_labels=edge_labels, font_size=max(label_size - 1, 5), ax=ax
    )
    ax.set_title(f"{model.name}: rooted canal tree")
    ax.set_axis_off()
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
    data: pd.DataFrame, output_root: Path, *, title: str | None = None
) -> None:
    """Render the node-balance-vs-operator-flow scatter for the given rows."""
    write_table(data, output_root / "figure_data", "figure_4_operator_balance_agreement")

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
    _save(fig, "figure_4_operator_balance_agreement", output_root)


def plot_lexicographic_profiles(
    model: Benchmark, solution: ThreeStageSolution, output_root: Path
) -> None:
    """Render Stage-2 vs. Stage-3 service-ratio profiles for one benchmark."""
    rows: list[dict[str, float | str]] = []
    period_index = {period: idx + 1 for idx, period in enumerate(model.periods)}
    fig, ax = plt.subplots(figsize=DOUBLE_COLUMN)
    for user in model.user_ids:
        # Periods with zero demand for this user are excluded from the
        # optimization records entirely (no ratio is defined), so only plot
        # the periods where the user actually has an active record.
        active_periods = [
            period for period in model.periods if (period, user) in solution.stage2.ratios
        ]
        if not active_periods:
            continue
        active_numbers = [period_index[period] for period in active_periods]
        stage2_values = [solution.stage2.ratios[(period, user)] for period in active_periods]
        stage3_values = [solution.stage3.ratios[(period, user)] for period in active_periods]
        ax.plot(
            active_numbers,
            stage2_values,
            marker="o",
            linestyle="--",
            label=f"{user}, Stage 2",
        )
        ax.plot(
            active_numbers,
            stage3_values,
            marker="s",
            linestyle="-",
            label=f"{user}, Stage 3",
        )
        for period, s2, s3 in zip(active_periods, stage2_values, stage3_values):
            rows.append(
                {
                    "period": period,
                    "user": user,
                    "stage2_ratio": s2,
                    "stage3_ratio": s3,
                }
            )
    write_table(pd.DataFrame(rows), output_root / "figure_data", "figure_5_profiles")
    ax.axhline(
        float(solution.lambda_closed_form),
        linestyle=":",
        linewidth=1.0,
        label=r"$\lambda^*$",
    )
    ax.set_xlabel("Planning period")
    ax.set_ylabel("Service ratio")
    ax.set_xticks(list(period_index.values()), model.periods)
    ax.set_ylim(0.5, 1.02)
    # A per-user legend becomes unreadable clutter once a benchmark has more
    # than a handful of users (e.g. gone_abat_jap has 20); skip it there.
    if len(model.user_ids) <= 6:
        ax.legend(frameon=False, ncol=2)
    ax.grid(True, linewidth=0.4, alpha=0.5)
    ax.set_title(f"{model.name}: lexicographic profiles")
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
        ax.plot(period_numbers, stage1_values, marker="o", label="Stage 1")
        ax.plot(period_numbers, stage2_values, marker="s", label="Stage 2")
        ax.plot(period_numbers, stage3_values, marker="^", label="Stage 3")
        ax.set_xticks(period_numbers, active_periods)
        ax.set_ylim(0.0, 1.05)
        ax.set_xlabel("Planning period")
        ax.set_ylabel("Service ratio")
        ax.set_title(f"{model.name} — {user}: lexicographic profile")
        ax.grid(True, alpha=0.3)
        ax.legend(loc="best")
        _save(fig, f"profiles_by_user/{user}", output_root)


def plot_matrix_patterns(model: Benchmark, output_root: Path) -> None:
    """Render the balance- and operator-matrix sparsity patterns for one benchmark."""
    period = model.periods[0]
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

    fig_m, ax_m = plt.subplots(figsize=SINGLE_COLUMN)
    ax_m.spy(m, markersize=7)
    ax_m.set_xlabel("Edge variables")
    ax_m.set_ylabel("Non-source nodes")
    ax_m.set_title(f"{model.name}: sparsity pattern of $M_k$")
    _save(fig_m, "figure_6_matrix", output_root)

    fig_a, ax_a = plt.subplots(figsize=SINGLE_COLUMN)
    ax_a.spy(np.abs(a_matrix) > 1e-14, markersize=7)
    ax_a.set_xlabel("Users")
    ax_a.set_ylabel("Edges")
    ax_a.set_title(f"{model.name}: nonzero pattern of $A_k=M_k^{{-1}}P$")
    _save(fig_a, "figure_7_matrix", output_root)
