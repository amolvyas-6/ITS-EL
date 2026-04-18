"""
optimization.py — Flow Optimization Module

Modifies transition probabilities to:
  1. Reduce congestion at bottleneck nodes
  2. Improve overall flow toward exits
  3. Balance load across parallel paths

Optimization strategies:
  - Bottleneck relief: Redistribute probability away from congested nodes
  - Exit acceleration: Increase probability of exit-ward transitions
  - Path splitting: Balance flow across parallel corridors
  - Combined: Apply all strategies together

Each strategy produces a new transition matrix that can be compared
with the original using the simulation engine.
"""

import numpy as np
import networkx as nx
from src.markov_model import (
    build_transition_matrix_biased,
    compute_stationary_distribution,
    validate_transition_matrix,
    compute_exit_distances,
)


def identify_bottlenecks(sim, top_k=3):
    """
    Identify the top-k bottleneck nodes from simulation results.

    A bottleneck is a node with consistently high density across time.

    Args:
        sim: A completed CrowdSimulation object.
        top_k (int): Number of bottlenecks to return.

    Returns:
        bottlenecks (list of dict): Top bottleneck nodes with metadata.
    """
    flow = sim.compute_total_flow_through()
    peaks = sim.get_peak_congestion_over_time()

    # Score = total flow × peak density
    scores = {}
    for node in sim.node_list:
        ntype = sim.G.nodes[node]['node_type']
        if ntype in ('exit', 'entrance'):
            continue  # Skip terminal nodes
        total_flow = flow[node]
        peak_density, peak_t = peaks[node]
        scores[node] = total_flow * peak_density

    sorted_nodes = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    bottlenecks = []
    for node, score in sorted_nodes[:top_k]:
        bottlenecks.append({
            'node_id': node,
            'label': sim.labels[node],
            'type': sim.G.nodes[node]['node_type'],
            'score': score,
            'peak_density': peaks[node][0],
            'peak_timestep': peaks[node][1],
            'total_flow': flow[node],
        })

    return bottlenecks


def optimize_bottleneck_relief(G, T_original, node_list, bottleneck_nodes,
                                relief_factor=0.5):
    """
    Reduce transition probability INTO bottleneck nodes.

    For each node that transitions into a bottleneck, redistribute some
    probability to other non-bottleneck neighbours.

    Args:
        G: Station graph.
        T_original: Original transition matrix.
        node_list: Ordered node IDs.
        bottleneck_nodes (list): Node IDs identified as bottlenecks.
        relief_factor (float): Fraction of probability to redistribute
            (0 = no change, 1 = avoid bottleneck entirely).

    Returns:
        T_opt (np.ndarray): Optimized transition matrix.
    """
    T_opt = T_original.copy()
    n = len(node_list)

    bottleneck_indices = [node_list.index(b) for b in bottleneck_nodes]

    for i in range(n):
        node = node_list[i]
        if G.nodes[node]['node_type'] == 'exit':
            continue

        # Find transitions to bottleneck nodes
        bottleneck_prob = 0.0
        non_bottleneck_indices = []

        for j in range(n):
            if T_opt[i][j] > 1e-8:
                if j in bottleneck_indices and j != i:
                    bottleneck_prob += T_opt[i][j]
                elif j != i:
                    non_bottleneck_indices.append(j)

        if bottleneck_prob < 1e-8 or len(non_bottleneck_indices) == 0:
            continue

        # Redistribute
        relief_amount = bottleneck_prob * relief_factor
        bonus_per_node = relief_amount / len(non_bottleneck_indices)

        for j in bottleneck_indices:
            if T_opt[i][j] > 1e-8 and j != i:
                T_opt[i][j] *= (1 - relief_factor)

        for j in non_bottleneck_indices:
            T_opt[i][j] += bonus_per_node

    # Re-normalize rows
    for i in range(n):
        row_sum = T_opt[i].sum()
        if row_sum > 0:
            T_opt[i] /= row_sum

    validate_transition_matrix(T_opt, "T_bottleneck_relief")
    return T_opt


def optimize_exit_acceleration(G, T_original, node_list, accel_factor=1.5):
    """
    Increase transition probability toward exits globally.

    Multiplies the exit-ward bias by an acceleration factor.

    Args:
        G: Station graph.
        T_original: Original transition matrix.
        node_list: Ordered node IDs.
        accel_factor (float): Multiplier for exit-seeking behavior.

    Returns:
        T_opt (np.ndarray): Optimized transition matrix.
    """
    # Rebuild with stronger exit bias
    T_opt, _ = build_transition_matrix_biased(
        G,
        exit_bias=2.0 * accel_factor,
        self_loop_factor=0.05  # Reduce loitering
    )
    validate_transition_matrix(T_opt, "T_exit_accel")
    return T_opt


def optimize_path_splitting(G, T_original, node_list):
    """
    Balance flow across parallel paths.

    When a node has multiple neighbours leading toward exits, equalize
    the probabilities more to prevent one path from getting overloaded.

    Args:
        G: Station graph.
        T_original: Original transition matrix.
        node_list: Ordered node IDs.

    Returns:
        T_opt (np.ndarray): Optimized transition matrix.
    """
    T_opt = T_original.copy()
    n = len(node_list)

    exit_nodes = [nd for nd in G.nodes() if G.nodes[nd]['node_type'] == 'exit']
    dist_to_exit = compute_exit_distances(G, exit_nodes)

    for i in range(n):
        node = node_list[i]
        if G.nodes[node]['node_type'] == 'exit':
            continue

        # Group neighbours by their distance bucket to exit
        neighbours = list(G.neighbors(node))
        forward_neighbours = []
        other_neighbours = []

        my_dist = dist_to_exit.get(node, float('inf'))

        for nb in neighbours:
            nb_dist = dist_to_exit.get(nb, float('inf'))
            j = node_list.index(nb)
            if nb_dist < my_dist:
                forward_neighbours.append(j)
            else:
                other_neighbours.append(j)

        if len(forward_neighbours) <= 1:
            continue  # Nothing to balance

        # Equalize forward-neighbour probabilities
        total_forward_prob = sum(T_opt[i][j] for j in forward_neighbours)
        equal_prob = total_forward_prob / len(forward_neighbours)

        # Blend: 70% equalized + 30% original
        blend = 0.7
        for j in forward_neighbours:
            T_opt[i][j] = blend * equal_prob + (1 - blend) * T_opt[i][j]

    # Re-normalize rows
    for i in range(n):
        row_sum = T_opt[i].sum()
        if row_sum > 0:
            T_opt[i] /= row_sum

    validate_transition_matrix(T_opt, "T_path_split")
    return T_opt


def optimize_combined(G, T_original, node_list, bottleneck_nodes,
                       relief_factor=0.4, accel_factor=1.3):
    """
    Apply all optimization strategies in sequence.

    1. Exit acceleration (rebuild with stronger bias)
    2. Bottleneck relief
    3. Path splitting

    Args:
        G: Station graph.
        T_original: Original transition matrix.
        node_list: Ordered node IDs.
        bottleneck_nodes: Identified bottleneck node IDs.
        relief_factor: Bottleneck relief strength.
        accel_factor: Exit acceleration strength.

    Returns:
        T_opt (np.ndarray): Fully optimized transition matrix.
    """
    print("\n  Applying combined optimization...")

    # Step 1: Exit acceleration
    T1 = optimize_exit_acceleration(G, T_original, node_list, accel_factor)
    print("    ✓ Exit acceleration applied")

    # Step 2: Bottleneck relief
    T2 = optimize_bottleneck_relief(G, T1, node_list, bottleneck_nodes,
                                     relief_factor)
    print("    ✓ Bottleneck relief applied")

    # Step 3: Path splitting
    T3 = optimize_path_splitting(G, T2, node_list)
    print("    ✓ Path splitting applied")

    return T3


def compare_distributions(pi_before, pi_after, node_list, labels,
                           title="Optimization Comparison"):
    """
    Compare two stationary distributions and print improvements.

    Args:
        pi_before: Stationary distribution before optimization.
        pi_after: Stationary distribution after optimization.
        node_list: Ordered node IDs.
        labels: Dict of node_id → label.
        title: Title for the comparison.

    Returns:
        improvements (dict): node_id → (before, after, change%).
    """
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")
    print(f"\n  {'Node':<22s} {'Before':>8s} {'After':>8s} {'Change':>10s}")
    print(f"  {'─' * 50}")

    improvements = {}
    for i, node in enumerate(node_list):
        before = pi_before[i]
        after = pi_after[i]
        if before > 1e-8:
            change_pct = ((after - before) / before) * 100
        else:
            change_pct = 0.0

        improvements[node] = (before, after, change_pct)

        marker = ""
        if abs(change_pct) > 5:
            marker = " ▼" if change_pct < 0 else " ▲"

        print(f"  {labels.get(node, f'Node {node}'):<22s} "
              f"{before:>8.4f} {after:>8.4f} {change_pct:>+8.1f}%{marker}")

    print(f"\n{'=' * 60}")
    return improvements


def print_optimization_report(bottlenecks, sim_before, sim_after, node_list, labels):
    """Print a comprehensive optimization report."""
    print("\n" + "═" * 60)
    print("  OPTIMIZATION REPORT")
    print("═" * 60)

    print("\n  Identified Bottlenecks:")
    for b in bottlenecks:
        print(f"    ⚠ {b['label']:20s}  score={b['score']:.4f}  "
              f"peak={b['peak_density']:.4f} at t={b['peak_timestep']}")

    # Compare convergence speed
    conv_before = sim_before.compute_convergence()
    conv_after = sim_after.compute_convergence()
    print(f"\n  Convergence Speed:")
    print(f"    Before: {'step ' + str(conv_before) if conv_before else 'not converged'}")
    print(f"    After:  {'step ' + str(conv_after) if conv_after else 'not converged'}")

    # Compare peak congestion
    peaks_before = sim_before.get_peak_congestion_over_time()
    peaks_after = sim_after.get_peak_congestion_over_time()

    print(f"\n  Peak Congestion Changes:")
    for b in bottlenecks:
        node = b['node_id']
        pb = peaks_before[node][0]
        pa = peaks_after[node][0]
        reduction = ((pb - pa) / pb) * 100 if pb > 1e-8 else 0
        print(f"    {b['label']:20s}: {pb:.4f} → {pa:.4f}  "
              f"({reduction:+.1f}% reduction)")

    print("\n" + "═" * 60)


if __name__ == "__main__":
    from src.graph_model import build_graph
    from src.markov_model import build_transition_matrix_biased
    from src.simulation import run_scenario

    G = build_graph()
    T_orig, node_list = build_transition_matrix_biased(G)

    sim_orig = run_scenario(G, T_orig, node_list, label="Original")
    bottlenecks = identify_bottlenecks(sim_orig)

    T_opt = optimize_combined(
        G, T_orig, node_list,
        [b['node_id'] for b in bottlenecks]
    )

    sim_opt = run_scenario(G, T_opt, node_list, label="Optimized")

    labels = {n: G.nodes[n]['label'] for n in G.nodes()}
    pi_before = compute_stationary_distribution(T_orig)
    pi_after = compute_stationary_distribution(T_opt)
    compare_distributions(pi_before, pi_after, node_list, labels)
