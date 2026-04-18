#!/usr/bin/env python3
"""
main.py — Crowd Movement Simulation using Markov Chains & Graph Theory

Mathematical Modelling Project — Main Entry Point

This script runs the complete pipeline:
  1. Build the metro station graph
  2. Construct transition matrices (uniform + biased)
  3. Run simulation (before optimization)
  4. Identify bottlenecks
  5. Optimize transition probabilities
  6. Run simulation (after optimization)
  7. Compare results
  8. Generate all visualizations
  9. Print comprehensive report

Usage:
    python main.py
"""

import os
import sys
import numpy as np

# Ensure the project root is in the path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.graph_model import (
    build_graph,
    get_adjacency_matrix,
    get_weighted_adjacency_matrix,
    print_graph_info,
)
from src.markov_model import (
    build_transition_matrix_uniform,
    build_transition_matrix_biased,
    compute_stationary_distribution,
    compute_mean_first_passage_time,
    validate_transition_matrix,
    print_transition_matrix,
)
from src.simulation import CrowdSimulation, run_scenario
from src.optimization import (
    identify_bottlenecks,
    optimize_combined,
    compare_distributions,
    print_optimization_report,
)
from src.visualization import generate_all_plots


def main():
    print()
    print("╔" + "═" * 58 + "╗")
    print("║  CROWD MOVEMENT SIMULATION                              ║")
    print("║  Markov Chains & Graph Theory                           ║")
    print("║  Mathematical Modelling Project                         ║")
    print("╚" + "═" * 58 + "╝")
    print()

    # ══════════════════════════════════════════════════════════════════════
    # PHASE 1: Graph Construction
    # ══════════════════════════════════════════════════════════════════════
    print("\n▶ PHASE 1: Building Metro Station Graph...\n")

    G = build_graph()
    print_graph_info(G)

    # Adjacency matrix
    A, node_list = get_adjacency_matrix(G)
    print("\n  Adjacency Matrix (A):")
    print(f"  Shape: {A.shape}")
    print(f"  Non-zero entries: {int(np.sum(A > 0))}")
    print(f"  Symmetric: {np.allclose(A, A.T)}")

    # Weighted adjacency matrix
    W, _ = get_weighted_adjacency_matrix(G)
    print(f"\n  Weighted Adjacency Matrix (W):")
    print(f"  Total edge weight: {np.sum(W) / 2:.1f}")

    # ══════════════════════════════════════════════════════════════════════
    # PHASE 2: Markov Chain Model
    # ══════════════════════════════════════════════════════════════════════
    print("\n▶ PHASE 2: Building Transition Matrices...\n")

    # Uniform transition matrix
    T_uniform, _ = build_transition_matrix_uniform(G)
    validate_transition_matrix(T_uniform, "T_uniform")

    # Biased transition matrix (exit-seeking)
    T_biased, _ = build_transition_matrix_biased(G, exit_bias=2.0,
                                                   self_loop_factor=0.1)
    validate_transition_matrix(T_biased, "T_biased")

    print_transition_matrix(T_biased, node_list, G)

    # ══════════════════════════════════════════════════════════════════════
    # PHASE 3: Simulation — Before Optimization
    # ══════════════════════════════════════════════════════════════════════
    print("\n▶ PHASE 3: Running Simulation (Original)...\n")

    N_STEPS = 20

    sim_before = run_scenario(
        G, T_biased, node_list,
        n_steps=N_STEPS,
        init_mode="entrances",
        label="Original (Biased Transition)"
    )

    # ══════════════════════════════════════════════════════════════════════
    # PHASE 4: Bottleneck Analysis
    # ══════════════════════════════════════════════════════════════════════
    print("\n▶ PHASE 4: Identifying Bottlenecks...\n")

    bottlenecks = identify_bottlenecks(sim_before, top_k=3)
    print("  Top Bottleneck Nodes:")
    for b in bottlenecks:
        print(f"    ⚠ [{b['node_id']:2d}] {b['label']:20s} "
              f"score={b['score']:.4f}  peak={b['peak_density']:.4f}  "
              f"flow={b['total_flow']:.4f}")

    # ══════════════════════════════════════════════════════════════════════
    # PHASE 5: Optimization
    # ══════════════════════════════════════════════════════════════════════
    print("\n▶ PHASE 5: Optimizing Transition Probabilities...\n")

    bottleneck_ids = [b['node_id'] for b in bottlenecks]
    T_optimized = optimize_combined(
        G, T_biased, node_list,
        bottleneck_ids,
        relief_factor=0.4,
        accel_factor=1.3
    )
    validate_transition_matrix(T_optimized, "T_optimized")

    # ══════════════════════════════════════════════════════════════════════
    # PHASE 6: Simulation — After Optimization
    # ══════════════════════════════════════════════════════════════════════
    print("\n▶ PHASE 6: Running Simulation (Optimized)...\n")

    sim_after = run_scenario(
        G, T_optimized, node_list,
        n_steps=N_STEPS,
        init_mode="entrances",
        label="Optimized (Combined Strategy)"
    )

    # ══════════════════════════════════════════════════════════════════════
    # PHASE 7: Comparison Analysis
    # ══════════════════════════════════════════════════════════════════════
    print("\n▶ PHASE 7: Comparing Results...\n")

    # Stationary distributions
    pi_before = compute_stationary_distribution(T_biased)
    pi_after = compute_stationary_distribution(T_optimized)

    labels = {n: G.nodes[n]['label'] for n in G.nodes()}
    compare_distributions(pi_before, pi_after, node_list, labels,
                           title="Stationary Distribution — Before vs After")

    # Mean first passage times
    exit_nodes = [n for n in G.nodes() if G.nodes[n]['node_type'] == 'exit']
    mfpt_before = compute_mean_first_passage_time(T_biased, exit_nodes, node_list)
    mfpt_after = compute_mean_first_passage_time(T_optimized, exit_nodes, node_list)

    print("\n  Mean Steps to Exit — Comparison:")
    print(f"  {'Node':<22s} {'Before':>8s} {'After':>8s} {'Saved':>8s}")
    print(f"  {'─' * 42}")
    for node in node_list:
        before = mfpt_before.get(node, 0)
        after = mfpt_after.get(node, 0)
        saved = before - after
        if before > 0:
            print(f"  {labels[node]:<22s} {before:>8.2f} {after:>8.2f} "
                  f"{saved:>+8.2f}")

    # Full optimization report
    print_optimization_report(bottlenecks, sim_before, sim_after,
                               node_list, labels)

    # ══════════════════════════════════════════════════════════════════════
    # PHASE 8: Visualization
    # ══════════════════════════════════════════════════════════════════════
    print("\n▶ PHASE 8: Generating Visualizations...\n")

    generate_all_plots(
        G=G,
        sim_before=sim_before,
        sim_after=sim_after,
        T_before=T_biased,
        T_after=T_optimized,
        node_list=node_list,
        pi_before=pi_before,
        pi_after=pi_after,
        mfpt_before=mfpt_before,
        mfpt_after=mfpt_after,
    )

    # ══════════════════════════════════════════════════════════════════════
    # PHASE 9: Export Data for Dashboard
    # ══════════════════════════════════════════════════════════════════════
    print("\n▶ PHASE 9: Exporting Data for Dashboard...\n")

    export_dashboard_data(G, node_list, T_biased, T_optimized,
                           sim_before, sim_after,
                           pi_before, pi_after,
                           mfpt_before, mfpt_after,
                           bottlenecks)

    # ══════════════════════════════════════════════════════════════════════
    # FINAL SUMMARY
    # ══════════════════════════════════════════════════════════════════════
    print("\n")
    print("╔" + "═" * 58 + "╗")
    print("║  ✅ SIMULATION COMPLETE                                  ║")
    print("╠" + "═" * 58 + "╣")
    print("║  Outputs:                                                ║")
    print("║    • outputs/      — All visualization plots             ║")
    print("║    • dashboard/    — Interactive web dashboard            ║")
    print("║    • Console       — Full analysis report above          ║")
    print("╚" + "═" * 58 + "╝")
    print()


def export_dashboard_data(G, node_list, T_before, T_after,
                           sim_before, sim_after,
                           pi_before, pi_after,
                           mfpt_before, mfpt_after,
                           bottlenecks):
    """Export simulation data as JSON for the web dashboard."""
    import json

    data = {
        'nodes': [],
        'edges': [],
        'transition_matrix_before': T_before.tolist(),
        'transition_matrix_after': T_after.tolist(),
        'history_before': np.array(sim_before.history).tolist(),
        'history_after': np.array(sim_after.history).tolist(),
        'stationary_before': pi_before.tolist(),
        'stationary_after': pi_after.tolist(),
        'mfpt_before': {str(k): v for k, v in mfpt_before.items()},
        'mfpt_after': {str(k): v for k, v in mfpt_after.items()},
        'bottlenecks': [b['node_id'] for b in bottlenecks],
        'n_steps': len(sim_before.history) - 1,
    }

    # Nodes
    for node in node_list:
        data['nodes'].append({
            'id': node,
            'label': G.nodes[node]['label'],
            'type': G.nodes[node]['node_type'],
            'x': G.nodes[node]['pos'][0],
            'y': G.nodes[node]['pos'][1],
        })

    # Edges
    for u, v, d in G.edges(data=True):
        data['edges'].append({
            'source': u,
            'target': v,
            'weight': d.get('weight', 1.0),
        })

    # Write to dashboard directory
    dashboard_dir = os.path.join(project_root, 'dashboard')
    os.makedirs(dashboard_dir, exist_ok=True)
    json_path = os.path.join(dashboard_dir, 'simulation_data.json')

    with open(json_path, 'w') as f:
        json.dump(data, f, indent=2)

    print(f"  📦 Dashboard data exported to: {json_path}")


if __name__ == "__main__":
    main()
