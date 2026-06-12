"""Adaptive traffic signal optimization for the ORR Markov model."""

import numpy as np

from src.graph_model import ROAD_CAPACITY
from src.markov_model import compute_exit_distances, validate_transition_matrix


def identify_bottlenecks(sim, top_k=3, start_timestep=1):
    """Rank bottlenecks by operational peak v/c ratio after the initial load injection."""
    peak_vc = sim.get_peak_vc_over_time(start_timestep=start_timestep)
    flow = sim.compute_total_flow_through()

    scores = {}
    for node in sim.node_list:
        node_type = sim.G.nodes[node]["node_type"]
        if node_type == "destination_zone":
            continue
        score = peak_vc[node][0]
        scores[node] = score

    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)

    bottlenecks = []
    for node, score in ranked[:top_k]:
        bottlenecks.append(
            {
                "node_id": node,
                "label": sim.labels[node],
                "type": sim.G.nodes[node]["node_type"],
                "score": float(score),
                "peak_v_c": float(peak_vc[node][0]),
                "peak_timestep": int(peak_vc[node][1]),
                "total_flow": float(flow[node]),
            }
        )

    return bottlenecks


def _downstream_priority(G, source_node, target_node, exit_distances, coordination_factor):
    """Score downstream candidates by proximity to destinations and corridor relief value."""
    edge_data = G.get_edge_data(source_node, target_node, default={})
    travel_time = float(edge_data.get("weight", 1.0))
    exit_distance = float(exit_distances.get(target_node, travel_time))
    node_type = G.nodes[target_node]["node_type"]

    distance_score = 1.0 / (travel_time + exit_distance + 1.0)
    if node_type == "destination_zone":
        relief_score = coordination_factor * 1.5
    else:
        relief_score = coordination_factor / max(float(ROAD_CAPACITY.get(target_node, 1.0)), 1.0)

    return distance_score + relief_score


def _redistribute_probability(
    G,
    row,
    source_node,
    node_list,
    released_mass,
    exit_distances,
    coordination_factor,
    excluded_indices=None,
):
    """Redistribute released probability mass to feasible downstream alternatives."""
    if excluded_indices is None:
        excluded_indices = set()

    candidate_indices = [
        j
        for j, probability in enumerate(row)
        if j not in excluded_indices and probability > 1e-9 and G.has_edge(source_node, node_list[j])
    ]

    if not candidate_indices or released_mass <= 0:
        return False

    scores = np.array(
        [
            _downstream_priority(
                G,
                source_node,
                node_list[j],
                exit_distances,
                coordination_factor,
            )
            for j in candidate_indices
        ],
        dtype=float,
    )

    score_sum = float(scores.sum())
    if score_sum <= 0:
        return False

    scores = scores / score_sum
    for local_idx, j in enumerate(candidate_indices):
        row[j] += released_mass * scores[local_idx]

    return True


def _normalize_row(row, self_index):
    row_sum = float(row.sum())
    if row_sum <= 0:
        row[:] = 0.0
        row[self_index] = 1.0
        return row
    return row / row_sum


def optimize_combined(
    G,
    T_original,
    node_list,
    bottleneck_nodes,
    green_extension_factor=0.4,
    downstream_coordination_factor=1.3,
    **legacy_kwargs,
):
    """Apply adaptive signal timing and downstream coordination."""
    if "relief_factor" in legacy_kwargs:
        green_extension_factor = legacy_kwargs["relief_factor"]
    if "accel_factor" in legacy_kwargs:
        downstream_coordination_factor = legacy_kwargs["accel_factor"]

    print("\n  Applying adaptive signal timing optimization...")
    optimized = T_original.copy()

    index_by_node = {node: idx for idx, node in enumerate(node_list)}
    destination_nodes = {
        node
        for node in G.nodes()
        if G.nodes[node].get("node_type") == "destination_zone"
    }
    exit_distances = compute_exit_distances(G, list(destination_nodes))
    upstream_diversion_factor = 0.25 * (downstream_coordination_factor / 1.3)

    for bottleneck in bottleneck_nodes:
        if bottleneck not in index_by_node or bottleneck in destination_nodes:
            continue

        i = index_by_node[bottleneck]
        row = optimized[i].copy()

        self_loop = float(row[i])
        released_mass = self_loop * float(green_extension_factor)
        row[i] = max(0.0, self_loop - released_mass)

        redistributed = _redistribute_probability(
            G,
            row,
            bottleneck,
            node_list,
            released_mass,
            exit_distances,
            downstream_coordination_factor,
            excluded_indices={i},
        )
        if not redistributed:
            row[i] += released_mass

        optimized[i] = _normalize_row(row, i)

        for upstream_node in G.predecessors(bottleneck):
            if upstream_node in destination_nodes:
                continue

            upstream_index = index_by_node[upstream_node]
            upstream_row = optimized[upstream_index].copy()
            target_probability = float(upstream_row[i])
            if target_probability <= 1e-9:
                continue

            released_upstream_mass = target_probability * upstream_diversion_factor
            upstream_row[i] = max(0.0, target_probability - released_upstream_mass)
            redistributed = _redistribute_probability(
                G,
                upstream_row,
                upstream_node,
                node_list,
                released_upstream_mass,
                exit_distances,
                downstream_coordination_factor,
                excluded_indices={upstream_index, i},
            )
            if not redistributed:
                upstream_row[i] += released_upstream_mass

            optimized[upstream_index] = _normalize_row(upstream_row, upstream_index)

    for node in destination_nodes:
        idx = index_by_node[node]
        optimized[idx, :] = 0.0
        optimized[idx, idx] = 1.0

    validate_transition_matrix(optimized, "T_adaptive_signal")
    print("    [ok] Adaptive green extension applied")
    print("    [ok] Downstream coordination applied")
    return optimized


def compare_distributions(
    pi_before,
    pi_after,
    node_list,
    labels,
    title="Intersection Utilization Comparison",
):
    """Compare pre/post stationary utilization distributions."""
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")
    print(f"\n  {'Node':<28s} {'Before':>8s} {'After':>8s} {'Change':>10s}")
    print(f"  {'-' * 58}")

    improvements = {}
    for i, node in enumerate(node_list):
        before = float(pi_before[i])
        after = float(pi_after[i])
        change_pct = ((after - before) / before) * 100 if before > 1e-8 else 0.0

        improvements[node] = (before, after, change_pct)
        print(
            f"  {labels.get(node, f'Node {node}'):<28s} "
            f"{before:>8.4f} {after:>8.4f} {change_pct:>+8.1f}%"
        )

    print(f"\n{'=' * 60}")
    return improvements


def print_optimization_report(
    bottlenecks,
    sim_before,
    sim_after,
    node_list,
    labels,
    mfpt_before=None,
    mfpt_after=None,
):
    """Print and return optimization report for ATMS intervention."""
    before_peaks = sim_before.get_peak_vc_over_time(start_timestep=1)
    after_peaks = sim_after.get_peak_vc_over_time(start_timestep=1)

    v_c_before = {
        b["node_id"]: float(before_peaks[b["node_id"]][0])
        for b in bottlenecks
    }
    v_c_after = {
        b["node_id"]: float(after_peaks[b["node_id"]][0])
        for b in bottlenecks
    }

    if mfpt_before and mfpt_after:
        before_values = [value for value in mfpt_before.values() if value > 0]
        after_values = [value for value in mfpt_after.values() if value > 0]
        avg_before = float(np.mean(before_values)) if before_values else 0.0
        avg_after = float(np.mean(after_values)) if after_values else 0.0
        if avg_before > 0:
            antt_improvement_percent = ((avg_before - avg_after) / avg_before) * 100.0
        else:
            antt_improvement_percent = 0.0
    else:
        antt_improvement_percent = 0.0

    report = {
        "strategy": "Adaptive Signal Timing with Downstream Coordination",
        "intervention_type": "ATMS - Centralized Signal Control",
        "bottleneck_intersections": [b["label"] for b in bottlenecks],
        "v_c_before": {str(node): ratio for node, ratio in v_c_before.items()},
        "v_c_after": {str(node): ratio for node, ratio in v_c_after.items()},
        "antt_improvement_percent": float(antt_improvement_percent),
    }

    print("\n" + "=" * 60)
    print("OPTIMIZATION REPORT - ADAPTIVE SIGNAL TIMING")
    print("=" * 60)
    print(f"Strategy: {report['strategy']}")
    print(f"Intervention: {report['intervention_type']}")

    print("\nTop Saturated Intersections:")
    for rank, bottleneck in enumerate(bottlenecks, start=1):
        node = bottleneck["node_id"]
        print(
            f"  {rank}. {labels[node]} - "
            f"Peak v/c before={v_c_before[node]:.3f}, after={v_c_after[node]:.3f}"
        )

    print(f"\nANTT Improvement: {report['antt_improvement_percent']:.2f}%")
    print("=" * 60)
    return report


if __name__ == "__main__":
    from src.graph_model import build_graph
    from src.markov_model import build_transition_matrix_biased
    from src.simulation import run_scenario

    graph = build_graph()
    transition, nodes = build_transition_matrix_biased(graph)

    sim_base = run_scenario(graph, transition, nodes, label="Pre-ATMS")
    detected = identify_bottlenecks(sim_base)
    optimized = optimize_combined(
        graph,
        transition,
        nodes,
        [row["node_id"] for row in detected],
    )
    sim_opt = run_scenario(graph, optimized, nodes, label="Post-ATMS")
    label_map = {node: graph.nodes[node]["label"] for node in graph.nodes()}
    print_optimization_report(detected, sim_base, sim_opt, nodes, label_map)
