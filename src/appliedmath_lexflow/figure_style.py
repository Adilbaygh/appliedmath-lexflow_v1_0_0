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

    Three deterministic layouts are used, and all three are reproducible because
    the nodes of a level are always ordered by name or by surveyed chainage.

    A small benchmark that ships surveyed canal geometry is drawn with it, since
    at that size the physical arrangement is both informative and legible.

    A surveyed network of several dozen nodes is drawn as the linear canal scheme
    that the operating organisation itself draws (:func:`canal_scheme_layout`):
    the main canal is a horizontal axis at its surveyed chainage and every
    offtake is placed on the bank it is really on, above or below the axis. That
    keeps the two facts a hydraulic reader needs -- which bank an offtake takes
    from, and how far down the canal it is -- while making the identifiers
    legible, which the surveyed coordinates themselves do not at printable size.

    A benchmark with no surveyed geometry has no physical arrangement to
    preserve, and is laid out by topological level.
    """
    levels = nx.single_source_shortest_path_length(graph, model.source)
    if model.node_positions is not None and is_small_network(model):
        positions = {node: model.node_positions[node] for node in graph.nodes}
        return positions, levels

    if model.node_positions is not None:
        scheme = canal_scheme_layout(model, graph)
        if scheme is not None:
            return scheme, levels

    positions: dict[str, tuple[float, float]] = {}
    layer_nodes: dict[int, list[str]] = {}
    for node, level in levels.items():
        layer_nodes.setdefault(level, []).append(node)
    horizontal = len(model.nodes) > SMALL_NETWORK_NODES
    for level, nodes in sorted(layer_nodes.items()):
        count = len(nodes)
        for idx, node in enumerate(sorted(nodes)):
            spread = (idx + 1) / (count + 1)
            positions[node] = (
                (float(level), spread) if horizontal else (spread, -float(level))
            )
    return positions, levels


#: Vertical position of an offtake marker in the linear canal scheme, with the
#: main canal on ``y = 0``. Right-bank offtakes take ``+``, left-bank ``-``.
BANK_OFFSET = 0.62


def canal_spine(model: "Benchmark", graph: nx.DiGraph) -> list[str] | None:
    """The main canal, source to tail, or ``None`` if the network is not linear.

    A node that serves a user is an offtake; every other node belongs to the
    canal itself. The canal is linear when each of its nodes continues into at
    most one further canal node, which is what makes a linear scheme the right
    drawing. Anything else -- a canal that forks into two canals -- is not drawn
    this way.
    """
    terminals = {user.terminal for user in model.users}
    spine = [model.source]
    node = model.source
    while True:
        onward = [c for c in graph.successors(node) if c not in terminals]
        if len(onward) > 1:
            return None
        if not onward:
            return spine
        node = onward[0]
        spine.append(node)


def _spread(values: list[float], separation: float) -> list[float]:
    """Push values apart to at least ``separation``, preserving order and range.

    Two consecutive offtakes on the main canal can share a chainage to within a
    fraction of a per cent of the canal length, so their labels have to be
    separated on the drawing even though their tap points are not. The passes
    below enforce the separation without letting any label leave the interval
    ``[0, 1]`` spanned by the canal, and they depend only on the input order, so
    the result is reproducible.
    """
    out = list(values)
    count = len(out)
    for i in range(1, count):
        out[i] = max(out[i], out[i - 1] + separation)
    out[-1] = min(out[-1], 1.0)
    for i in range(count - 2, -1, -1):
        out[i] = min(out[i], out[i + 1] - separation)
    out[0] = max(out[0], 0.0)
    for i in range(1, count):
        out[i] = max(out[i], out[i - 1] + separation)
    return out


def canal_scheme_layout(
    model: "Benchmark", graph: nx.DiGraph
) -> dict[str, tuple[float, float]] | None:
    """Linear canal scheme: the canal on an axis, offtakes on their own banks.

    Returns ``None`` when the network is not a single canal with offtakes.
    """
    spine = canal_spine(model, graph)
    if spine is None or len(spine) < 2:
        return None
    surveyed = model.node_positions
    if surveyed is None or any(node not in surveyed for node in graph.nodes):
        return None

    chainage = {node: surveyed[node][0] for node in graph.nodes}
    low = min(chainage[node] for node in spine)
    high = max(chainage[node] for node in spine)
    if high <= low:
        return None
    # The canal is redrawn on a straight axis, but every node keeps its surveyed
    # chainage along it, so distances down the canal stay proportional.
    positions = {node: ((chainage[node] - low) / (high - low), 0.0) for node in spine}

    canal_level = sorted(surveyed[node][1] for node in spine)[len(spine) // 2]
    terminals = [user.terminal for user in model.users]
    for sign in (1.0, -1.0):
        bank = sorted(
            (t for t in terminals
             if (surveyed[t][1] > canal_level) == (sign > 0)),
            key=lambda t: (chainage[t], t),
        )
        if not bank:
            continue
        separation = min(0.075, 0.95 / max(len(bank) - 1, 1))
        slots = _spread(
            [(chainage[t] - low) / (high - low) for t in bank], separation
        )
        for terminal, slot in zip(bank, slots):
            positions[terminal] = (slot, sign * BANK_OFFSET)
    return positions if len(positions) == len(model.nodes) else None


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


def _draw_canal_scheme(
    model: "Benchmark",
    graph: nx.DiGraph,
    positions: dict[str, tuple[float, float]],
    ax: "Axes",
    spine: list[str],
    *,
    label_size: float = 6.5,
) -> None:
    """Draw the linear canal scheme of Figure 8.

    The drawing follows the linear scheme the canal operator itself uses: the
    main canal is one horizontal axis, right-bank offtakes hang above it and
    left-bank offtakes below it, each taken off at its own chainage. An offtake
    whose label cannot stand at its exact chainage, because the next offtake is
    a fraction of a per cent of the canal length away, is drawn on a slanted
    lead-off: the foot of the lead-off is the true tap point on the canal and
    only the label end is moved, so no offtake is shown on the wrong bank or in
    the wrong order. Offtake identifiers are set vertically, as in the
    operator's own drawing, because a vertical label needs a fifth of the
    horizontal room of a level one and that is what lets twenty offtakes be
    named across one text width.
    """
    reach_size = max(label_size - 1.0, 5.0)
    terminals = {user.terminal for user in model.users}
    spine_x = {node: positions[node][0] for node in spine}
    incoming = {edge.head: edge for edge in model.edges}

    # ---------------------------------------------------------- the main canal
    ordered = sorted(spine, key=lambda n: spine_x[n])
    ax.plot([spine_x[n] for n in ordered], [0.0] * len(ordered),
            color=REACH_COLOR, linewidth=2.0, solid_capstyle="butt", zorder=1)
    for tail, head in zip(ordered, ordered[1:]):
        x0, x1 = spine_x[tail], spine_x[head]
        ax.annotate("", xy=(x1, 0.0), xytext=(0.5 * (x0 + x1), 0.0),
                    arrowprops={"arrowstyle": "-|>", "color": REACH_COLOR,
                                "linewidth": 2.0, "shrinkA": 0, "shrinkB": 3.0,
                                "mutation_scale": 8}, zorder=1)
        reach = incoming.get(head)
        if reach is not None:
            # Clear of the node markers and of the canal node names, so that a
            # short reach between two close offtake points is still readable.
            ax.annotate(reach.edge_id, (0.5 * (x0 + x1), 0.19),
                        ha="center", va="center", fontsize=reach_size,
                        color=REACH_COLOR, annotation_clip=False,
                        bbox={"facecolor": "white", "edgecolor": "none",
                              "pad": 0.5})

    # --------------------------------------------------------- the lead-offs
    for terminal in sorted(terminals, key=lambda t: positions[t][0]):
        reach = incoming[terminal]
        foot = spine_x[reach.tail]
        head_x, head_y = positions[terminal]
        sign = 1.0 if head_y > 0 else -1.0
        bend = sign * 0.26
        ax.plot([foot, foot, head_x, head_x],
                [0.0, bend, head_y - sign * 0.16, head_y],
                color=REACH_COLOR, linewidth=0.7, solid_capstyle="round",
                zorder=1)
        ax.annotate("", xy=(head_x, head_y),
                    xytext=(head_x, head_y - sign * 0.10),
                    arrowprops={"arrowstyle": "-|>", "color": REACH_COLOR,
                                "linewidth": 0.7, "shrinkA": 0, "shrinkB": 2.6,
                                "mutation_scale": 6}, zorder=1)
        # The reach identifier rides the vertical part of its own lead-off and
        # the offtake identifier stands beyond the marker, so the two never meet.
        ax.annotate(reach.edge_id, (head_x, head_y - sign * 0.26),
                    ha="center", va="center", rotation=90,
                    fontsize=reach_size, color=REACH_COLOR,
                    annotation_clip=False,
                    bbox={"facecolor": "white", "edgecolor": "none", "pad": 0.4})
        ax.annotate(terminal, (head_x, head_y),
                    xytext=(0, sign * 5.0), textcoords="offset points",
                    ha="center", va="bottom" if sign > 0 else "top",
                    rotation=90, fontsize=label_size, color="black",
                    annotation_clip=False)

    # ------------------------------------------------------- canal node names
    # Alternating sides double the room available to a canal node name, which
    # matters where two offtake points are close together on the canal.
    for index, node in enumerate(ordered):
        side = 1.0 if index % 2 == 0 else -1.0
        ax.annotate(node, (spine_x[node], side * 0.075),
                    ha="center", va="bottom" if side > 0 else "top",
                    fontsize=label_size, color="black", annotation_clip=False,
                    bbox={"facecolor": "white", "edgecolor": "none", "pad": 0.5})

    nx.draw_networkx_nodes(
        graph, positions, node_size=70,
        node_color=node_role_colors(model, graph),
        edgecolors="black", linewidths=0.4, ax=ax,
    )
    ax.annotate("right bank", (-0.035, BANK_OFFSET), ha="center", va="center",
                rotation=90, fontsize=reach_size, color=REACH_COLOR,
                style="italic", annotation_clip=False)
    ax.annotate("left bank", (-0.035, -BANK_OFFSET), ha="center", va="center",
                rotation=90, fontsize=reach_size, color=REACH_COLOR,
                style="italic", annotation_clip=False)
    ax.set_xlim(-0.06, 1.05)
    ax.set_ylim(-1.02, 1.06)


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
        legend = True

    if not small:
        spine = canal_spine(model, graph)
        if spine is not None and all(
            abs(positions[node][1]) < 1e-9 for node in spine
        ):
            _draw_canal_scheme(model, graph, positions, ax, spine)
            if legend:
                ax.legend(handles=tree_legend_handles(6.5), loc="upper right",
                          frameon=False, fontsize=5.5, ncol=2,
                          handletextpad=0.4, columnspacing=1.0)
            ax.set_axis_off()
            return

    # On a small benchmark the identifier is set inside a large marker; on any
    # other network it is placed beside the node in black instead of inside it,
    # so that the label size does not depend on the node spacing.
    node_size = 900 if small else 150
    label_size = 8 if small else 7

    nx.draw_networkx_nodes(
        graph, positions, node_size=node_size,
        node_color=node_role_colors(model, graph),
        edgecolors="black", linewidths=0.6 if small else 0.4, ax=ax,
    )
    nx.draw_networkx_edges(
        graph, positions, arrows=True, arrowsize=14 if small else 9,
        arrowstyle="-|>", edge_color=REACH_COLOR, width=1.3 if small else 0.9,
        ax=ax,
    )
    # Reviewer request: identifiers are typeset as mathematical symbols on the
    # small benchmarks, where they denote the model variables of Section 2.
    if small:
        nx.draw_networkx_labels(
            graph, positions, labels={n: math_label(n) for n in graph.nodes},
            font_size=label_size, font_color="white", ax=ax,
        )
        edge_label_pos = positions
    else:
        ys = [xy[1] for xy in positions.values()]
        span = (max(ys) - min(ys)) or 1.0
        node_offset, edge_offset = 0.075 * span, -0.075 * span
        nx.draw_networkx_labels(
            graph, {n: (x, y + node_offset) for n, (x, y) in positions.items()},
            labels={n: n for n in graph.nodes}, font_size=label_size,
            font_color="black", ax=ax,
        )
        edge_label_pos = {
            n: (x, y + edge_offset) for n, (x, y) in positions.items()
        }
    edge_labels = {
        (edge.tail, edge.head): (math_label(edge.edge_id) if small else edge.edge_id)
        for edge in model.edges
    }
    nx.draw_networkx_edge_labels(
        graph, edge_label_pos, edge_labels=edge_labels, rotate=False,
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
