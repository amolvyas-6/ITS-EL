"""
markov_model.py — Markov Chain Model for Crowd Movement

Constructs a transition matrix T from the graph structure where:
  - T[i][j] = probability of moving from node i to node j
  - Rows sum to 1 (row-stochastic matrix)
  - Transition probabilities are biased toward exits (forward flow)
  - Backtracking has reduced probability
  - Exit nodes are absorbing states (people leave the system)
  - Entrance nodes have zero self-loop (people don't stay at entrances)

The model supports:
  - Basic uniform transition (equal probability to all neighbours)
  - Biased transition (weighted toward exits using shortest-path distances)
  - Custom transition matrix injection for optimization experiments
"""

import numpy as np
from scipy import linalg
import networkx as nx


def compute_exit_distances(G, exit_nodes):
    """
    Compute shortest-path distance from every node to the nearest exit.

    Args:
        G (nx.Graph): The station graph.
        exit_nodes (list): List of exit node IDs.

    Returns:
        dist_to_exit (dict): node_id → minimum distance to any exit.
    """
    dist_to_exit = {}
    for node in G.nodes():
        min_dist = float('inf')
        for ex in exit_nodes:
            try:
                d = nx.shortest_path_length(G, node, ex, weight='weight')
                min_dist = min(min_dist, d)
            except nx.NetworkXNoPath:
                pass
        dist_to_exit[node] = min_dist
    return dist_to_exit


def build_transition_matrix_uniform(G):
    """
    Build a uniform transition matrix where each neighbour has equal probability.

    Exit nodes are absorbing (T[exit][exit] = 1).

    Args:
        G (nx.Graph): The station graph.

    Returns:
        T (np.ndarray): Transition matrix of shape (n, n).
        node_list (list): Ordered node IDs.
    """
    node_list = sorted(G.nodes())
    n = len(node_list)
    T = np.zeros((n, n))

    exit_nodes = [nd for nd in G.nodes() if G.nodes[nd]['node_type'] == 'exit']

    for i, node in enumerate(node_list):
        if node in exit_nodes:
            # Absorbing state: stays at exit
            T[i][i] = 1.0
            continue

        neighbours = list(G.neighbors(node))
        if len(neighbours) == 0:
            T[i][i] = 1.0  # Isolated node (shouldn't happen)
        else:
            prob = 1.0 / len(neighbours)
            for nb in neighbours:
                j = node_list.index(nb)
                T[i][j] = prob

    return T, node_list


def build_transition_matrix_biased(G, exit_bias=2.0, self_loop_factor=0.1):
    """
    Build a biased transition matrix that encourages movement toward exits.

    The bias works by assigning weights inversely proportional to the
    shortest-path distance to the nearest exit. Nodes closer to exits
    get higher transition probabilities.

    Args:
        G (nx.Graph): The station graph.
        exit_bias (float): Strength of the exit-seeking bias.
            Higher values = stronger pull toward exits.
        self_loop_factor (float): Small probability of staying at current node.
            Represents people pausing, looking at maps, etc.

    Returns:
        T (np.ndarray): Biased transition matrix of shape (n, n).
        node_list (list): Ordered node IDs.
    """
    node_list = sorted(G.nodes())
    n = len(node_list)
    T = np.zeros((n, n))

    exit_nodes = [nd for nd in G.nodes() if G.nodes[nd]['node_type'] == 'exit']
    entrance_nodes = [nd for nd in G.nodes() if G.nodes[nd]['node_type'] == 'entrance']

    # Compute distance to nearest exit for each node
    dist_to_exit = compute_exit_distances(G, exit_nodes)
    max_dist = max(dist_to_exit.values()) if dist_to_exit else 1.0

    for i, node in enumerate(node_list):
        # Exit nodes: absorbing state
        if node in exit_nodes:
            T[i][i] = 1.0
            continue

        neighbours = list(G.neighbors(node))
        if len(neighbours) == 0:
            T[i][i] = 1.0
            continue

        # Compute raw weights for each neighbour
        raw_weights = []
        for nb in neighbours:
            d_nb = dist_to_exit.get(nb, max_dist)
            # Inverse distance weighting: closer to exit = higher weight
            # Add 1 to avoid division by zero, raise to exit_bias power
            w = (1.0 / (d_nb + 0.1)) ** exit_bias
            raw_weights.append(w)

        # Add self-loop weight (staying in place)
        total_weight = sum(raw_weights)
        self_weight = total_weight * self_loop_factor

        # Entrance nodes: no self-loop (people move quickly from entrance)
        if node in entrance_nodes:
            self_weight = 0.0

        total_weight += self_weight

        # Normalize to probabilities
        for k, nb in enumerate(neighbours):
            j = node_list.index(nb)
            T[i][j] = raw_weights[k] / total_weight

        T[i][i] += self_weight / total_weight

    # Verify row-stochastic property
    row_sums = T.sum(axis=1)
    assert np.allclose(row_sums, 1.0), f"Row sums not 1: {row_sums}"

    return T, node_list


def compute_stationary_distribution(T):
    """
    Compute the stationary distribution π such that π = π · T.

    Uses eigenvalue decomposition: the stationary distribution is the
    left eigenvector corresponding to eigenvalue 1.

    Note: For absorbing Markov chains, the stationary distribution
    concentrates mass on absorbing states.

    Args:
        T (np.ndarray): Row-stochastic transition matrix.

    Returns:
        pi (np.ndarray): Stationary distribution vector.
    """
    n = T.shape[0]

    # Find left eigenvectors: π T = π  ⟺  T^T π^T = π^T
    eigenvalues, eigenvectors = linalg.eig(T.T)

    # Find the eigenvector for eigenvalue ≈ 1
    idx = np.argmin(np.abs(eigenvalues - 1.0))
    stationary = np.real(eigenvectors[:, idx])

    # Normalize to sum to 1
    stationary = stationary / stationary.sum()

    # Ensure non-negative (numerical precision)
    stationary = np.abs(stationary)
    stationary = stationary / stationary.sum()

    return stationary


def compute_mean_first_passage_time(T, target_nodes, node_list):
    """
    Compute the expected number of steps to reach any target node from each node.

    Uses the fundamental matrix of the absorbing Markov chain.

    Args:
        T (np.ndarray): Transition matrix.
        target_nodes (list): Target node IDs (e.g., exits).
        node_list (list): Ordered node IDs corresponding to T's rows/cols.

    Returns:
        mfpt (dict): node_id → expected steps to reach target.
    """
    n = T.shape[0]
    target_indices = [node_list.index(t) for t in target_nodes]
    transient_indices = [i for i in range(n) if i not in target_indices]

    if len(transient_indices) == 0:
        return {node_list[i]: 0.0 for i in range(n)}

    # Extract the transient submatrix Q
    Q = T[np.ix_(transient_indices, transient_indices)]

    # Fundamental matrix N = (I - Q)^{-1}
    I = np.eye(len(transient_indices))
    try:
        N = linalg.inv(I - Q)
    except linalg.LinAlgError:
        # If singular, use pseudoinverse
        N = linalg.pinv(I - Q)

    # Mean steps = N · 1  (sum each row of N)
    mean_steps = N.sum(axis=1)

    mfpt = {}
    for k, i in enumerate(transient_indices):
        mfpt[node_list[i]] = mean_steps[k]
    for i in target_indices:
        mfpt[node_list[i]] = 0.0

    return mfpt


def validate_transition_matrix(T, name="T"):
    """Validate that T is a proper row-stochastic matrix."""
    n = T.shape[0]
    assert T.shape == (n, n), f"{name} must be square"
    assert np.all(T >= -1e-10), f"{name} has negative entries"
    row_sums = T.sum(axis=1)
    assert np.allclose(row_sums, 1.0, atol=1e-6), \
        f"{name} rows don't sum to 1: {row_sums}"
    print(f"  ✓ {name} is a valid {n}×{n} row-stochastic matrix")


def print_transition_matrix(T, node_list, G, top_k=5):
    """Print the transition matrix with readable labels."""
    labels = {n: G.nodes[n]['label'] for n in G.nodes()}
    n = len(node_list)

    print("\n" + "=" * 60)
    print("TRANSITION MATRIX — TOP TRANSITIONS PER NODE")
    print("=" * 60)

    for i in range(n):
        node = node_list[i]
        label = labels.get(node, f"Node {node}")
        print(f"\n  [{node:2d}] {label}")

        # Get nonzero transitions, sorted by probability
        transitions = []
        for j in range(n):
            if T[i][j] > 1e-6:
                target_label = labels.get(node_list[j], f"Node {node_list[j]}")
                transitions.append((T[i][j], node_list[j], target_label))

        transitions.sort(reverse=True)
        for prob, tid, tlabel in transitions[:top_k]:
            bar = "█" * int(prob * 30)
            print(f"       → [{tid:2d}] {tlabel:20s}  {prob:.4f}  {bar}")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    from graph_model import build_graph

    G = build_graph()
    T_uni, nodes = build_transition_matrix_uniform(G)
    T_bias, _ = build_transition_matrix_biased(G)

    print("Uniform Transition Matrix:")
    validate_transition_matrix(T_uni, "T_uniform")
    print_transition_matrix(T_uni, nodes, G)

    print("\n\nBiased Transition Matrix:")
    validate_transition_matrix(T_bias, "T_biased")
    print_transition_matrix(T_bias, nodes, G)

    pi = compute_stationary_distribution(T_bias)
    print("\nStationary Distribution (biased):")
    labels = {n: G.nodes[n]['label'] for n in G.nodes()}
    for i, node in enumerate(nodes):
        print(f"  {labels[node]:20s}: {pi[i]:.6f}")
