"""Markov traffic flow model for Bengaluru ORR intersections."""

import numpy as np
import networkx as nx
from scipy import linalg

from src.graph_model import ROAD_CAPACITY


SCALE_FACTOR = 5000
DESTINATION_ROUTING_CAPACITY = 3200
SELF_LOOP_MULTIPLIERS = {
    "major_signalized": 4.5,
    "signalized": 3.8,
    "arterial_merge": 1.2,
    "flyover_merge": 0.8,
    "destination_zone": 0.0,
}


def get_destination_nodes(graph):
    """Return destination-zone node IDs (absorbing states)."""
    return [
        node
        for node in graph.nodes()
        if graph.nodes[node].get("node_type") == "destination_zone"
    ]


def compute_exit_distances(graph, target_nodes=None):
    """Return shortest weighted distance from each node to any destination."""
    if target_nodes is None:
        target_nodes = get_destination_nodes(graph)

    dist_to_target = {}
    for node in graph.nodes():
        best = float("inf")
        for target in target_nodes:
            try:
                distance = nx.shortest_path_length(
                    graph,
                    source=node,
                    target=target,
                    weight="weight",
                )
                best = min(best, float(distance))
            except nx.NetworkXNoPath:
                continue
        dist_to_target[node] = best
    return dist_to_target


def _get_routing_capacity(graph, node):
    """Return the effective routing capacity used for transition weighting."""
    node_type = graph.nodes[node].get("node_type")
    capacity = float(graph.nodes[node].get("capacity", ROAD_CAPACITY.get(node, 2400)))

    if node_type == "destination_zone":
        return min(capacity, DESTINATION_ROUTING_CAPACITY)
    return capacity


def _get_self_loop_multiplier(graph, node):
    """Return node-type retention multiplier for red-phase holding."""
    node_type = graph.nodes[node].get("node_type", "")
    return float(SELF_LOOP_MULTIPLIERS.get(node_type, 1.0))


def build_transition_matrix_uniform(graph):
    """Build uniform routing transition matrix for directed road graph."""
    node_list = sorted(graph.nodes())
    index_by_node = {node: idx for idx, node in enumerate(node_list)}
    n_nodes = len(node_list)

    transition = np.zeros((n_nodes, n_nodes), dtype=float)
    destination_nodes = set(get_destination_nodes(graph))

    for node in node_list:
        i = index_by_node[node]

        if node in destination_nodes:
            transition[i, i] = 1.0
            continue

        outgoing = [nb for nb in graph.successors(node) if nb != node]
        if not outgoing:
            transition[i, i] = 1.0
            continue

        probability = 1.0 / len(outgoing)
        for neighbor in outgoing:
            j = index_by_node[neighbor]
            transition[i, j] = probability

    return transition, node_list


def build_transition_matrix_congestion_biased(
    graph,
    congestion_bias=2.0,
    self_loop_factor=0.1,
):
    """Build congestion-aware routing matrix using capacity, travel time, and signal holding."""
    node_list = sorted(graph.nodes())
    index_by_node = {node: idx for idx, node in enumerate(node_list)}
    n_nodes = len(node_list)

    transition = np.zeros((n_nodes, n_nodes), dtype=float)
    destination_nodes = set(get_destination_nodes(graph))

    for node in node_list:
        i = index_by_node[node]

        if node in destination_nodes:
            transition[i, i] = 1.0
            continue

        outgoing = [nb for nb in graph.successors(node) if nb != node]
        if not outgoing:
            transition[i, i] = 1.0
            continue

        raw_weights = []
        for neighbor in outgoing:
            edge_data = graph.get_edge_data(node, neighbor, default={})
            travel_time = float(edge_data.get("weight", 1.0))
            capacity = _get_routing_capacity(graph, neighbor)

            weight = (capacity / (travel_time + 0.1)) ** congestion_bias
            raw_weights.append(weight)

        outgoing_weight = float(np.sum(raw_weights))
        self_weight = outgoing_weight * self_loop_factor * _get_self_loop_multiplier(graph, node)
        total_weight = outgoing_weight + self_weight

        for idx, neighbor in enumerate(outgoing):
            j = index_by_node[neighbor]
            transition[i, j] = raw_weights[idx] / total_weight

        transition[i, i] += self_weight / total_weight

        row_sum = transition[i].sum()
        if row_sum > 0:
            transition[i] /= row_sum

    validate_transition_matrix(transition, "T_congestion_biased")
    return transition, node_list


def build_transition_matrix_biased(graph, exit_bias=2.0, self_loop_factor=0.1):
    """Backward-compatible alias for congestion-biased transition matrix."""
    return build_transition_matrix_congestion_biased(
        graph,
        congestion_bias=exit_bias,
        self_loop_factor=self_loop_factor,
    )


def compute_stationary_distribution(transition):
    """Compute stationary distribution vector pi such that pi = pi * T."""
    eigenvalues, eigenvectors = linalg.eig(transition.T)
    idx = int(np.argmin(np.abs(eigenvalues - 1.0)))
    stationary = np.real(eigenvectors[:, idx])

    stationary = np.abs(stationary)
    total = stationary.sum()
    if total <= 0:
        return np.ones(transition.shape[0], dtype=float) / transition.shape[0]

    stationary = stationary / total
    return stationary


def compute_mean_first_passage_time(transition, target_nodes, node_list):
    """Compute MFPT to destination nodes using fundamental matrix."""
    n_nodes = transition.shape[0]
    index_by_node = {node: idx for idx, node in enumerate(node_list)}
    target_indices = [index_by_node[node] for node in target_nodes if node in index_by_node]
    transient_indices = [idx for idx in range(n_nodes) if idx not in target_indices]

    if not transient_indices:
        return {node_list[idx]: 0.0 for idx in range(n_nodes)}

    q_matrix = transition[np.ix_(transient_indices, transient_indices)]
    identity = np.eye(len(transient_indices))

    try:
        fundamental = linalg.inv(identity - q_matrix)
    except linalg.LinAlgError:
        fundamental = linalg.pinv(identity - q_matrix)

    mean_steps = fundamental.sum(axis=1)

    mfpt = {}
    for local_idx, global_idx in enumerate(transient_indices):
        mfpt[node_list[global_idx]] = float(mean_steps[local_idx])
    for idx in target_indices:
        mfpt[node_list[idx]] = 0.0

    return mfpt


def compute_volume_capacity_ratio(state_vector, capacity_dict):
    """Compute node-wise volume/capacity ratios from a state distribution."""
    ratios = {}
    for node_id, probability_mass in enumerate(state_vector):
        capacity = float(capacity_dict.get(node_id, 1.0))
        if capacity <= 0:
            ratios[node_id] = 0.0
            continue
        ratios[node_id] = float(probability_mass) * SCALE_FACTOR / capacity
    return ratios


def validate_transition_matrix(transition, name="T"):
    """Validate that transition matrix is square, non-negative, row-stochastic."""
    n_nodes = transition.shape[0]
    assert transition.shape == (n_nodes, n_nodes), f"{name} must be square"
    assert np.all(transition >= -1e-10), f"{name} has negative entries"
    row_sums = transition.sum(axis=1)
    assert np.allclose(row_sums, 1.0, atol=1e-6), (
        f"{name} rows do not sum to 1: {row_sums}"
    )
    print(f"  [ok] {name} is a valid {n_nodes}x{n_nodes} row-stochastic matrix")


def print_transition_matrix(transition, node_list, graph, top_k=5):
    """Print top transition probabilities from each node."""
    labels = {node: graph.nodes[node]["label"] for node in graph.nodes()}
    n_nodes = len(node_list)

    print("\n" + "=" * 60)
    print("VEHICLE ROUTING PROBABILITIES - TOP TRANSITIONS")
    print("=" * 60)

    for i in range(n_nodes):
        node = node_list[i]
        print(f"\n  [{node:2d}] {labels.get(node, f'Node {node}')}")

        outgoing = []
        for j in range(n_nodes):
            prob = transition[i, j]
            if prob > 1e-6:
                target = node_list[j]
                outgoing.append((prob, target, labels.get(target, f"Node {target}")))

        outgoing.sort(reverse=True)
        for prob, target, label in outgoing[:top_k]:
            print(f"      -> [{target:2d}] {label:24s} {prob:.4f}")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    from src.graph_model import build_graph

    road_graph = build_graph()
    t_uniform, ordered_nodes = build_transition_matrix_uniform(road_graph)
    t_congestion, _ = build_transition_matrix_congestion_biased(road_graph)

    validate_transition_matrix(t_uniform, "T_uniform")
    validate_transition_matrix(t_congestion, "T_congestion")
    print_transition_matrix(t_congestion, ordered_nodes, road_graph)
