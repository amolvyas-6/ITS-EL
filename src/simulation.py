"""
simulation.py — Crowd Movement Simulation Engine

Simulates discrete-time crowd movement through the metro station graph
using the Markov chain model.

The simulation:
  1. Initializes a crowd distribution P_0 (people at various nodes)
  2. Evolves the distribution: P_{t+1} = P_t · T
  3. Tracks crowd density at every node over time
  4. Identifies congestion points (nodes with high density)
  5. Computes convergence metrics

Key concepts:
  - P_t is a probability distribution vector over nodes
  - T is the transition matrix
  - The product P_t · T redistributes the crowd according to
    movement probabilities
"""

import numpy as np
from src.markov_model import (
    compute_stationary_distribution,
    compute_mean_first_passage_time,
    validate_transition_matrix,
)


class CrowdSimulation:
    """
    Discrete-time Markov chain simulation of crowd movement.

    Attributes:
        T (np.ndarray): Transition matrix (n × n).
        node_list (list): Ordered node IDs.
        G (nx.Graph): The station graph.
        n_nodes (int): Number of nodes.
        history (list): List of distribution vectors P_0, P_1, ..., P_T.
        congestion_threshold (float): Density above which a node is congested.
    """

    def __init__(self, G, T, node_list, congestion_threshold=0.15):
        """
        Initialize the simulation.

        Args:
            G: The station graph (NetworkX).
            T: Row-stochastic transition matrix.
            node_list: Ordered node IDs matching T's rows/columns.
            congestion_threshold: Fraction of crowd above which congestion
                is flagged.
        """
        self.G = G
        self.T = T
        self.node_list = node_list
        self.n_nodes = len(node_list)
        self.congestion_threshold = congestion_threshold
        self.history = []
        self.labels = {n: G.nodes[n]['label'] for n in G.nodes()}

        validate_transition_matrix(T, "Simulation T")

    def set_initial_distribution(self, P0=None, mode="entrances"):
        """
        Set the initial crowd distribution.

        Args:
            P0 (np.ndarray, optional): Custom initial distribution.
            mode (str): How to initialize if P0 is not given:
                - "entrances": Concentrate at entrance nodes
                - "uniform": Equal distribution across all nodes
                - "random": Random distribution

        Returns:
            P0 (np.ndarray): The initial distribution vector.
        """
        if P0 is not None:
            assert len(P0) == self.n_nodes
            assert np.isclose(P0.sum(), 1.0), "P0 must sum to 1"
            self.history = [P0.copy()]
            return P0

        if mode == "entrances":
            P0 = np.zeros(self.n_nodes)
            entrance_indices = []
            for i, node in enumerate(self.node_list):
                if self.G.nodes[node]['node_type'] == 'entrance':
                    entrance_indices.append(i)

            if entrance_indices:
                prob = 1.0 / len(entrance_indices)
                for idx in entrance_indices:
                    P0[idx] = prob
            else:
                P0 = np.ones(self.n_nodes) / self.n_nodes

        elif mode == "uniform":
            P0 = np.ones(self.n_nodes) / self.n_nodes

        elif mode == "random":
            P0 = np.random.dirichlet(np.ones(self.n_nodes))

        else:
            raise ValueError(f"Unknown mode: {mode}")

        self.history = [P0.copy()]
        return P0

    def step(self):
        """
        Advance the simulation by one time step.

        Computes P_{t+1} = P_t · T

        Returns:
            P_new (np.ndarray): The new distribution vector.
        """
        P_current = self.history[-1]
        P_new = P_current @ self.T
        self.history.append(P_new)
        return P_new

    def run(self, n_steps=20):
        """
        Run the simulation for n_steps time steps.

        Args:
            n_steps (int): Number of discrete time steps.

        Returns:
            history (np.ndarray): Array of shape (n_steps+1, n_nodes)
                containing all distribution vectors.
        """
        for _ in range(n_steps):
            self.step()
        return np.array(self.history)

    def get_history_matrix(self):
        """Return the full history as a 2D numpy array."""
        return np.array(self.history)

    def get_congestion_report(self, timestep=-1):
        """
        Identify congested nodes at a given timestep.

        Args:
            timestep (int): Which timestep to analyze (-1 = latest).

        Returns:
            report (list of dict): Congestion data for each node,
                sorted by density descending.
        """
        P = self.history[timestep]
        report = []

        for i, node in enumerate(self.node_list):
            label = self.labels.get(node, f"Node {node}")
            ntype = self.G.nodes[node]['node_type']
            density = P[i]
            is_congested = density > self.congestion_threshold

            report.append({
                'node_id': node,
                'label': label,
                'type': ntype,
                'density': density,
                'congested': is_congested,
            })

        report.sort(key=lambda x: x['density'], reverse=True)
        return report

    def get_peak_congestion_over_time(self):
        """
        Find the peak density at each node across all timesteps.

        Returns:
            peaks (dict): node_id → (peak_density, timestep_of_peak).
        """
        H = np.array(self.history)
        peaks = {}

        for i, node in enumerate(self.node_list):
            col = H[:, i]
            peak_t = int(np.argmax(col))
            peak_val = col[peak_t]
            peaks[node] = (peak_val, peak_t)

        return peaks

    def compute_convergence(self, tolerance=1e-6):
        """
        Check if the distribution has converged (reached stationary state).

        Returns:
            converged_step (int or None): First step where convergence
                was detected, or None if not converged.
        """
        H = np.array(self.history)
        for t in range(1, len(H)):
            diff = np.max(np.abs(H[t] - H[t - 1]))
            if diff < tolerance:
                return t
        return None

    def compute_total_flow_through(self):
        """
        Compute the total flow through each node over the simulation.

        This is the sum of the density at each node across all time steps,
        representing how much "traffic" the node sees.

        Returns:
            flow (dict): node_id → total flow.
        """
        H = np.array(self.history)
        flow = {}
        for i, node in enumerate(self.node_list):
            flow[node] = float(H[:, i].sum())
        return flow

    def print_summary(self, n_steps=None):
        """Print a summary of the simulation results."""
        if n_steps is None:
            n_steps = len(self.history) - 1

        print("\n" + "=" * 60)
        print(f"SIMULATION SUMMARY — {n_steps} TIME STEPS")
        print("=" * 60)

        # Initial distribution
        P0 = self.history[0]
        print("\n  Initial Distribution (P₀):")
        for i, node in enumerate(self.node_list):
            if P0[i] > 1e-6:
                print(f"    {self.labels[node]:20s}: {P0[i]:.4f}")

        # Final distribution
        P_final = self.history[-1]
        print(f"\n  Final Distribution (P_{n_steps}):")
        sorted_indices = np.argsort(P_final)[::-1]
        for idx in sorted_indices:
            if P_final[idx] > 1e-6:
                node = self.node_list[idx]
                bar = "█" * int(P_final[idx] * 40)
                print(f"    {self.labels[node]:20s}: {P_final[idx]:.4f}  {bar}")

        # Congestion
        print(f"\n  Congestion Analysis (threshold = {self.congestion_threshold}):")
        report = self.get_congestion_report()
        congested = [r for r in report if r['congested']]
        if congested:
            for r in congested:
                print(f"    ⚠ {r['label']:20s}: density = {r['density']:.4f}")
        else:
            print("    ✓ No congestion detected")

        # Convergence
        conv = self.compute_convergence()
        if conv is not None:
            print(f"\n  Convergence: reached stationary state at step {conv}")
        else:
            print(f"\n  Convergence: not yet converged after {n_steps} steps")

        # Stationary distribution
        pi = compute_stationary_distribution(self.T)
        print("\n  Stationary Distribution (π):")
        sorted_pi = np.argsort(pi)[::-1]
        for idx in sorted_pi:
            if pi[idx] > 1e-6:
                node = self.node_list[idx]
                bar = "█" * int(pi[idx] * 40)
                print(f"    {self.labels[node]:20s}: {pi[idx]:.6f}  {bar}")

        # Mean first passage time to exits
        exit_nodes = [n for n in self.G.nodes()
                      if self.G.nodes[n]['node_type'] == 'exit']
        mfpt = compute_mean_first_passage_time(self.T, exit_nodes, self.node_list)
        print("\n  Mean Steps to Exit:")
        sorted_mfpt = sorted(mfpt.items(), key=lambda x: x[1], reverse=True)
        for node, steps in sorted_mfpt:
            if steps > 0:
                print(f"    {self.labels[node]:20s}: {steps:.2f} steps")

        print("\n" + "=" * 60)

        return {
            'stationary': pi,
            'mfpt': mfpt,
            'convergence_step': conv,
        }


def run_scenario(G, T, node_list, n_steps=20, init_mode="entrances",
                 P0=None, label="Default"):
    """
    Convenience function to run a complete simulation scenario.

    Args:
        G: Station graph.
        T: Transition matrix.
        node_list: Ordered node IDs.
        n_steps: Number of time steps.
        init_mode: Initialization mode.
        P0: Custom initial distribution.
        label: Scenario label for printing.

    Returns:
        sim (CrowdSimulation): The completed simulation object.
    """
    print(f"\n{'━' * 60}")
    print(f"  SCENARIO: {label}")
    print(f"{'━' * 60}")

    sim = CrowdSimulation(G, T, node_list)
    sim.set_initial_distribution(P0=P0, mode=init_mode)
    sim.run(n_steps)
    results = sim.print_summary(n_steps)

    return sim


if __name__ == "__main__":
    from graph_model import build_graph
    from markov_model import build_transition_matrix_biased

    G = build_graph()
    T, node_list = build_transition_matrix_biased(G)
    sim = run_scenario(G, T, node_list, n_steps=20, label="Biased Flow")
