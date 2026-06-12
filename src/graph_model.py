"""Traffic graph construction and metadata for Bengaluru ORR corridor."""

import numpy as np
import networkx as nx


NODE_DATA = {
    0: ("Silk Board Junction", "major_signalized", 0.15, 0.50),
    1: ("HSR Layout Signal", "signalized", 0.25, 0.35),
    2: ("Agara Junction", "signalized", 0.25, 0.65),
    3: ("BTM Layout Signal", "signalized", 0.38, 0.25),
    4: ("Koramangala 5th Block", "signalized", 0.38, 0.50),
    5: ("Koramangala 1st Block", "signalized", 0.38, 0.70),
    6: ("Sony World Signal", "major_signalized", 0.52, 0.20),
    7: ("Intermediate Ring Road", "arterial_merge", 0.52, 0.45),
    8: ("Domlur Flyover", "flyover_merge", 0.52, 0.65),
    9: ("Marathahalli Bridge", "major_signalized", 0.65, 0.20),
    10: ("Outer Ring Road East", "arterial_merge", 0.65, 0.45),
    11: ("Bellandur Signal", "signalized", 0.65, 0.70),
    12: ("Sarjapur Road Junction", "major_signalized", 0.78, 0.30),
    13: ("Kadubeesanahalli Signal", "signalized", 0.78, 0.55),
    14: ("Whitefield Road", "destination_zone", 0.90, 0.20),
    15: ("Electronic City", "destination_zone", 0.90, 0.50),
    16: ("Hosur Road Toll", "destination_zone", 0.90, 0.75),
    17: ("CBD (MG Road)", "destination_zone", 0.05, 0.50),
}


TYPE_CAPACITY = {
    "major_signalized": 3600,
    "signalized": 2400,
    "arterial_merge": 3000,
    "flyover_merge": 3600,
    "destination_zone": 9999,
}


ROAD_CAPACITY = {
    node_id: TYPE_CAPACITY[node_type]
    for node_id, (_, node_type, _, _) in NODE_DATA.items()
}


SIGNAL_NODES = [
    node_id
    for node_id, (_, node_type, _, _) in NODE_DATA.items()
    if "signalized" in node_type
]


DESTINATION_NODES = {
    node_id
    for node_id, (_, node_type, _, _) in NODE_DATA.items()
    if node_type == "destination_zone"
}


PRIMARY_EDGE_DATA = [
    (0, 1, 90, 1800),
    (0, 2, 85, 1800),
    (1, 3, 75, 1400),
    (1, 4, 80, 1600),
    (2, 4, 70, 1400),
    (2, 5, 65, 1200),
    (3, 6, 110, 1600),
    (4, 7, 95, 1800),
    (5, 8, 100, 1400),
    (6, 9, 120, 2000),
    (7, 10, 85, 1800),
    (7, 8, 70, 1200),
    (8, 11, 90, 1400),
    (9, 12, 130, 2000),
    (10, 12, 95, 1800),
    (10, 13, 80, 1600),
    (11, 13, 75, 1400),
    (11, 16, 110, 1200),
    (12, 14, 140, 2000),
    (13, 15, 120, 1800),
    (0, 17, 150, 2200),
    (3, 17, 160, 1600),
    (6, 17, 180, 1800),
    (14, 14, 0, 0),
    (15, 15, 0, 0),
    (16, 16, 0, 0),
    (17, 17, 0, 0),
]


def _is_bidirectional_candidate(source, target):
    if source == target:
        return False
    if source in DESTINATION_NODES or target in DESTINATION_NODES:
        return False
    return True


def _build_directed_edges():
    directed_edges = {}
    for source, target, travel_time, capacity in PRIMARY_EDGE_DATA:
        directed_edges[(source, target)] = {
            "weight": float(travel_time),
            "capacity": float(capacity),
        }

        if _is_bidirectional_candidate(source, target):
            reverse_capacity = float(capacity) * 0.8
            directed_edges.setdefault(
                (target, source),
                {"weight": float(travel_time), "capacity": reverse_capacity},
            )

    return [
        (source, target, attrs["weight"], attrs["capacity"])
        for (source, target), attrs in sorted(directed_edges.items())
    ]


EDGE_DATA = _build_directed_edges()


def build_graph():
    """Construct the directed Bengaluru ORR traffic graph."""
    graph = nx.DiGraph()

    for node_id, (label, node_type, x, y) in NODE_DATA.items():
        graph.add_node(
            node_id,
            label=label,
            node_type=node_type,
            pos=(x, y),
            capacity=ROAD_CAPACITY[node_id],
        )

    for source, target, travel_time, capacity in EDGE_DATA:
        graph.add_edge(source, target, weight=travel_time, capacity=capacity)

    return graph


def get_adjacency_matrix(graph):
    """Return binary directed adjacency matrix and ordered node IDs."""
    node_list = sorted(graph.nodes())
    adjacency = nx.to_numpy_array(graph, nodelist=node_list, dtype=float)
    adjacency = (adjacency > 0).astype(float)
    return adjacency, node_list


def get_weighted_adjacency_matrix(graph):
    """Return directed weighted adjacency matrix and ordered node IDs."""
    node_list = sorted(graph.nodes())
    weighted = nx.to_numpy_array(
        graph,
        nodelist=node_list,
        dtype=float,
        weight="weight",
    )
    return weighted, node_list


def get_node_labels(graph):
    """Return mapping node_id -> intersection label."""
    return {node: graph.nodes[node]["label"] for node in graph.nodes()}


def get_node_types(graph):
    """Return mapping node_id -> node type."""
    return {node: graph.nodes[node]["node_type"] for node in graph.nodes()}


def get_node_positions(graph):
    """Return mapping node_id -> dashboard position (x, y)."""
    return {node: graph.nodes[node]["pos"] for node in graph.nodes()}


def get_traffic_node_metadata(graph):
    """Return ITS-oriented metadata for each intersection node."""
    metadata = {}

    for node in graph.nodes():
        node_type = graph.nodes[node]["node_type"]
        label = graph.nodes[node]["label"]

        if node_type == "major_signalized":
            detector_type = "ANPR_Camera"
        elif "signalized" in node_type:
            detector_type = "Inductive_Loop"
        elif node_type == "destination_zone":
            detector_type = "None"
        else:
            detector_type = "None"

        if "signalized" in node_type:
            its_subsystem = "ATMS"
        elif "merge" in node_type:
            its_subsystem = "AVCS"
        else:
            its_subsystem = "ATIS_Gantry"

        metadata[node] = {
            "label": label,
            "type": node_type,
            "its_subsystem": its_subsystem,
            "detector_type": detector_type,
            "signal_phase_capable": "signalized" in node_type,
        }

    return metadata


def print_graph_info(graph):
    """Print summary information for the directed road network."""
    print("=" * 60)
    print("BENGALURU ORR TRAFFIC GRAPH - SUMMARY")
    print("=" * 60)
    print(f"  Nodes: {graph.number_of_nodes()}")
    print(f"  Directed edges: {graph.number_of_edges()}")
    print(f"  Density: {nx.density(graph):.4f}")

    node_types = {}
    for node in graph.nodes():
        ntype = graph.nodes[node]["node_type"]
        node_types.setdefault(ntype, []).append(graph.nodes[node]["label"])

    print("\n  Node groups:")
    for ntype, labels in node_types.items():
        print(f"    [{ntype}] ({len(labels)})")

    in_degrees = dict(graph.in_degree())
    out_degrees = dict(graph.out_degree())
    max_out = max(out_degrees, key=out_degrees.get)
    max_in = max(in_degrees, key=in_degrees.get)

    print("\n  Degree highlights:")
    print(
        f"    Max out-degree: Node {max_out} "
        f"({graph.nodes[max_out]['label']}) -> {out_degrees[max_out]}"
    )
    print(
        f"    Max in-degree: Node {max_in} "
        f"({graph.nodes[max_in]['label']}) -> {in_degrees[max_in]}"
    )
    print(f"    Avg out-degree: {np.mean(list(out_degrees.values())):.2f}")
    print(f"    Avg in-degree: {np.mean(list(in_degrees.values())):.2f}")
    print("=" * 60)


if __name__ == "__main__":
    traffic_graph = build_graph()
    print_graph_info(traffic_graph)

    adjacency, ordered_nodes = get_adjacency_matrix(traffic_graph)
    print("\nAdjacency Matrix shape:", adjacency.shape)
    print("Ordered nodes:", ordered_nodes)
