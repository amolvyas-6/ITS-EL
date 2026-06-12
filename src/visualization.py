"""Visualization pipeline for ITS traffic simulation outputs."""

import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
import networkx as nx
import numpy as np
import seaborn as sns


plt.rcParams.update(
    {
        "figure.facecolor": "#0d1117",
        "axes.facecolor": "#161b22",
        "axes.edgecolor": "#30363d",
        "axes.labelcolor": "#c9d1d9",
        "xtick.color": "#8b949e",
        "ytick.color": "#8b949e",
        "text.color": "#c9d1d9",
        "font.family": "sans-serif",
        "font.size": 10,
        "axes.titlesize": 14,
        "axes.labelsize": 11,
        "figure.titlesize": 16,
        "grid.color": "#21262d",
        "grid.alpha": 0.5,
    }
)


NODE_COLORS = {
    "major_signalized": "#C0392B",
    "signalized": "#E67E22",
    "arterial_merge": "#2980B9",
    "flyover_merge": "#16A085",
    "destination_zone": "#27AE60",
}


OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "outputs")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def _save_fig(fig, filename):
    path = os.path.join(OUTPUT_DIR, filename)
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"  Saved: {path}")
    return path


def _short_label(label, max_len=18):
    if len(label) <= max_len:
        return label
    return label[: max_len - 3] + "..."


def plot_graph(
    G,
    title="Road Network - Intersection Graph",
    filename="01_graph.png",
    highlight_nodes=None,
    density=None,
):
    """Draw directed road network with color-coded intersection types."""
    fig, ax = plt.subplots(1, 1, figsize=(14, 8))

    pos = nx.get_node_attributes(G, "pos")
    labels = nx.get_node_attributes(G, "label")
    types = nx.get_node_attributes(G, "node_type")

    if density is not None:
        density = np.asarray(density, dtype=float)
        node_sizes = 350 + (density * 2600)
    else:
        node_sizes = [520 if types[n] == "major_signalized" else 420 for n in G.nodes()]

    node_colors = [NODE_COLORS.get(types[n], "#8b949e") for n in G.nodes()]
    if highlight_nodes:
        node_colors = [highlight_nodes.get(n, node_colors[idx]) for idx, n in enumerate(G.nodes())]

    edge_capacities = [edata.get("capacity", 1200) for _, _, edata in G.edges(data=True)]
    max_capacity = max(edge_capacities) if edge_capacities else 1.0
    edge_widths = [1.0 + 3.0 * (c / max_capacity) for c in edge_capacities]

    nx.draw_networkx_edges(
        G,
        pos,
        ax=ax,
        edge_color="#3d4754",
        width=edge_widths,
        alpha=0.75,
        arrows=G.is_directed(),
        arrowstyle="-|>",
        arrowsize=12,
        connectionstyle="arc3,rad=0.05",
    )

    nx.draw_networkx_nodes(
        G,
        pos,
        ax=ax,
        node_color=node_colors,
        node_size=node_sizes,
        edgecolors="#d0d7de",
        linewidths=1.3,
    )

    short_labels = {n: _short_label(lbl, 16) for n, lbl in labels.items()}
    nx.draw_networkx_labels(
        G,
        pos,
        labels=short_labels,
        ax=ax,
        font_size=7,
        font_color="white",
        font_weight="bold",
    )

    edge_labels = {
        (u, v): str(int(d.get("weight", 0)))
        for u, v, d in G.edges(data=True)
        if d.get("weight", 0) > 0
    }
    nx.draw_networkx_edge_labels(
        G,
        pos,
        edge_labels=edge_labels,
        ax=ax,
        font_size=6,
        font_color="#9fb3c8",
        label_pos=0.45,
        bbox={"boxstyle": "round,pad=0.15", "fc": "#0d1117", "ec": "none", "alpha": 0.7},
    )

    legend_items = []
    for node_type, color in NODE_COLORS.items():
        legend_items.append(
            plt.scatter([], [], s=90, c=color, edgecolors="#d0d7de", label=node_type)
        )
    ax.legend(
        handles=legend_items,
        loc="upper left",
        framealpha=0.85,
        facecolor="#161b22",
        edgecolor="#30363d",
        fontsize=8,
    )

    ax.set_title(title, fontsize=16, fontweight="bold", pad=12)
    ax.set_xlim(-0.02, 1.02)
    ax.set_ylim(-0.02, 1.02)
    ax.set_aspect("equal")
    ax.axis("off")

    return _save_fig(fig, filename)


def plot_density_heatmap(
    history,
    node_list,
    G,
    title="Vehicle Density (Normalized PCU) Over Signal Cycles",
    filename="02_density_heatmap.png",
):
    """Plot vehicle density heatmap over time."""
    fig, ax = plt.subplots(1, 1, figsize=(16, 8))

    matrix = np.array(history)
    labels = [_short_label(G.nodes[n]["label"], 20) for n in node_list]

    cmap = sns.color_palette("rocket_r", as_cmap=True)
    image = ax.imshow(matrix.T, aspect="auto", cmap=cmap, interpolation="nearest")

    ax.set_xlabel("Signal Cycle")
    ax.set_ylabel("Intersection")
    ax.set_title(title, fontsize=16, fontweight="bold", pad=14)

    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels, fontsize=8)

    step_count = matrix.shape[0]
    ticks = list(range(0, step_count, max(1, step_count // 10)))
    ax.set_xticks(ticks)
    ax.set_xticklabels([str(t) for t in ticks])

    cbar = fig.colorbar(image, ax=ax, shrink=0.8, pad=0.02)
    cbar.set_label("Vehicle Density (Normalized PCU)")

    fig.tight_layout()
    return _save_fig(fig, filename)


def plot_distribution_evolution(
    history,
    node_list,
    G,
    title="Vehicle Density Evolution",
    filename="03_evolution.png",
):
    """Plot per-intersection density evolution lines."""
    fig, axes = plt.subplots(2, 1, figsize=(14, 10), height_ratios=[3, 1])

    matrix = np.array(history)
    labels = {node: G.nodes[node]["label"] for node in G.nodes()}
    types = {node: G.nodes[node]["node_type"] for node in G.nodes()}
    timesteps = np.arange(matrix.shape[0])

    ax = axes[0]
    for i, node in enumerate(node_list):
        color = NODE_COLORS.get(types[node], "#8b949e")
        lw = 2.4 if np.max(matrix[:, i]) > 0.06 else 1.0
        ax.plot(
            timesteps,
            matrix[:, i],
            color=color,
            linewidth=lw,
            alpha=0.85,
            label=_short_label(labels[node], 18),
        )

    ax.set_xlabel("Signal Cycle")
    ax.set_ylabel("Vehicle Density (Normalized PCU)")
    ax.set_title(title, fontsize=16, fontweight="bold")
    ax.set_xlim(0, matrix.shape[0] - 1)
    ax.grid(True, alpha=0.3)
    ax.legend(
        loc="upper right",
        ncol=3,
        fontsize=7,
        framealpha=0.85,
        facecolor="#161b22",
        edgecolor="#30363d",
    )

    ax2 = axes[1]
    major_indices = [
        i
        for i, node in enumerate(node_list)
        if types[node] in {"major_signalized", "signalized", "arterial_merge"}
        and np.max(matrix[:, i]) > 0.015
    ]
    if major_indices:
        ax2.stackplot(
            timesteps,
            *[matrix[:, i] for i in major_indices],
            labels=[_short_label(labels[node_list[i]], 18) for i in major_indices],
            colors=[NODE_COLORS.get(types[node_list[i]], "#8b949e") for i in major_indices],
            alpha=0.7,
        )
        ax2.set_xlim(0, matrix.shape[0] - 1)
        ax2.set_xlabel("Signal Cycle")
        ax2.set_ylabel("Cum. Density")
        ax2.set_title("Key Corridors - Stacked Vehicle Density", fontsize=12)
        ax2.grid(True, alpha=0.3)

    fig.tight_layout()
    return _save_fig(fig, filename)


def plot_transition_matrix(
    T,
    node_list,
    G,
    title="Vehicle Routing Probability Matrix",
    filename="04_transition_matrix.png",
):
    """Render transition matrix heatmap with high-value annotations."""
    fig, ax = plt.subplots(1, 1, figsize=(12, 10))

    labels = [_short_label(G.nodes[n]["label"], 14) for n in node_list]
    cmap = sns.color_palette("viridis", as_cmap=True)
    image = ax.imshow(T, cmap=cmap, vmin=0.0, vmax=float(np.max(T)))

    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=7)
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels, fontsize=7)

    ax.set_xlabel("To Intersection")
    ax.set_ylabel("From Intersection")
    ax.set_title(title, fontsize=16, fontweight="bold", pad=12)

    for i in range(T.shape[0]):
        for j in range(T.shape[1]):
            if T[i, j] > 0.05:
                color = "white" if T[i, j] > 0.45 else "#d5dde5"
                ax.text(j, i, f"{T[i, j]:.2f}", ha="center", va="center", fontsize=6, color=color)

    cbar = fig.colorbar(image, ax=ax, shrink=0.8)
    cbar.set_label("Routing Probability")

    fig.tight_layout()
    return _save_fig(fig, filename)


def plot_stationary_distribution(
    pi,
    node_list,
    G,
    title="Long-Run Intersection Utilization",
    filename="05_stationary.png",
):
    """Plot long-run utilization (stationary distribution)."""
    fig, ax = plt.subplots(1, 1, figsize=(14, 6))

    labels = [_short_label(G.nodes[n]["label"], 18) for n in node_list]
    colors = [NODE_COLORS.get(G.nodes[n]["node_type"], "#8b949e") for n in node_list]

    bars = ax.bar(range(len(pi)), pi, color=colors, edgecolor="#30363d", linewidth=1.0, alpha=0.9)
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=8)
    ax.set_ylabel("Utilization Probability")
    ax.set_title(title, fontsize=16, fontweight="bold", pad=12)
    ax.grid(axis="y", alpha=0.3)

    for bar, value in zip(bars, pi):
        if value > 0.01:
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.003,
                f"{value:.3f}",
                ha="center",
                va="bottom",
                fontsize=7,
            )

    fig.tight_layout()
    return _save_fig(fig, filename)


def plot_comparison(
    history_before,
    history_after,
    node_list,
    G,
    title="Pre-ATMS Intervention vs Post-ATMS Signal Optimization",
    filename="06_comparison.png",
):
    """Heatmap comparison of pre/post interventions."""
    fig, axes = plt.subplots(1, 2, figsize=(18, 8), constrained_layout=True)

    matrix_before = np.array(history_before)
    matrix_after = np.array(history_after)
    labels = [_short_label(G.nodes[n]["label"], 18) for n in node_list]

    cmap = sns.color_palette("rocket_r", as_cmap=True)
    vmax = float(max(np.max(matrix_before), np.max(matrix_after)))

    image_before = axes[0].imshow(matrix_before.T, aspect="auto", cmap=cmap, vmin=0, vmax=vmax)
    axes[0].set_title("Pre-ATMS Intervention", fontsize=14, fontweight="bold", color="#f4d03f")
    axes[0].set_xlabel("Signal Cycle")
    axes[0].set_ylabel("Intersection")
    axes[0].set_yticks(range(len(labels)))
    axes[0].set_yticklabels(labels, fontsize=7)

    image_after = axes[1].imshow(matrix_after.T, aspect="auto", cmap=cmap, vmin=0, vmax=vmax)
    axes[1].set_title("Post-ATMS Signal Optimization", fontsize=14, fontweight="bold", color="#2ecc71")
    axes[1].set_xlabel("Signal Cycle")
    axes[1].set_yticks(range(len(labels)))
    axes[1].set_yticklabels(labels, fontsize=7)

    fig.colorbar(
        image_after,
        ax=axes,
        shrink=0.65,
        pad=0.02,
        label="Vehicle Density (Normalized PCU)",
    )
    fig.suptitle(title, fontsize=16, fontweight="bold")
    return _save_fig(fig, filename)


def plot_comparison_bars(
    pi_before,
    pi_after,
    node_list,
    G,
    title="Long-Run Intersection Utilization - Pre vs Post ATMS",
    filename="07_comparison_bars.png",
):
    """Grouped bar chart for pre/post stationary utilization."""
    fig, ax = plt.subplots(1, 1, figsize=(14, 6))

    labels = [_short_label(G.nodes[n]["label"], 18) for n in node_list]
    xvals = np.arange(len(labels))
    width = 0.36

    ax.bar(
        xvals - width / 2,
        pi_before,
        width,
        label="Pre-ATMS Intervention",
        color="#f39c12",
        edgecolor="#30363d",
        alpha=0.85,
    )
    ax.bar(
        xvals + width / 2,
        pi_after,
        width,
        label="Post-ATMS Signal Optimization",
        color="#27ae60",
        edgecolor="#30363d",
        alpha=0.85,
    )

    ax.set_xticks(xvals)
    ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=8)
    ax.set_ylabel("Utilization Probability")
    ax.set_title(title, fontsize=16, fontweight="bold", pad=12)
    ax.grid(axis="y", alpha=0.3)
    ax.legend(fontsize=9, framealpha=0.85, facecolor="#161b22", edgecolor="#30363d")

    fig.tight_layout()
    return _save_fig(fig, filename)


def plot_mfpt(
    mfpt_before,
    mfpt_after,
    node_list,
    G,
    title="Average Network Travel Time (Signal Cycles)",
    filename="08_mfpt.png",
):
    """Horizontal bar chart of ANTT before/after intervention."""
    fig, ax = plt.subplots(1, 1, figsize=(14, 6))

    labels = [_short_label(G.nodes[n]["label"], 20) for n in node_list]
    before_vals = [mfpt_before.get(n, 0.0) for n in node_list]
    after_vals = [mfpt_after.get(n, 0.0) for n in node_list]

    yvals = np.arange(len(labels))
    width = 0.36

    ax.barh(
        yvals - width / 2,
        before_vals,
        width,
        label="Pre-ATMS Intervention",
        color="#e67e22",
        edgecolor="#30363d",
        alpha=0.85,
    )
    ax.barh(
        yvals + width / 2,
        after_vals,
        width,
        label="Post-ATMS Signal Optimization",
        color="#2ecc71",
        edgecolor="#30363d",
        alpha=0.85,
    )

    ax.set_yticks(yvals)
    ax.set_yticklabels(labels, fontsize=8)
    ax.set_xlabel("Average Network Travel Time (Signal Cycles)")
    ax.set_title(title, fontsize=16, fontweight="bold", pad=12)
    ax.grid(axis="x", alpha=0.3)
    ax.legend(fontsize=9, framealpha=0.85, facecolor="#161b22", edgecolor="#30363d")
    ax.invert_yaxis()

    fig.tight_layout()
    return _save_fig(fig, filename)


def plot_congestion_timeline(
    v_c_history,
    node_list,
    G,
    threshold=0.85,
    title="Saturated Intersection Timeline",
    filename="09_congestion_timeline.png",
):
    """Scatter timeline of v/c saturation events across signal cycles."""
    fig, ax = plt.subplots(1, 1, figsize=(14, 6))

    labels = [_short_label(G.nodes[n]["label"], 20) for n in node_list]
    ratio_matrix = np.array(
        [[float(step.get(node, 0.0)) for node in node_list] for step in v_c_history],
        dtype=float,
    )

    for t in range(ratio_matrix.shape[0]):
        for j in range(ratio_matrix.shape[1]):
            value = ratio_matrix[t, j]
            if value > threshold:
                ax.scatter(
                    t,
                    j,
                    s=110 + (value * 130),
                    c="#c0392b" if value > 1.0 else "#e67e22",
                    alpha=0.65,
                    edgecolors="#f7d9c8",
                    linewidths=1.2,
                )

    for j in range(ratio_matrix.shape[1]):
        ax.axhline(y=j, color="#1f2a36", linewidth=0.4)

    ax.axvline(0, color="#34495e", linewidth=1.0, linestyle=":")

    ax.set_xlabel("Signal Cycle")
    ax.set_ylabel("Intersection")
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels, fontsize=8)
    ax.set_xlim(-0.5, ratio_matrix.shape[0] - 0.5)
    ax.set_title(
        f"{title} (v/c threshold {threshold:.2f})",
        fontsize=16,
        fontweight="bold",
        pad=12,
    )

    fig.tight_layout()
    return _save_fig(fig, filename)


def plot_graph_snapshots(
    G,
    history,
    node_list,
    timesteps=None,
    filename="10_snapshots.png",
):
    """Graph snapshots over selected cycles with density overlays."""
    matrix = np.array(history)

    if timesteps is None:
        max_t = matrix.shape[0] - 1
        timesteps = sorted(set([0, max_t // 4, max_t // 2, (3 * max_t) // 4, max_t]))

    fig, axes = plt.subplots(1, len(timesteps), figsize=(5 * len(timesteps), 6))
    if len(timesteps) == 1:
        axes = [axes]

    pos = nx.get_node_attributes(G, "pos")
    types = nx.get_node_attributes(G, "node_type")

    for idx, timestep in enumerate(timesteps):
        ax = axes[idx]
        density = matrix[timestep]

        node_sizes = 240 + density * 3200
        colors = []
        for i, node in enumerate(node_list):
            base = NODE_COLORS.get(types[node], "#8b949e")
            if density[i] > 0.12:
                colors.append("#e74c3c")
            elif density[i] > 0.06:
                colors.append("#f1c40f")
            else:
                colors.append(base)

        nx.draw_networkx_edges(
            G,
            pos,
            ax=ax,
            edge_color="#3d4754",
            width=1.2,
            alpha=0.55,
            arrows=G.is_directed(),
            arrowstyle="-|>",
            arrowsize=10,
            connectionstyle="arc3,rad=0.05",
        )
        nx.draw_networkx_nodes(
            G,
            pos,
            ax=ax,
            node_color=colors,
            node_size=node_sizes,
            edgecolors="#d0d7de",
            linewidths=1.1,
            alpha=0.9,
        )

        for i, node in enumerate(node_list):
            if density[i] > 0.015:
                x, y = pos[node]
                ax.text(
                    x,
                    y,
                    f"{density[i]:.2f}",
                    ha="center",
                    va="center",
                    fontsize=6,
                    color="white",
                    fontweight="bold",
                    path_effects=[pe.withStroke(linewidth=1.7, foreground="black")],
                )

        ax.set_title(f"Cycle {timestep}", fontsize=11, fontweight="bold")
        ax.set_xlim(-0.02, 1.02)
        ax.set_ylim(-0.02, 1.02)
        ax.axis("off")

    fig.suptitle("Vehicle Density Snapshots Across Signal Cycles", fontsize=16, fontweight="bold")
    fig.tight_layout()
    return _save_fig(fig, filename)


def plot_adjacency_matrix(
    adjacency,
    node_list,
    G,
    title="Directed Adjacency Matrix",
    filename="11_adjacency_matrix.png",
):
    """Plot directed adjacency matrix."""
    fig, ax = plt.subplots(1, 1, figsize=(10, 8))

    labels = [_short_label(G.nodes[n]["label"], 12) for n in node_list]
    cmap = sns.color_palette("YlOrRd", as_cmap=True)
    image = ax.imshow(adjacency, cmap=cmap, vmin=0, vmax=1)

    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=7)
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels, fontsize=7)
    ax.set_title(title, fontsize=16, fontweight="bold", pad=12)

    for i in range(adjacency.shape[0]):
        for j in range(adjacency.shape[1]):
            if adjacency[i, j] > 0:
                ax.text(j, i, "1", ha="center", va="center", fontsize=6, color="white")

    fig.colorbar(image, ax=ax, shrink=0.8, label="Connectivity")
    fig.tight_layout()
    return _save_fig(fig, filename)


def plot_v_c_ratio_timeline(
    v_c_history_before,
    v_c_history_after,
    node_list,
    G,
    title="v/c Ratio Timeline - Top Congested Intersections",
    filename="v_c_ratio_timeline.png",
):
    """Plot v/c ratios for top 5 congested nodes before and after optimization."""
    fig, ax = plt.subplots(1, 1, figsize=(14, 7))

    peak_before = {}
    for node in node_list:
        series = [float(step.get(node, 0.0)) for step in v_c_history_before]
        peak_before[node] = max(series) if series else 0.0

    top_nodes = [
        node for node, _ in sorted(peak_before.items(), key=lambda item: item[1], reverse=True)[:5]
    ]

    palette = sns.color_palette("tab10", n_colors=max(5, len(top_nodes)))
    x_before = np.arange(len(v_c_history_before))
    x_after = np.arange(len(v_c_history_after))

    for idx, node in enumerate(top_nodes):
        label = _short_label(G.nodes[node]["label"], 22)
        before_series = [float(step.get(node, 0.0)) for step in v_c_history_before]
        after_series = [float(step.get(node, 0.0)) for step in v_c_history_after]

        ax.plot(
            x_before,
            before_series,
            color=palette[idx],
            linewidth=2.0,
            label=f"{label} - Pre-ATMS",
        )
        ax.plot(
            x_after,
            after_series,
            color=palette[idx],
            linewidth=2.0,
            linestyle="--",
            label=f"{label} - Post-ATMS",
        )

    ax.axhline(0.85, color="#f39c12", linestyle="--", linewidth=1.5, label="Saturation Threshold (0.85)")
    ax.axhline(1.00, color="#e74c3c", linestyle="--", linewidth=1.5, label="Over-Capacity Threshold (1.0)")

    xmax = max(len(v_c_history_before), len(v_c_history_after)) - 1
    ax.text(xmax, 0.86, "0.85", color="#f39c12", fontsize=9, va="bottom", ha="right")
    ax.text(xmax, 1.01, "1.0", color="#e74c3c", fontsize=9, va="bottom", ha="right")

    ax.set_xlabel("Signal Cycle (time step)")
    ax.set_ylabel("v/c Ratio")
    ax.set_title(title, fontsize=16, fontweight="bold", pad=12)
    ax.grid(True, alpha=0.28)
    ax.legend(
        fontsize=8,
        ncol=2,
        framealpha=0.85,
        facecolor="#161b22",
        edgecolor="#30363d",
        loc="upper right",
    )

    fig.tight_layout()
    return _save_fig(fig, filename)


def generate_all_plots(
    G,
    sim_before,
    sim_after,
    T_before,
    T_after,
    node_list,
    pi_before,
    pi_after,
    mfpt_before,
    mfpt_after,
):
    """Generate full traffic analysis plot suite in outputs/."""
    from src.graph_model import get_adjacency_matrix

    print("\n" + "=" * 60)
    print("  GENERATING TRAFFIC ANALYSIS VISUALS")
    print("=" * 60)

    plot_graph(G, title="Road Network - Intersection Graph")

    adjacency, _ = get_adjacency_matrix(G)
    plot_adjacency_matrix(adjacency, node_list, G)

    plot_transition_matrix(
        T_before,
        node_list,
        G,
        title="Vehicle Routing Probability Matrix - Pre-ATMS Intervention",
        filename="04a_transition_original.png",
    )
    plot_transition_matrix(
        T_after,
        node_list,
        G,
        title="Vehicle Routing Probability Matrix - Post-ATMS Signal Optimization",
        filename="04b_transition_optimized.png",
    )

    plot_density_heatmap(
        sim_before.history,
        node_list,
        G,
        title="Vehicle Density Heatmap - Pre-ATMS Intervention",
        filename="02a_density_before.png",
    )
    plot_density_heatmap(
        sim_after.history,
        node_list,
        G,
        title="Vehicle Density Heatmap - Post-ATMS Signal Optimization",
        filename="02b_density_after.png",
    )

    plot_distribution_evolution(
        sim_before.history,
        node_list,
        G,
        title="Vehicle Density Evolution - Pre-ATMS Intervention",
        filename="03a_evolution_before.png",
    )
    plot_distribution_evolution(
        sim_after.history,
        node_list,
        G,
        title="Vehicle Density Evolution - Post-ATMS Signal Optimization",
        filename="03b_evolution_after.png",
    )

    plot_stationary_distribution(
        pi_before,
        node_list,
        G,
        title="Long-Run Intersection Utilization - Pre-ATMS Intervention",
        filename="05a_stationary_before.png",
    )
    plot_stationary_distribution(
        pi_after,
        node_list,
        G,
        title="Long-Run Intersection Utilization - Post-ATMS Signal Optimization",
        filename="05b_stationary_after.png",
    )

    plot_comparison(sim_before.history, sim_after.history, node_list, G)
    plot_comparison_bars(pi_before, pi_after, node_list, G)

    plot_mfpt(
        mfpt_before,
        mfpt_after,
        node_list,
        G,
        title="Average Network Travel Time (Signal Cycles)",
        filename="08_mfpt.png",
    )

    plot_congestion_timeline(
        sim_before.v_c_history,
        node_list,
        G,
        title="Saturated Intersection Timeline - Pre-ATMS Intervention",
        filename="09a_congestion_before.png",
    )
    plot_congestion_timeline(
        sim_after.v_c_history,
        node_list,
        G,
        title="Saturated Intersection Timeline - Post-ATMS Signal Optimization",
        filename="09b_congestion_after.png",
    )

    plot_graph_snapshots(G, sim_before.history, node_list, filename="10a_snapshots_before.png")
    plot_graph_snapshots(G, sim_after.history, node_list, filename="10b_snapshots_after.png")

    plot_v_c_ratio_timeline(
        sim_before.v_c_history,
        sim_after.v_c_history,
        node_list,
        G,
        filename="v_c_ratio_timeline.png",
    )

    print("\n  All plots generated in outputs/")
    print("=" * 60)
