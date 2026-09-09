"""Colour code and drawing primitives shared by every plot the project draws.

Both the publication figures (:mod:`appliedmath_lexflow.figures`, used by
``main.py analysis`` / ``run_analysis.py``) and the interactive desktop
application (:mod:`appliedmath_lexflow.desktop_gui`, opened by a bare
``main.py``) render through this module. A network or a service-ratio profile
displayed in the GUI therefore uses exactly the same node-role colours, edge
colour, stage colours, markers, layout and label typesetting as the
corresponding figure in the article, so that the figures printed in the paper
are visibly the output of this software.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

import networkx as nx

try:  # matplotlib >= 3.6
    from matplotlib import colormaps as _COLORMAPS

    def _get_cmap(name: str):
        return _COLORMAPS[name]

except ImportError:  # pragma: no cover - older matplotlib
    from matplotlib.cm import get_cmap as _get_cmap

from matplotlib.lines import Line2D

if TYPE_CHECKING:  # pragma: no cover - typing only
    from matplotlib.axes import Axes

    from .domain import Benchmark

# --------------------------------------------------------------- colour code
# Matrix-pattern panels (Figures 6 and 7).
POSITIVE_COLOR = "#1f77b4"
NEGATIVE_COLOR = "#d62728"
# Node roles in the rooted-tree figure (Figure 1) and in the GUI network tab.
SOURCE_COLOR = "#1f77b4"
JUNCTION_COLOR = "#8c8c8c"
TERMINAL_COLOR = "#2ca02c"
REACH_COLOR = "#404040"
# The three lexicographic stages, wherever they are drawn together.
STAGE_COLORS = ("#1f77b4", "#ff7f0e", "#2ca02c")
STAGE_MARKERS = ("o", "s", "^")
GUARANTEE_COLOR = "black"

#: Networks with at most this many nodes are drawn in the "small" style:
#: large markers, white node labels and mathematical identifiers.
SMALL_NETWORK_NODES = 15

_LABEL_PATTERN = re.compile(r"^([A-Za-z])(\d+)$")


def math_label(name: str) -> str:
    """Render ``e12`` as ``$e_{12}$`` and ``s`` as ``$s$``.

    Applied only to the small synthetic benchmarks, whose identifiers are
    single letters with an optional index. Real canal networks carry
    descriptive node names that must stay as plain text.
    """
    match = _LABEL_PATTERN.match(name)
    if match is not None:
        return f"${match.group(1)}_{{{match.group(2)}}}$"
    if len(name) == 1 and name.isalpha():
        return f"${name}$"
    return name


def is_small_network(model: "Benchmark") -> bool:
    return len(model.nodes) <= SMALL_NETWORK_NODES


def user_colors(users: list[str]) -> dict[str, tuple[float, float, float, float]]:
    """Assign each user a stable qualitative colour, as in Figures 5 and 9."""
    cmap = _get_cmap("tab10" if len(users) <= 10 else "tab20")
    return {user: cmap(idx % cmap.N) for idx, user in enumerate(users)}


def tree_layout(
    model: "Benchmark", graph: nx.DiGraph
) -> tuple[dict[str, tuple[float, float]], dict[str, int]]:
    """Node coordinates and topological levels of one benchmark network.

    Benchmarks that ship real canal-system geometry are drawn with it; the
    remaining ones get a deterministic depth-level layout in which each level
    is spread evenly and its nodes are ordered by name, so the picture is
    identical every time and in every entry point.
    """
    levels = nx.single_source_shortest_path_length(graph, model.source)
    if model.node_positions is not None:
        positions = {node: model.node_positions[node] for node in graph.nodes}
        return positions, levels

    layer_nodes: dict[int, list[str]] = {}
    for node, level in levels.items():
        layer_nodes.setdefault(level, []).append(node)
    positions: dict[str, tuple[float, float]] = {}
    for level, nodes in sorted(layer_nodes.items()):
        count = len(nodes)
        for idx, node in enumerate(sorted(nodes)):
            positions[node] = ((idx + 1) / (count + 1), -float(level))
    return positions, levels


def node_role_colors(model: "Benchmark", graph: nx.DiGraph) -> list[str]:
    terminals = {user.terminal for user in model.users}
    return [
        SOURCE_COLOR
        if node == model.source
        else (TERMINAL_COLOR if node in terminals else JUNCTION_COLOR)
        for node in graph.nodes
    ]


def tree_legend_handles(label_size: float) -> list[Line2D]:
    return [
        Line2D([], [], marker="o", linestyle="", markersize=7,
               markerfacecolor=SOURCE_COLOR, markeredgecolor="black",
               label="source $s$"),
        Line2D([], [], marker="o", linestyle="", markersize=7,
               markerfacecolor=JUNCTION_COLOR, markeredgecolor="black",
               label="junction node"),
        Line2D([], [], marker="o", linestyle="", markersize=7,
               markerfacecolor=TERMINAL_COLOR, markeredgecolor="black",
               label="terminal offtake $t_f$"),
        Line2D([], [], color=REACH_COLOR, linewidth=1.3,
               label="directed reach $e_i$"),
    ]


def draw_tree(
    model: "Benchmark",
    graph: nx.DiGraph,
    positions: dict[str, tuple[float, float]],
    ax: "Axes",
    *,
    small: bool | None = None,
    legend: bool | None = None,
) -> None:
    """Draw one rooted canal tree onto ``ax`` in the article's style."""
    if small is None:
        small = is_small_network(model)
    if legend is None:
        legend = small
    node_size = 900 if small else 260
    label_size = 8 if small else 6

    nx.draw_networkx_nodes(
        graph, positions, node_size=node_size,
        node_color=node_role_colors(model, graph),
        edgecolors="black", linewidths=0.6, ax=ax,
    )
    nx.draw_networkx_edges(
        graph, positions, arrows=True, arrowsize=14, arrowstyle="-|>",
        edge_color=REACH_COLOR, width=1.3, ax=ax,
    )
    # Reviewer request: identifiers are typeset as mathematical symbols on the
    # small benchmarks, where they denote the model variables of Section 2.
    node_labels = {n: (math_label(n) if small else n) for n in graph.nodes}
    nx.draw_networkx_labels(
        graph, positions, labels=node_labels, font_size=label_size,
        font_color="white", ax=ax,
    )
    edge_labels = {
        (edge.tail, edge.head): (math_label(edge.edge_id) if small else edge.edge_id)
        for edge in model.edges
    }
    nx.draw_networkx_edge_labels(
        graph, positions, edge_labels=edge_labels, rotate=False,
        font_size=max(label_size - 1, 5),
        bbox={"facecolor": "white", "edgecolor": "none", "pad": 0.6}, ax=ax,
    )
    if legend:
        ax.legend(
            handles=tree_legend_handles(label_size),
            loc="upper left", frameon=False, fontsize=max(label_size - 1, 5),
        )
    ax.set_axis_off()
    ax.margins(0.14, 0.12)


def draw_user_profile(
    ax: "Axes",
    period_numbers: list[int],
    period_labels: list[str],
    stage_series: tuple[list[float], list[float], list[float]],
    stage_labels: tuple[str, str, str],
    *,
    xlabel: str,
    ylabel: str,
    title: str | None = None,
) -> None:
    """Draw the Stage-1/2/3 service-ratio profile of a single user onto ``ax``.

    Used both for the ``profiles_by_user`` PNGs written by the reporting
    pipeline and for the GUI's per-user allocation chart, so the two are
    colour- and marker-identical.
    """
    for values, label, color, marker in zip(
        stage_series, stage_labels, STAGE_COLORS, STAGE_MARKERS
    ):
        ax.plot(period_numbers, values, marker=marker, color=color, label=label)
    ax.set_xticks(period_numbers, period_labels)
    ax.set_ylim(0.0, 1.05)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    if title is not None:
        ax.set_title(title)
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best")
