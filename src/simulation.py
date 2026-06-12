"""Traffic simulation engine for time-stepped Markov vehicle flow."""

import numpy as np

from src.graph_model import ROAD_CAPACITY
from src.markov_model import (
    compute_mean_first_passage_time,
    compute_stationary_distribution,
    compute_volume_capacity_ratio,
    validate_transition_matrix,
)


SATURATION_THRESHOLD = 0.85
OVER_CAPACITY_THRESHOLD = 1.0
OPERATIONAL_CAPACITY_FACTORS = {
    "major_signalized": 0.55,
    "signalized": 0.28,
    "arterial_merge": 0.80,
    "flyover_merge": 0.85,
    "destination_zone": 1.0,
}


def build_operational_capacity_dict(graph, node_list):
    """Convert geometric node capacity into operational peak-hour capacity."""
    capacity_dict = {}

    for node in node_list:
        node_type = graph.nodes[node]["node_type"]
        nominal_capacity = float(ROAD_CAPACITY.get(node, 2400))
        factor = OPERATIONAL_CAPACITY_FACTORS.get(node_type, 1.0)
        capacity_dict[node] = nominal_capacity * factor

    return capacity_dict


class CrowdSimulation:
    """Deterministic Markov simulation of vehicle density over intersections."""

    def __init__(self, G, T, node_list, congestion_threshold=SATURATION_THRESHOLD):
        self.G = G
        self.T = T
        self.node_list = node_list
        self.n_nodes = len(node_list)
        self.congestion_threshold = congestion_threshold

        self.history = []
        self.v_c_history = []
        self.saturated_history = []
        self.over_capacity_history = []

        self.labels = {node: G.nodes[node]["label"] for node in G.nodes()}
        self.capacity_dict = build_operational_capacity_dict(G, self.node_list)

        validate_transition_matrix(T, "Simulation T")

    def _record_timestep_metrics(self, distribution):
        ratios = compute_volume_capacity_ratio(distribution, self.capacity_dict)
        saturated_nodes = [node for node, ratio in ratios.items() if ratio > SATURATION_THRESHOLD]
        over_capacity_nodes = [node for node, ratio in ratios.items() if ratio > OVER_CAPACITY_THRESHOLD]

        self.v_c_history.append(ratios)
        self.saturated_history.append(saturated_nodes)
        self.over_capacity_history.append(over_capacity_nodes)

    def set_initial_distribution(self, P0=None, mode="peak_hour_origins"):
        """Set initial vehicle distribution for the scenario."""
        if P0 is not None:
            P0 = np.asarray(P0, dtype=float)
            assert len(P0) == self.n_nodes
            assert np.isclose(P0.sum(), 1.0), "P0 must sum to 1"
            self.history = [P0.copy()]
            self.v_c_history = []
            self.saturated_history = []
            self.over_capacity_history = []
            self._record_timestep_metrics(P0)
            return P0

        if mode in {"peak_hour_origins", "entrances"}:
            P0 = np.zeros(self.n_nodes, dtype=float)
            initial_mass = {
                0: 0.35,
                9: 0.30,
                6: 0.20,
                4: 0.15,
            }
            for idx, node in enumerate(self.node_list):
                P0[idx] = initial_mass.get(node, 0.0)

        elif mode == "uniform":
            P0 = np.ones(self.n_nodes, dtype=float) / self.n_nodes

        elif mode == "random":
            P0 = np.random.dirichlet(np.ones(self.n_nodes))

        else:
            raise ValueError(f"Unknown mode: {mode}")

        P0 = P0 / P0.sum()
        self.history = [P0.copy()]
        self.v_c_history = []
        self.saturated_history = []
        self.over_capacity_history = []
        self._record_timestep_metrics(P0)
        return P0

    def step(self):
        """Advance one signal-cycle step using P_{t+1} = P_t * T."""
        P_current = self.history[-1]
        P_next = P_current @ self.T
        self.history.append(P_next)
        self._record_timestep_metrics(P_next)
        return P_next

    def run(self, n_steps=30):
        """Run simulation for n_steps signal cycles."""
        for _ in range(n_steps):
            self.step()
        return np.array(self.history)

    def get_history_matrix(self):
        """Return all state vectors stacked by timestep."""
        return np.array(self.history)

    def get_congestion_report(self, timestep=-1):
        """Return node-wise density and v/c status at a timestep."""
        distribution = self.history[timestep]
        ratios = self.v_c_history[timestep]
        report = []

        for i, node in enumerate(self.node_list):
            report.append(
                {
                    "node_id": node,
                    "label": self.labels.get(node, f"Node {node}"),
                    "type": self.G.nodes[node]["node_type"],
                    "density": float(distribution[i]),
                    "v_c_ratio": float(ratios[node]),
                    "saturated": ratios[node] > SATURATION_THRESHOLD,
                    "over_capacity": ratios[node] > OVER_CAPACITY_THRESHOLD,
                }
            )

        report.sort(key=lambda row: row["v_c_ratio"], reverse=True)
        return report

    def get_peak_congestion_over_time(self):
        """Return peak density and timestep for each node (legacy metric)."""
        history_matrix = np.array(self.history)
        peaks = {}
        for i, node in enumerate(self.node_list):
            column = history_matrix[:, i]
            peak_t = int(np.argmax(column))
            peaks[node] = (float(column[peak_t]), peak_t)
        return peaks

    def get_peak_vc_over_time(self, start_timestep=0):
        """Return peak v/c ratio and timestep for each node from a given timestep onward."""
        peaks = {}
        for node in self.node_list:
            node_series = [ratios[node] for ratios in self.v_c_history[start_timestep:]]
            if not node_series:
                peaks[node] = (0.0, start_timestep)
                continue
            local_peak_idx = int(np.argmax(node_series))
            peak_t = local_peak_idx + start_timestep
            peaks[node] = (float(node_series[local_peak_idx]), peak_t)
        return peaks

    def compute_convergence(self, tolerance=1e-6):
        """Return first timestep where max state delta falls below tolerance."""
        history_matrix = np.array(self.history)
        for t in range(1, len(history_matrix)):
            diff = np.max(np.abs(history_matrix[t] - history_matrix[t - 1]))
            if diff < tolerance:
                return t
        return None

    def compute_total_flow_through(self):
        """Return cumulative vehicle density-throughput per node."""
        history_matrix = np.array(self.history)
        return {
            node: float(history_matrix[:, i].sum())
            for i, node in enumerate(self.node_list)
        }

    def print_summary(self, n_steps=None):
        """Print scenario summary with traffic and ANTT semantics."""
        if n_steps is None:
            n_steps = len(self.history) - 1

        print("\n" + "=" * 60)
        print(f"SIMULATION SUMMARY - {n_steps} SIGNAL CYCLES")
        print("=" * 60)

        p0 = self.history[0]
        print("\n  Initial Vehicle Distribution (t=0):")
        for i, node in enumerate(self.node_list):
            if p0[i] > 1e-6:
                print(f"    {self.labels[node]:28s}: {p0[i]:.4f}")

        final_report = self.get_congestion_report(timestep=-1)
        print("\n  Final Step - Top v/c Ratios:")
        for row in final_report[:8]:
            print(
                f"    {row['label']:28s}: density={row['density']:.4f}, "
                f"v/c={row['v_c_ratio']:.3f}"
            )

        conv = self.compute_convergence()
        if conv is not None:
            print(f"\n  Convergence: reached at cycle {conv}")
        else:
            print(f"\n  Convergence: not reached in {n_steps} cycles")

        pi = compute_stationary_distribution(self.T)
        destination_nodes = [
            node
            for node in self.G.nodes()
            if self.G.nodes[node]["node_type"] == "destination_zone"
        ]
        mfpt = compute_mean_first_passage_time(self.T, destination_nodes, self.node_list)

        print("\n  Average Network Travel Time (Signal Cycles):")
        for node, steps in sorted(mfpt.items(), key=lambda item: item[1], reverse=True):
            if steps > 0:
                print(f"    {self.labels[node]:28s}: {steps:.2f}")

        print("\n" + "=" * 60)

        return {
            "stationary": pi,
            "mfpt": mfpt,
            "convergence_step": conv,
            "v_c_history": self.v_c_history,
            "saturated_nodes": self.saturated_history,
            "over_capacity_nodes": self.over_capacity_history,
        }


def run_scenario(
    G,
    T,
    node_list,
    n_steps=30,
    init_mode="peak_hour_origins",
    P0=None,
    label="Default",
):
    """Convenience wrapper to run and summarize one traffic scenario."""
    print("\n" + "=" * 60)
    print(f"  SCENARIO: {label}")
    print("=" * 60)

    simulation = CrowdSimulation(G, T, node_list)
    simulation.set_initial_distribution(P0=P0, mode=init_mode)
    simulation.run(n_steps)
    simulation.print_summary(n_steps)
    return simulation


if __name__ == "__main__":
    from src.graph_model import build_graph
    from src.markov_model import build_transition_matrix_congestion_biased

    graph = build_graph()
    transition_matrix, nodes = build_transition_matrix_congestion_biased(graph)
    run_scenario(graph, transition_matrix, nodes, n_steps=30, label="Traffic Baseline")
