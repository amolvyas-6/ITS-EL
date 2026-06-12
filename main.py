#!/usr/bin/env python3
"""ITS Urban Traffic Management simulation entrypoint."""

import json
import os
import sys

import numpy as np


PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
os.environ.setdefault("MPLCONFIGDIR", os.path.join(PROJECT_ROOT, ".matplotlib"))


N_STEPS = 30
CONGESTION_BIAS = 2.0
GREEN_EXTENSION_FACTOR = 0.4
DOWNSTREAM_COORD_FACTOR = 1.3
TOP_N_BOTTLENECKS = 3


from src.graph_model import (  # noqa: E402
    ROAD_CAPACITY,
    build_graph,
    get_adjacency_matrix,
    get_traffic_node_metadata,
    get_weighted_adjacency_matrix,
    print_graph_info,
)
from src.its_traffic_context import (  # noqa: E402
    generate_traffic_its_report,
    simulate_detector_feed,
)
from src.markov_model import (  # noqa: E402
    build_transition_matrix_congestion_biased,
    build_transition_matrix_uniform,
    compute_mean_first_passage_time,
    compute_stationary_distribution,
    validate_transition_matrix,
)
from src.optimization import (  # noqa: E402
    compare_distributions,
    identify_bottlenecks,
    optimize_combined,
    print_optimization_report,
)
from src.simulation import run_scenario  # noqa: E402
from src.visualization import generate_all_plots  # noqa: E402


def _make_graph_stats(graph, adjacency, weighted):
    node_count = int(graph.number_of_nodes())
    possible_edges = max(node_count * (node_count - 1), 1)
    return {
        "nodes": node_count,
        "edges": int(graph.number_of_edges()),
        "density": float(np.sum(adjacency > 0) / possible_edges),
        "total_weight": float(np.sum(weighted)),
    }


def _build_detector_feed(node_list, sim_before, sim_after):
    feed_before = simulate_detector_feed(node_list, sim_before.history, sim_before.capacity_dict)
    for entry in feed_before:
        entry["scenario"] = "pre_atms"

    feed_after = simulate_detector_feed(node_list, sim_after.history, sim_after.capacity_dict)
    for entry in feed_after:
        entry["scenario"] = "post_atms"

    return feed_before + feed_after


def _print_origin_peak_vc(simulation, labels):
    """Print entry-corridor peak v/c ratios for verification of injected demand."""
    origin_nodes = [0, 9, 6, 4]
    peak_vc = simulation.get_peak_vc_over_time()

    print("  Peak entry-corridor v/c:")
    for node in origin_nodes:
        ratio, timestep = peak_vc.get(node, (0.0, 0))
        print(f"    {labels[node]:<28s} v/c={ratio:.3f} at cycle {timestep}")


def _print_its_console_report(its_report, bottlenecks, labels, optimization_report):
    kpis = its_report["kpi_summary"]
    units = its_report["its_unit_coverage"]

    alerts = its_report.get("sensor_alerts", [])
    critical = sum(1 for alert in alerts if alert.get("alert_level") == "CRITICAL")
    warning = sum(1 for alert in alerts if alert.get("alert_level") == "WARNING")
    moderate = sum(1 for alert in alerts if alert.get("alert_level") == "MODERATE")
    normal = sum(1 for alert in alerts if alert.get("alert_level") == "NORMAL")

    vc_before = optimization_report.get("v_c_before", {})

    print()
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║         ITS TRAFFIC MANAGEMENT EVALUATION REPORT            ║")
    print("║   Bengaluru ORR Corridor - Silk Board to Whitefield         ║")
    print("║              Peak Hour: 08:00 - 09:00 IST                   ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print()
    graph_stats = its_report.get("graph_stats", {})
    print("CORRIDOR: Bengaluru Outer Ring Road")
    print(
        f"NETWORK : {graph_stats.get('nodes', 18)} intersections | "
        f"{graph_stats.get('edges', 0)} directed road segments"
    )
    print("PEAK VOLUME: ~38,000 PCU/hr entry load")
    print()
    print("ITS UNIT COVERAGE:")
    print(f"  Unit I  : {units['unit_1']}")
    print(f"  Unit II : {units['unit_2']}")
    print(f"  Unit III: {units['unit_3']}")
    print(f"  Unit IV : {units['unit_4']}")
    print(f"  Unit V  : {units['unit_5']}")
    print()
    print("TRAFFIC KPIs - ATMS INTERVENTION IMPACT:")
    print(f"  Avg Travel Time Before  : {kpis['avg_antt_before']:.2f} signal cycles")
    print(f"  Avg Travel Time After   : {kpis['avg_antt_after']:.2f} signal cycles")
    print(f"  Travel Time Improvement : {kpis['antt_improvement_percent']:.1f}%")
    print(f"  Est. Delay Saved/Vehicle: {kpis['avg_delay_reduction_seconds']:.1f} seconds")
    print(
        f"  Saturated Junctions Before : {kpis['saturated_intersections_before']}  "
        "(v/c > 0.85)"
    )
    print(f"  Saturated Junctions After  : {kpis['saturated_intersections_after']}")
    print(
        f"  Over-Capacity Before       : {kpis['over_capacity_intersections_before']}  "
        "(v/c > 1.00)"
    )
    print(f"  Over-Capacity After        : {kpis['over_capacity_intersections_after']}")
    print()
    print("DETECTOR ALERT SUMMARY:")
    print(f"  CRITICAL (v/c > 1.00) : {critical} junction-cycles")
    print(f"  WARNING  (v/c > 0.85) : {warning} junction-cycles")
    print(f"  MODERATE (v/c > 0.60) : {moderate} junction-cycles")
    print(f"  NORMAL               : {normal} junction-cycles")
    print()
    print("TOP SATURATED INTERSECTIONS:")
    for rank, bottleneck in enumerate(bottlenecks[:3], start=1):
        node = bottleneck["node_id"]
        peak_vc = float(vc_before.get(str(node), bottleneck.get("peak_v_c", 0.0)))
        print(f"  {rank}. {labels[node]} - Peak v/c: {peak_vc:.2f}")


def export_dashboard_data(
    graph,
    node_list,
    T_before,
    T_after,
    sim_before,
    sim_after,
    pi_before,
    pi_after,
    mfpt_before,
    mfpt_after,
    bottlenecks,
    its_report,
    detector_feed,
):
    """Export all simulation and ITS data for the static dashboard."""
    data = {
        "nodes": [],
        "edges": [],
        "transition_matrix_before": T_before.tolist(),
        "transition_matrix_after": T_after.tolist(),
        "history_before": np.array(sim_before.history).tolist(),
        "history_after": np.array(sim_after.history).tolist(),
        "stationary_before": pi_before.tolist(),
        "stationary_after": pi_after.tolist(),
        "mfpt_before": {str(k): v for k, v in mfpt_before.items()},
        "mfpt_after": {str(k): v for k, v in mfpt_after.items()},
        "bottlenecks": [row["node_id"] for row in bottlenecks],
        "n_steps": len(sim_before.history) - 1,
        "its_report": its_report,
        "detector_feed": detector_feed,
        "v_c_history": {
            "before": sim_before.v_c_history,
            "after": sim_after.v_c_history,
        },
    }

    node_metadata = get_traffic_node_metadata(graph)
    for node in node_list:
        data["nodes"].append(
            {
                "id": node,
                "label": graph.nodes[node]["label"],
                "type": graph.nodes[node]["node_type"],
                "x": graph.nodes[node]["pos"][0],
                "y": graph.nodes[node]["pos"][1],
                "capacity": graph.nodes[node].get("capacity", ROAD_CAPACITY.get(node, 2400)),
                "its_subsystem": node_metadata[node]["its_subsystem"],
                "detector_type": node_metadata[node]["detector_type"],
                "signal_phase_capable": node_metadata[node]["signal_phase_capable"],
            }
        )

    for source, target, attrs in graph.edges(data=True):
        data["edges"].append(
            {
                "source": source,
                "target": target,
                "weight": attrs.get("weight", 1.0),
                "capacity": attrs.get("capacity", 1200),
            }
        )

    dashboard_dir = os.path.join(PROJECT_ROOT, "dashboard")
    os.makedirs(dashboard_dir, exist_ok=True)
    json_path = os.path.join(dashboard_dir, "simulation_data.json")

    with open(json_path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2)

    print(f"  Dashboard data exported to: {json_path}")


def main():
    print()
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║      ITS URBAN TRAFFIC MANAGEMENT SYSTEM - BENGALURU ORR    ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print()

    print("\n▶ Phase 1: Building Bengaluru ORR road network graph\n")
    graph = build_graph()
    print_graph_info(graph)

    adjacency, node_list = get_adjacency_matrix(graph)
    weighted, _ = get_weighted_adjacency_matrix(graph)
    graph_stats = _make_graph_stats(graph, adjacency, weighted)

    print("\n▶ Phase 2: Building transition matrices (Uniform Routing + Congestion-Biased Routing)\n")
    T_uniform, _ = build_transition_matrix_uniform(graph)
    validate_transition_matrix(T_uniform, "T_uniform")

    T_biased, _ = build_transition_matrix_congestion_biased(
        graph,
        congestion_bias=CONGESTION_BIAS,
        self_loop_factor=0.1,
    )
    validate_transition_matrix(T_biased, "T_congestion_biased")

    print("\n▶ Phase 3: Running baseline simulation - Pre-ATMS Intervention (Peak Hour)\n")
    sim_before = run_scenario(
        graph,
        T_biased,
        node_list,
        n_steps=N_STEPS,
        init_mode="peak_hour_origins",
        label="Pre-ATMS Intervention",
    )

    print("\n▶ Phase 4: Identifying saturated intersections via v/c ratio analysis\n")
    bottlenecks = identify_bottlenecks(sim_before, top_k=TOP_N_BOTTLENECKS)
    print("  Saturation ranking (peak v/c):")
    for row in bottlenecks:
        print(
            f"    [{row['node_id']:2d}] {row['label']:<28s} "
            f"peak v/c={row['peak_v_c']:.3f} at cycle {row['peak_timestep']}"
        )
    _print_origin_peak_vc(sim_before, {node: graph.nodes[node]["label"] for node in graph.nodes()})

    print("\n▶ Phase 5: Optimizing signal timing - Adaptive Green Phase Extension\n")
    bottleneck_ids = [row["node_id"] for row in bottlenecks]
    T_optimized = optimize_combined(
        graph,
        T_biased,
        node_list,
        bottleneck_ids,
        green_extension_factor=GREEN_EXTENSION_FACTOR,
        downstream_coordination_factor=DOWNSTREAM_COORD_FACTOR,
    )
    validate_transition_matrix(T_optimized, "T_optimized")

    print("\n▶ Phase 6: Running optimized simulation - Post-ATMS Intervention\n")
    sim_after = run_scenario(
        graph,
        T_optimized,
        node_list,
        n_steps=N_STEPS,
        init_mode="peak_hour_origins",
        label="Post-ATMS Signal Optimization",
    )

    print("\n▶ Phase 7: Comparing ANTT and v/c ratio improvements\n")
    pi_before = compute_stationary_distribution(T_biased)
    pi_after = compute_stationary_distribution(T_optimized)

    labels = {node: graph.nodes[node]["label"] for node in graph.nodes()}
    compare_distributions(
        pi_before,
        pi_after,
        node_list,
        labels,
        title="Long-Run Intersection Utilization - Pre vs Post ATMS",
    )

    destination_nodes = [
        node
        for node in graph.nodes()
        if graph.nodes[node]["node_type"] == "destination_zone"
    ]
    mfpt_before = compute_mean_first_passage_time(T_biased, destination_nodes, node_list)
    mfpt_after = compute_mean_first_passage_time(T_optimized, destination_nodes, node_list)

    optimization_report = print_optimization_report(
        bottlenecks,
        sim_before,
        sim_after,
        node_list,
        labels,
        mfpt_before=mfpt_before,
        mfpt_after=mfpt_after,
    )

    print("\n▶ Phase 8: Generating traffic analysis plots\n")
    generate_all_plots(
        G=graph,
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

    detector_feed = _build_detector_feed(node_list, sim_before, sim_after)
    optimization_report["detector_feed"] = detector_feed

    peak_vc_before = {
        node: ratio
        for node, (ratio, _) in sim_before.get_peak_vc_over_time(start_timestep=1).items()
    }
    peak_vc_after = {
        node: ratio
        for node, (ratio, _) in sim_after.get_peak_vc_over_time(start_timestep=1).items()
    }

    its_report = generate_traffic_its_report(
        graph_stats=graph_stats,
        bottlenecks=bottlenecks,
        mfpt_before=mfpt_before,
        mfpt_after=mfpt_after,
        v_c_ratios_before=peak_vc_before,
        v_c_ratios_after=peak_vc_after,
        optimization_report=optimization_report,
    )

    print("\n▶ Phase 9: Exporting dashboard data\n")
    export_dashboard_data(
        graph=graph,
        node_list=node_list,
        T_before=T_biased,
        T_after=T_optimized,
        sim_before=sim_before,
        sim_after=sim_after,
        pi_before=pi_before,
        pi_after=pi_after,
        mfpt_before=mfpt_before,
        mfpt_after=mfpt_after,
        bottlenecks=bottlenecks,
        its_report=its_report,
        detector_feed=detector_feed,
    )

    print("\n▶ Phase 10: Generating ITS System Evaluation Report\n")
    _print_its_console_report(its_report, bottlenecks, labels, optimization_report)

    print()
    print("Summary:")
    print("  outputs/   -> Traffic analysis plots")
    print("  dashboard/ -> Static ITS dashboard payload")
    print()


if __name__ == "__main__":
    main()
