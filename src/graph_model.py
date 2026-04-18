"""
graph_model.py — Graph Construction & Representation

Models a metro station environment as a weighted, undirected graph.

Nodes represent physical locations:
  - Entrances (where people enter the system)
  - Platforms (boarding/alighting areas)
  - Corridors (connecting paths)
  - Ticket counters / gates
  - Exits (where people leave the system)

Edges represent walkable paths with optional distance/capacity weights.
"""

import numpy as np
import networkx as nx


# ─── Node Definitions ───────────────────────────────────────────────────────

NODE_DATA = {
    # ID: (label, type, position_x, position_y)
    0:  ("Entrance A",       "entrance",  0.0,  3.0),
    1:  ("Entrance B",       "entrance",  0.0,  7.0),
    2:  ("Security Check",   "gate",      2.0,  5.0),
    3:  ("Ticket Counter 1", "gate",      3.5,  3.5),
    4:  ("Ticket Counter 2", "gate",      3.5,  6.5),
    5:  ("Main Lobby",       "corridor",  5.0,  5.0),
    6:  ("Corridor North",   "corridor",  6.5,  7.5),
    7:  ("Corridor South",   "corridor",  6.5,  2.5),
    8:  ("Waiting Area",     "corridor",  7.5,  5.0),
    9:  ("Escalator Up",     "corridor",  8.5,  3.5),
    10: ("Escalator Down",   "corridor",  8.5,  6.5),
    11: ("Platform 1",       "platform",  10.0, 2.0),
    12: ("Platform 2",       "platform",  10.0, 5.0),
    13: ("Platform 3",       "platform",  10.0, 8.0),
    14: ("Exit West",        "exit",      12.0, 3.5),
    15: ("Exit East",        "exit",      12.0, 6.5),
}

# ─── Edge Definitions ───────────────────────────────────────────────────────
# (node_i, node_j, distance_weight)

EDGE_DATA = [
    (0,  2,  2.5),   # Entrance A → Security
    (1,  2,  2.5),   # Entrance B → Security
    (2,  3,  1.8),   # Security → Ticket 1
    (2,  4,  1.8),   # Security → Ticket 2
    (3,  5,  2.0),   # Ticket 1 → Main Lobby
    (4,  5,  2.0),   # Ticket 2 → Main Lobby
    (5,  6,  2.0),   # Main Lobby → Corridor North
    (5,  7,  2.0),   # Main Lobby → Corridor South
    (5,  8,  2.5),   # Main Lobby → Waiting Area
    (6,  8,  1.5),   # Corridor North → Waiting
    (7,  8,  1.5),   # Corridor South → Waiting
    (6, 10,  2.0),   # Corridor North → Escalator Down
    (7,  9,  2.0),   # Corridor South → Escalator Up
    (8,  9,  1.5),   # Waiting → Escalator Up
    (8, 10,  1.5),   # Waiting → Escalator Down
    (9, 11,  2.0),   # Escalator Up → Platform 1
    (9, 12,  1.5),   # Escalator Up → Platform 2
    (10, 12, 1.5),   # Escalator Down → Platform 2
    (10, 13, 2.0),   # Escalator Down → Platform 3
    (11, 14, 2.0),   # Platform 1 → Exit West
    (12, 14, 2.0),   # Platform 2 → Exit West
    (12, 15, 2.0),   # Platform 2 → Exit East
    (13, 15, 2.0),   # Platform 3 → Exit East
    (11, 12, 2.5),   # Platform 1 ↔ Platform 2
    (12, 13, 2.5),   # Platform 2 ↔ Platform 3
]


def build_graph():
    """
    Construct the metro station graph using NetworkX.

    Returns:
        G (nx.Graph): The metro station graph with node/edge attributes.
    """
    G = nx.Graph()

    # Add nodes with attributes
    for node_id, (label, ntype, x, y) in NODE_DATA.items():
        G.add_node(node_id, label=label, node_type=ntype, pos=(x, y))

    # Add edges with distance weights
    for u, v, w in EDGE_DATA:
        G.add_edge(u, v, weight=w)

    return G


def get_adjacency_matrix(G):
    """
    Return the adjacency matrix as a numpy array.

    Args:
        G (nx.Graph): The metro station graph.

    Returns:
        A (np.ndarray): Binary adjacency matrix of shape (n, n).
        node_list (list): Ordered list of node IDs.
    """
    node_list = sorted(G.nodes())
    A = nx.adjacency_matrix(G, nodelist=node_list).toarray().astype(float)
    return A, node_list


def get_weighted_adjacency_matrix(G):
    """
    Return the weighted adjacency matrix (edge weights = distances).

    Args:
        G (nx.Graph): The metro station graph.

    Returns:
        W (np.ndarray): Weighted adjacency matrix of shape (n, n).
        node_list (list): Ordered list of node IDs.
    """
    node_list = sorted(G.nodes())
    n = len(node_list)
    W = np.zeros((n, n))

    for u, v, data in G.edges(data=True):
        i = node_list.index(u)
        j = node_list.index(v)
        W[i][j] = data.get('weight', 1.0)
        W[j][i] = data.get('weight', 1.0)

    return W, node_list


def get_node_labels(G):
    """Return a dict mapping node_id → label string."""
    return {n: G.nodes[n]['label'] for n in G.nodes()}


def get_node_types(G):
    """Return a dict mapping node_id → node_type string."""
    return {n: G.nodes[n]['node_type'] for n in G.nodes()}


def get_node_positions(G):
    """Return a dict mapping node_id → (x, y) position tuple."""
    return {n: G.nodes[n]['pos'] for n in G.nodes()}


def print_graph_info(G):
    """Print summary information about the graph."""
    print("=" * 60)
    print("METRO STATION GRAPH — SUMMARY")
    print("=" * 60)
    print(f"  Nodes: {G.number_of_nodes()}")
    print(f"  Edges: {G.number_of_edges()}")
    print(f"  Density: {nx.density(G):.4f}")
    print()

    types = {}
    for n in G.nodes():
        t = G.nodes[n]['node_type']
        types.setdefault(t, []).append(G.nodes[n]['label'])

    for t, nodes in types.items():
        print(f"  [{t.upper()}] ({len(nodes)} nodes)")
        for name in nodes:
            print(f"    • {name}")
    print()

    # Degree information
    degrees = dict(G.degree())
    max_deg_node = max(degrees, key=degrees.get)
    print(f"  Max degree: Node {max_deg_node} "
          f"({G.nodes[max_deg_node]['label']}) — degree {degrees[max_deg_node]}")
    print(f"  Avg degree: {np.mean(list(degrees.values())):.2f}")
    print("=" * 60)


if __name__ == "__main__":
    G = build_graph()
    print_graph_info(G)

    A, nodes = get_adjacency_matrix(G)
    print("\nAdjacency Matrix:")
    print(A)
