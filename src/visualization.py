"""
visualization.py — Plotting & Visualization Module

Generates all plots for the project:
  1. Station graph (nodes colored by type, edges with labels)
  2. Heatmap of crowd density over time
  3. Animation frames of crowd distribution evolution
  4. Before vs After optimization comparison
  5. Transition matrix heatmap
  6. Stationary distribution bar chart
  7. Mean first passage time visualization
  8. Congestion timeline

All plots are saved to the outputs/ directory.
"""

import os
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.patches import FancyBboxPatch
import matplotlib.patheffects as pe
import networkx as nx
import seaborn as sns

# ─── Style Configuration ────────────────────────────────────────────────────

plt.rcParams.update({
    'figure.facecolor': '#0d1117',
    'axes.facecolor': '#161b22',
    'axes.edgecolor': '#30363d',
    'axes.labelcolor': '#c9d1d9',
    'xtick.color': '#8b949e',
    'ytick.color': '#8b949e',
    'text.color': '#c9d1d9',
    'font.family': 'sans-serif',
    'font.size': 10,
    'axes.titlesize': 14,
    'axes.labelsize': 11,
    'figure.titlesize': 16,
    'grid.color': '#21262d',
    'grid.alpha': 0.5,
})

# Node type → color mapping
NODE_COLORS = {
    'entrance': '#58a6ff',   # Blue
    'exit':     '#3fb950',   # Green
    'gate':     '#d29922',   # Yellow/Gold
    'corridor': '#8b949e',   # Gray
    'platform': '#f85149',   # Red
}

# Create output directory
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'outputs')
os.makedirs(OUTPUT_DIR, exist_ok=True)


def _save_fig(fig, filename):
    """Save figure to outputs directory."""
    path = os.path.join(OUTPUT_DIR, filename)
    fig.savefig(path, dpi=150, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"  📊 Saved: {path}")
    return path


# ═══════════════════════════════════════════════════════════════════════════
# 1. GRAPH VISUALIZATION
# ═══════════════════════════════════════════════════════════════════════════

def plot_graph(G, title="Metro Station Graph", filename="01_graph.png",
               highlight_nodes=None, density=None):
    """
    Draw the metro station graph with nodes colored by type.

    Args:
        G: NetworkX graph.
        title: Plot title.
        filename: Output filename.
        highlight_nodes: Optional dict node_id → color for highlighting.
        density: Optional array of densities to size nodes.
    """
    fig, ax = plt.subplots(1, 1, figsize=(14, 8))

    pos = nx.get_node_attributes(G, 'pos')
    labels = nx.get_node_attributes(G, 'label')
    types = nx.get_node_attributes(G, 'node_type')

    # Node colors
    node_colors = [NODE_COLORS.get(types.get(n, 'corridor'), '#8b949e')
                   for n in G.nodes()]

    # Node sizes (based on density if provided)
    if density is not None:
        node_sizes = 300 + density * 3000
    else:
        node_sizes = [500 if types.get(n) in ('entrance', 'exit') else 400
                      for n in G.nodes()]

    # Draw edges
    nx.draw_networkx_edges(G, pos, ax=ax,
                           edge_color='#30363d',
                           width=2, alpha=0.7,
                           style='solid')

    # Draw edge weight labels
    edge_labels = nx.get_edge_attributes(G, 'weight')
    edge_labels = {k: f"{v:.1f}" for k, v in edge_labels.items()}
    nx.draw_networkx_edge_labels(G, pos, edge_labels,
                                 ax=ax, font_size=7,
                                 font_color='#484f58',
                                 bbox=dict(boxstyle='round,pad=0.1',
                                          facecolor='#0d1117',
                                          edgecolor='none', alpha=0.8))

    # Draw nodes
    if highlight_nodes:
        colors = [highlight_nodes.get(n, NODE_COLORS.get(types.get(n, 'corridor'), '#8b949e'))
                  for n in G.nodes()]
    else:
        colors = node_colors

    nx.draw_networkx_nodes(G, pos, ax=ax,
                           node_color=colors,
                           node_size=node_sizes,
                           edgecolors='#30363d',
                           linewidths=2)

    # Draw labels
    short_labels = {}
    for n, label in labels.items():
        # Shorten labels for display
        parts = label.split()
        if len(parts) > 2:
            short_labels[n] = parts[0][:3] + " " + " ".join(parts[1:])
        else:
            short_labels[n] = label

    nx.draw_networkx_labels(G, pos, short_labels, ax=ax,
                            font_size=7, font_weight='bold',
                            font_color='white')

    # Node ID labels (small)
    id_pos = {n: (x, y - 0.35) for n, (x, y) in pos.items()}
    id_labels = {n: f"[{n}]" for n in G.nodes()}
    nx.draw_networkx_labels(G, id_pos, id_labels, ax=ax,
                            font_size=6, font_color='#484f58')

    # Legend
    legend_elements = []
    for ntype, color in NODE_COLORS.items():
        legend_elements.append(
            plt.scatter([], [], c=color, s=100, label=ntype.capitalize(),
                       edgecolors='#30363d', linewidths=1.5)
        )
    ax.legend(handles=legend_elements, loc='upper left',
              framealpha=0.8, facecolor='#161b22', edgecolor='#30363d',
              fontsize=9)

    ax.set_title(title, fontsize=16, fontweight='bold', pad=15)
    ax.set_xlim(-0.5, 13.0)
    ax.set_ylim(0.5, 9.5)
    ax.set_aspect('equal')
    ax.axis('off')

    return _save_fig(fig, filename)


# ═══════════════════════════════════════════════════════════════════════════
# 2. CROWD DENSITY HEATMAP
# ═══════════════════════════════════════════════════════════════════════════

def plot_density_heatmap(history, node_list, G,
                          title="Crowd Density Over Time",
                          filename="02_density_heatmap.png"):
    """
    Plot a heatmap showing crowd density at each node across time steps.

    Args:
        history: Array of shape (T+1, n_nodes) — distribution over time.
        node_list: Ordered node IDs.
        G: Station graph (for labels).
        title: Plot title.
        filename: Output filename.
    """
    fig, ax = plt.subplots(1, 1, figsize=(16, 8))

    labels = [G.nodes[n]['label'] for n in node_list]
    H = np.array(history)

    # Custom colormap: dark blue → orange → bright yellow
    cmap = sns.color_palette("rocket_r", as_cmap=True)

    im = ax.imshow(H.T, aspect='auto', cmap=cmap, interpolation='nearest')

    ax.set_xlabel("Time Step", fontsize=12)
    ax.set_ylabel("Location", fontsize=12)
    ax.set_title(title, fontsize=16, fontweight='bold', pad=15)

    # Y-axis: node labels
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels, fontsize=8)

    # X-axis: time steps
    n_steps = H.shape[0]
    step_ticks = list(range(0, n_steps, max(1, n_steps // 10)))
    ax.set_xticks(step_ticks)
    ax.set_xticklabels([f"t={t}" for t in step_ticks])

    # Colorbar
    cbar = fig.colorbar(im, ax=ax, shrink=0.8, pad=0.02)
    cbar.set_label("Crowd Density (probability)", fontsize=10)
    cbar.ax.yaxis.set_tick_params(color='#8b949e')

    # Annotate high density cells
    threshold = H.max() * 0.5
    for t in range(H.shape[0]):
        for j in range(H.shape[1]):
            if H[t, j] > threshold:
                ax.text(t, j, f"{H[t, j]:.2f}", ha='center', va='center',
                       fontsize=6, color='white', fontweight='bold')

    fig.tight_layout()
    return _save_fig(fig, filename)


# ═══════════════════════════════════════════════════════════════════════════
# 3. DISTRIBUTION EVOLUTION
# ═══════════════════════════════════════════════════════════════════════════

def plot_distribution_evolution(history, node_list, G,
                                 title="Crowd Distribution Evolution",
                                 filename="03_evolution.png"):
    """
    Plot how the crowd distribution evolves over time (line plot per node).

    Args:
        history: Array of shape (T+1, n_nodes).
        node_list: Ordered node IDs.
        G: Station graph.
        title: Plot title.
        filename: Output filename.
    """
    fig, axes = plt.subplots(2, 1, figsize=(14, 10), height_ratios=[3, 1])
    H = np.array(history)
    labels = {n: G.nodes[n]['label'] for n in G.nodes()}
    types = {n: G.nodes[n]['node_type'] for n in G.nodes()}

    time_steps = np.arange(H.shape[0])

    # ─── Top: All nodes ───
    ax = axes[0]
    for i, node in enumerate(node_list):
        ntype = types[node]
        color = NODE_COLORS.get(ntype, '#8b949e')
        alpha = 1.0 if ntype in ('corridor', 'platform') else 0.6
        lw = 2.5 if max(H[:, i]) > 0.05 else 1.0
        ax.plot(time_steps, H[:, i], color=color, alpha=alpha,
                linewidth=lw, label=labels[node])

    ax.set_xlabel("Time Step")
    ax.set_ylabel("Crowd Density (probability)")
    ax.set_title(title, fontsize=16, fontweight='bold')
    ax.legend(loc='upper right', ncol=3, fontsize=7,
              framealpha=0.8, facecolor='#161b22', edgecolor='#30363d')
    ax.set_xlim(0, H.shape[0] - 1)
    ax.set_ylim(0, None)
    ax.grid(True, alpha=0.3)

    # ─── Bottom: Stacked area for key nodes ───
    ax2 = axes[1]
    # Show only non-terminal nodes with significant density
    key_indices = []
    key_labels = []
    key_colors = []
    for i, node in enumerate(node_list):
        if types[node] not in ('entrance',):
            if H[:, i].max() > 0.01:
                key_indices.append(i)
                key_labels.append(labels[node])
                key_colors.append(NODE_COLORS.get(types[node], '#8b949e'))

    if key_indices:
        ax2.stackplot(time_steps, *[H[:, i] for i in key_indices],
                      labels=key_labels, colors=key_colors, alpha=0.7)
        ax2.set_xlabel("Time Step")
        ax2.set_ylabel("Cumulative Density")
        ax2.set_title("Stacked Crowd Distribution", fontsize=12)
        ax2.legend(loc='upper right', ncol=3, fontsize=6,
                   framealpha=0.8, facecolor='#161b22', edgecolor='#30363d')
        ax2.set_xlim(0, H.shape[0] - 1)
        ax2.grid(True, alpha=0.3)

    fig.tight_layout()
    return _save_fig(fig, filename)


# ═══════════════════════════════════════════════════════════════════════════
# 4. TRANSITION MATRIX HEATMAP
# ═══════════════════════════════════════════════════════════════════════════

def plot_transition_matrix(T, node_list, G,
                            title="Transition Matrix",
                            filename="04_transition_matrix.png"):
    """
    Plot the transition matrix as a heatmap.

    Args:
        T: Transition matrix (n × n).
        node_list: Ordered node IDs.
        G: Station graph (for labels).
        title: Plot title.
        filename: Output filename.
    """
    fig, ax = plt.subplots(1, 1, figsize=(12, 10))

    labels = [G.nodes[n]['label'][:15] for n in node_list]

    cmap = sns.color_palette("viridis", as_cmap=True)
    im = ax.imshow(T, cmap=cmap, vmin=0, vmax=T.max())

    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=45, ha='right', fontsize=7)
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels, fontsize=7)

    ax.set_xlabel("To (destination)")
    ax.set_ylabel("From (source)")
    ax.set_title(title, fontsize=16, fontweight='bold', pad=15)

    # Annotate cells
    for i in range(T.shape[0]):
        for j in range(T.shape[1]):
            if T[i, j] > 0.01:
                color = 'white' if T[i, j] > T.max() / 2 else '#c9d1d9'
                ax.text(j, i, f"{T[i, j]:.2f}", ha='center', va='center',
                       fontsize=6, color=color)

    cbar = fig.colorbar(im, ax=ax, shrink=0.8)
    cbar.set_label("Transition Probability")

    fig.tight_layout()
    return _save_fig(fig, filename)


# ═══════════════════════════════════════════════════════════════════════════
# 5. STATIONARY DISTRIBUTION
# ═══════════════════════════════════════════════════════════════════════════

def plot_stationary_distribution(pi, node_list, G,
                                  title="Stationary Distribution",
                                  filename="05_stationary.png"):
    """
    Bar chart of the stationary distribution.

    Args:
        pi: Stationary distribution vector.
        node_list: Ordered node IDs.
        G: Station graph.
        title: Plot title.
        filename: Output filename.
    """
    fig, ax = plt.subplots(1, 1, figsize=(14, 6))

    labels = [G.nodes[n]['label'] for n in node_list]
    types = [G.nodes[n]['node_type'] for n in node_list]
    colors = [NODE_COLORS.get(t, '#8b949e') for t in types]

    bars = ax.bar(range(len(pi)), pi, color=colors, edgecolor='#30363d',
                  linewidth=1, alpha=0.9)

    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=45, ha='right', fontsize=8)
    ax.set_ylabel("Stationary Probability (π)")
    ax.set_title(title, fontsize=16, fontweight='bold', pad=15)
    ax.grid(axis='y', alpha=0.3)

    # Annotate values
    for bar, val in zip(bars, pi):
        if val > 0.01:
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.005,
                    f"{val:.3f}", ha='center', va='bottom', fontsize=7,
                    color='#c9d1d9')

    # Legend
    legend_elements = [plt.scatter([], [], c=c, s=80, label=t.capitalize(),
                                   edgecolors='#30363d')
                       for t, c in NODE_COLORS.items()]
    ax.legend(handles=legend_elements, loc='upper right', fontsize=8,
              framealpha=0.8, facecolor='#161b22', edgecolor='#30363d')

    fig.tight_layout()
    return _save_fig(fig, filename)


# ═══════════════════════════════════════════════════════════════════════════
# 6. BEFORE vs AFTER COMPARISON
# ═══════════════════════════════════════════════════════════════════════════

def plot_comparison(history_before, history_after, node_list, G,
                     title="Before vs After Optimization",
                     filename="06_comparison.png"):
    """
    Side-by-side comparison of crowd density before and after optimization.

    Args:
        history_before: Distribution history before optimization.
        history_after: Distribution history after optimization.
        node_list: Ordered node IDs.
        G: Station graph.
        title: Plot title.
        filename: Output filename.
    """
    fig, axes = plt.subplots(1, 2, figsize=(18, 8))

    labels = [G.nodes[n]['label'] for n in node_list]
    cmap = sns.color_palette("rocket_r", as_cmap=True)

    H1 = np.array(history_before)
    H2 = np.array(history_after)

    vmax = max(H1.max(), H2.max())

    # Before
    ax = axes[0]
    im1 = ax.imshow(H1.T, aspect='auto', cmap=cmap, vmin=0, vmax=vmax)
    ax.set_title("BEFORE Optimization", fontsize=14, fontweight='bold',
                 color='#f85149')
    ax.set_xlabel("Time Step")
    ax.set_ylabel("Location")
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels, fontsize=7)

    # After
    ax = axes[1]
    im2 = ax.imshow(H2.T, aspect='auto', cmap=cmap, vmin=0, vmax=vmax)
    ax.set_title("AFTER Optimization", fontsize=14, fontweight='bold',
                 color='#3fb950')
    ax.set_xlabel("Time Step")
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels, fontsize=7)

    fig.colorbar(im2, ax=axes, shrink=0.6, pad=0.02,
                 label="Crowd Density")

    fig.suptitle(title, fontsize=16, fontweight='bold', y=1.02)
    fig.tight_layout()
    return _save_fig(fig, filename)


def plot_comparison_bars(pi_before, pi_after, node_list, G,
                          title="Stationary Distribution — Before vs After",
                          filename="07_comparison_bars.png"):
    """
    Grouped bar chart comparing stationary distributions.

    Args:
        pi_before: Stationary distribution before optimization.
        pi_after: Stationary distribution after optimization.
        node_list: Ordered node IDs.
        G: Station graph.
        title: Plot title.
        filename: Output filename.
    """
    fig, ax = plt.subplots(1, 1, figsize=(14, 6))

    labels = [G.nodes[n]['label'] for n in node_list]
    x = np.arange(len(labels))
    width = 0.35

    bars1 = ax.bar(x - width / 2, pi_before, width,
                   label='Before', color='#f85149', alpha=0.8,
                   edgecolor='#30363d')
    bars2 = ax.bar(x + width / 2, pi_after, width,
                   label='After', color='#3fb950', alpha=0.8,
                   edgecolor='#30363d')

    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=45, ha='right', fontsize=8)
    ax.set_ylabel("Stationary Probability (π)")
    ax.set_title(title, fontsize=16, fontweight='bold', pad=15)
    ax.legend(fontsize=10, framealpha=0.8, facecolor='#161b22',
              edgecolor='#30363d')
    ax.grid(axis='y', alpha=0.3)

    # Annotate percentage change
    for i in range(len(pi_before)):
        if pi_before[i] > 1e-4:
            change = ((pi_after[i] - pi_before[i]) / pi_before[i]) * 100
            if abs(change) > 5:
                color = '#3fb950' if change < 0 else '#f85149'
                ax.text(x[i], max(pi_before[i], pi_after[i]) + 0.005,
                        f"{change:+.0f}%", ha='center', fontsize=7,
                        color=color, fontweight='bold')

    fig.tight_layout()
    return _save_fig(fig, filename)


# ═══════════════════════════════════════════════════════════════════════════
# 7. MEAN FIRST PASSAGE TIME
# ═══════════════════════════════════════════════════════════════════════════

def plot_mfpt(mfpt_before, mfpt_after, node_list, G,
               title="Mean Steps to Exit — Before vs After",
               filename="08_mfpt.png"):
    """
    Bar chart of mean first passage time to exits.

    Args:
        mfpt_before: Dict node_id → steps (before optimization).
        mfpt_after: Dict node_id → steps (after optimization).
        node_list: Ordered node IDs.
        G: Station graph.
        title: Plot title.
        filename: Output filename.
    """
    fig, ax = plt.subplots(1, 1, figsize=(14, 6))

    labels = [G.nodes[n]['label'] for n in node_list]
    before_vals = [mfpt_before.get(n, 0) for n in node_list]
    after_vals = [mfpt_after.get(n, 0) for n in node_list]

    x = np.arange(len(labels))
    width = 0.35

    ax.barh(x - width / 2, before_vals, width,
            label='Before', color='#f85149', alpha=0.8, edgecolor='#30363d')
    ax.barh(x + width / 2, after_vals, width,
            label='After', color='#3fb950', alpha=0.8, edgecolor='#30363d')

    ax.set_yticks(x)
    ax.set_yticklabels(labels, fontsize=8)
    ax.set_xlabel("Expected Steps to Reach Exit")
    ax.set_title(title, fontsize=16, fontweight='bold', pad=15)
    ax.legend(fontsize=10, framealpha=0.8, facecolor='#161b22',
              edgecolor='#30363d')
    ax.grid(axis='x', alpha=0.3)
    ax.invert_yaxis()

    fig.tight_layout()
    return _save_fig(fig, filename)


# ═══════════════════════════════════════════════════════════════════════════
# 8. CONGESTION TIMELINE
# ═══════════════════════════════════════════════════════════════════════════

def plot_congestion_timeline(history, node_list, G, threshold=0.15,
                              title="Congestion Timeline",
                              filename="09_congestion_timeline.png"):
    """
    Timeline showing when and where congestion occurs.

    Args:
        history: Distribution history array.
        node_list: Ordered node IDs.
        G: Station graph.
        threshold: Congestion threshold.
        title: Plot title.
        filename: Output filename.
    """
    fig, ax = plt.subplots(1, 1, figsize=(14, 6))

    H = np.array(history)
    labels = [G.nodes[n]['label'] for n in node_list]

    # Create congestion matrix (binary: above threshold or not)
    congested = (H > threshold).astype(float)

    # Plot as scatter where congested
    for t in range(H.shape[0]):
        for j in range(H.shape[1]):
            if congested[t, j]:
                size = H[t, j] * 500
                ax.scatter(t, j, s=size, c='#f85149', alpha=0.7,
                          edgecolors='#f8514960', linewidths=2)

    # Add faint lines for reference
    for j in range(H.shape[1]):
        ax.axhline(y=j, color='#21262d', linewidth=0.5)

    ax.set_xlabel("Time Step")
    ax.set_ylabel("Location")
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels, fontsize=8)
    ax.set_title(f"{title} (threshold = {threshold})",
                 fontsize=16, fontweight='bold', pad=15)
    ax.set_xlim(-0.5, H.shape[0] - 0.5)

    # Add threshold line in legend
    ax.scatter([], [], s=100, c='#f85149', alpha=0.7,
              label=f'Congested (>{threshold})', edgecolors='#f8514960')
    ax.legend(fontsize=9, framealpha=0.8, facecolor='#161b22',
              edgecolor='#30363d')

    fig.tight_layout()
    return _save_fig(fig, filename)


# ═══════════════════════════════════════════════════════════════════════════
# 9. SNAPSHOT FRAMES (for key timesteps)
# ═══════════════════════════════════════════════════════════════════════════

def plot_graph_snapshots(G, history, node_list, timesteps=None,
                          filename="10_snapshots.png"):
    """
    Show the graph at multiple timesteps with nodes sized by density.

    Args:
        G: Station graph.
        history: Distribution history.
        node_list: Ordered node IDs.
        timesteps: Which timesteps to show (default: 0, 5, 10, 15, 20).
        filename: Output filename.
    """
    H = np.array(history)
    if timesteps is None:
        max_t = H.shape[0] - 1
        timesteps = [0, max_t // 4, max_t // 2, 3 * max_t // 4, max_t]
        timesteps = sorted(set(timesteps))

    n_plots = len(timesteps)
    fig, axes = plt.subplots(1, n_plots, figsize=(5 * n_plots, 6))
    if n_plots == 1:
        axes = [axes]

    pos = nx.get_node_attributes(G, 'pos')
    types = nx.get_node_attributes(G, 'node_type')
    node_labels = nx.get_node_attributes(G, 'label')

    for idx, t in enumerate(timesteps):
        ax = axes[idx]
        density = H[t]

        # Size nodes by density
        sizes = 200 + density * 4000

        # Color nodes by density (blend type color with red for congestion)
        colors = []
        for i, node in enumerate(node_list):
            base_color = NODE_COLORS.get(types.get(node, 'corridor'), '#8b949e')
            if density[i] > 0.15:
                colors.append('#f85149')  # Red for congested
            elif density[i] > 0.05:
                colors.append('#d29922')  # Yellow for moderate
            else:
                colors.append(base_color)

        nx.draw_networkx_edges(G, pos, ax=ax,
                               edge_color='#30363d', width=1.5, alpha=0.5)
        nx.draw_networkx_nodes(G, pos, ax=ax,
                               node_color=colors, node_size=sizes,
                               edgecolors='#30363d', linewidths=1.5,
                               alpha=0.9)

        # Show density values on nodes
        for i, node in enumerate(node_list):
            if density[i] > 0.01:
                x, y = pos[node]
                ax.text(x, y, f"{density[i]:.2f}", ha='center', va='center',
                       fontsize=6, color='white', fontweight='bold',
                       path_effects=[pe.withStroke(linewidth=2, foreground='black')])

        ax.set_title(f"t = {t}", fontsize=12, fontweight='bold')
        ax.axis('off')
        ax.set_xlim(-0.5, 13.0)
        ax.set_ylim(0.5, 9.5)

    fig.suptitle("Crowd Distribution Snapshots", fontsize=16,
                 fontweight='bold', y=1.02)
    fig.tight_layout()
    return _save_fig(fig, filename)


# ═══════════════════════════════════════════════════════════════════════════
# 10. ADJACENCY + WEIGHT MATRIX VISUALIZATION
# ═══════════════════════════════════════════════════════════════════════════

def plot_adjacency_matrix(A, node_list, G,
                           title="Adjacency Matrix",
                           filename="11_adjacency_matrix.png"):
    """
    Plot the adjacency matrix as a heatmap.
    """
    fig, ax = plt.subplots(1, 1, figsize=(10, 8))
    labels = [G.nodes[n]['label'][:12] for n in node_list]

    cmap = sns.color_palette("YlOrRd", as_cmap=True)
    im = ax.imshow(A, cmap=cmap)

    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=45, ha='right', fontsize=7)
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels, fontsize=7)
    ax.set_title(title, fontsize=16, fontweight='bold', pad=15)

    for i in range(A.shape[0]):
        for j in range(A.shape[1]):
            if A[i, j] > 0:
                ax.text(j, i, f"{A[i,j]:.0f}", ha='center', va='center',
                       fontsize=7, color='white' if A[i,j] > 0.5 else '#c9d1d9')

    fig.colorbar(im, ax=ax, shrink=0.8)
    fig.tight_layout()
    return _save_fig(fig, filename)


# ═══════════════════════════════════════════════════════════════════════════
# MASTER PLOT FUNCTION
# ═══════════════════════════════════════════════════════════════════════════

def generate_all_plots(G, sim_before, sim_after, T_before, T_after,
                        node_list, pi_before, pi_after,
                        mfpt_before, mfpt_after):
    """
    Generate all visualization plots for the project.

    Args:
        G: Station graph.
        sim_before: Simulation before optimization.
        sim_after: Simulation after optimization.
        T_before: Transition matrix before.
        T_after: Transition matrix after.
        node_list: Ordered node IDs.
        pi_before: Stationary distribution before.
        pi_after: Stationary distribution after.
        mfpt_before: MFPT before.
        mfpt_after: MFPT after.
    """
    from src.graph_model import get_adjacency_matrix

    print("\n" + "═" * 60)
    print("  GENERATING VISUALIZATIONS")
    print("═" * 60)

    # 1. Graph
    plot_graph(G, title="Metro Station — Graph Model")

    # 2. Adjacency matrix
    A, _ = get_adjacency_matrix(G)
    plot_adjacency_matrix(A, node_list, G)

    # 3. Transition matrix (before)
    plot_transition_matrix(T_before, node_list, G,
                           title="Transition Matrix (Original)",
                           filename="04a_transition_original.png")

    # 4. Transition matrix (after)
    plot_transition_matrix(T_after, node_list, G,
                           title="Transition Matrix (Optimized)",
                           filename="04b_transition_optimized.png")

    # 5. Density heatmap (before)
    plot_density_heatmap(sim_before.history, node_list, G,
                          title="Crowd Density — Before Optimization",
                          filename="02a_density_before.png")

    # 6. Density heatmap (after)
    plot_density_heatmap(sim_after.history, node_list, G,
                          title="Crowd Density — After Optimization",
                          filename="02b_density_after.png")

    # 7. Distribution evolution (before)
    plot_distribution_evolution(sim_before.history, node_list, G,
                                 title="Distribution Evolution — Before",
                                 filename="03a_evolution_before.png")

    # 8. Distribution evolution (after)
    plot_distribution_evolution(sim_after.history, node_list, G,
                                 title="Distribution Evolution — After",
                                 filename="03b_evolution_after.png")

    # 9. Stationary distribution (before)
    plot_stationary_distribution(pi_before, node_list, G,
                                  title="Stationary Distribution — Original",
                                  filename="05a_stationary_before.png")

    # 10. Stationary distribution (after)
    plot_stationary_distribution(pi_after, node_list, G,
                                  title="Stationary Distribution — Optimized",
                                  filename="05b_stationary_after.png")

    # 11. Side-by-side comparison
    plot_comparison(sim_before.history, sim_after.history, node_list, G)

    # 12. Comparison bars
    plot_comparison_bars(pi_before, pi_after, node_list, G)

    # 13. MFPT comparison
    plot_mfpt(mfpt_before, mfpt_after, node_list, G)

    # 14. Congestion timeline (before)
    plot_congestion_timeline(sim_before.history, node_list, G,
                              title="Congestion Timeline — Before",
                              filename="09a_congestion_before.png")

    # 15. Congestion timeline (after)
    plot_congestion_timeline(sim_after.history, node_list, G,
                              title="Congestion Timeline — After",
                              filename="09b_congestion_after.png")

    # 16. Snapshots (before)
    plot_graph_snapshots(G, sim_before.history, node_list,
                          filename="10a_snapshots_before.png")

    # 17. Snapshots (after)
    plot_graph_snapshots(G, sim_after.history, node_list,
                          filename="10b_snapshots_after.png")

    print("\n  ✅ All plots generated in outputs/ directory")
    print("═" * 60)
