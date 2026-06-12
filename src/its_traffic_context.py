"""ITS architecture and KPI context layer for Bengaluru ORR traffic simulation."""

import numpy as np

from src.graph_model import build_graph, get_traffic_node_metadata
from src.markov_model import compute_volume_capacity_ratio


ITS_ARCHITECTURE = {
    "data_acquisition": {
        "technology": "Inductive Loop Detectors + ANPR Cameras",
        "mapped_to": "graph_model node detector_type field",
        "unit_syllabus": "Unit II - Detection, Identification and Collection Methods",
    },
    "data_communication": {
        "technology": "DSRC (Dedicated Short Range Communication) + 4G LTE backhaul",
        "mapped_to": "Edge weight updates in transition matrix",
        "unit_syllabus": "Unit II - Communication Tools",
    },
    "traffic_management_centre": {
        "technology": "Centralized ATMS with adaptive signal control",
        "mapped_to": "optimization.py - bottleneck detection + signal timing",
        "unit_syllabus": "Unit III - Traffic Management Centre, ATMS",
    },
    "traveller_information": {
        "technology": "Variable Message Signs (VMS) + Navigation App feeds",
        "mapped_to": "dashboard - congestion heatmap + ANTT display",
        "unit_syllabus": "Unit III - Advanced Traveller Information System (ATIS)",
    },
    "vehicle_control": {
        "technology": "Ramp metering + Incident detection on ORR",
        "mapped_to": "over_capacity_nodes alert in simulation output",
        "unit_syllabus": "Unit III - Advance Vehicle Control Systems (AVCS)",
    },
    "law_enforcement": {
        "technology": "ANPR cameras at major junctions for violation detection",
        "mapped_to": "major_signalized nodes with ANPR_Camera detector_type",
        "unit_syllabus": "Unit IV - ITS for Law Enforcement",
    },
}


BENGALURU_TRAFFIC_CONTEXT = {
    "city": "Bengaluru, Karnataka",
    "corridor": "Outer Ring Road - Silk Board to Whitefield",
    "peak_hour": "08:00 - 09:00 IST (AM Peak)",
    "avg_daily_traffic_pcu": 285000,
    "peak_hour_volume_pcu": 38000,
    "current_avg_delay_seconds": 420,
    "target_delay_reduction_percent": 25,
    "smart_city_mission": True,
    "atms_deployment_status": "Partial - Bengaluru Traffic Police ATMS operational at 150 junctions as of 2024",
    "anpr_cameras_deployed": 1200,
}


def _alert_level(v_c_ratio):
    if v_c_ratio > 1.0:
        return "CRITICAL"
    if v_c_ratio > 0.85:
        return "WARNING"
    if v_c_ratio > 0.6:
        return "MODERATE"
    return "NORMAL"


def simulate_detector_feed(node_list, history, capacity_dict):
    """Create per-node per-timestep detector telemetry records."""
    graph = build_graph()
    metadata = get_traffic_node_metadata(graph)

    feed = []
    for timestep, state_vector in enumerate(history):
        ratios = compute_volume_capacity_ratio(state_vector, capacity_dict)

        for idx, node_id in enumerate(node_list):
            v_c_ratio = float(ratios.get(node_id, 0.0))
            feed.append(
                {
                    "node_id": int(node_id),
                    "node_label": metadata[node_id]["label"],
                    "timestep": int(timestep),
                    "vehicle_density": float(state_vector[idx]),
                    "detector_type": metadata[node_id]["detector_type"],
                    "v_c_ratio": v_c_ratio,
                    "estimated_queue_length_vehicles": int(v_c_ratio * 15) if v_c_ratio > 0.85 else 0,
                    "signal_intervention_recommended": bool(v_c_ratio > 0.85),
                    "alert_level": _alert_level(v_c_ratio),
                }
            )

    return feed


def generate_traffic_its_report(
    graph_stats,
    bottlenecks,
    mfpt_before,
    mfpt_after,
    v_c_ratios_before,
    v_c_ratios_after,
    optimization_report,
):
    """Generate ITS KPI and syllabus-coverage report from simulation outputs."""
    before_values = [value for value in mfpt_before.values() if value > 0]
    after_values = [value for value in mfpt_after.values() if value > 0]

    avg_antt_before = float(np.mean(before_values)) if before_values else 0.0
    avg_antt_after = float(np.mean(after_values)) if after_values else 0.0
    if avg_antt_before > 0:
        antt_improvement_percent = ((avg_antt_before - avg_antt_after) / avg_antt_before) * 100.0
    else:
        antt_improvement_percent = 0.0

    avg_delay_reduction_seconds = (
        antt_improvement_percent / 100.0
    ) * BENGALURU_TRAFFIC_CONTEXT["current_avg_delay_seconds"]

    saturated_before = sum(1 for ratio in v_c_ratios_before.values() if ratio > 0.85)
    saturated_after = sum(1 for ratio in v_c_ratios_after.values() if ratio > 0.85)
    over_capacity_before = sum(1 for ratio in v_c_ratios_before.values() if ratio > 1.0)
    over_capacity_after = sum(1 for ratio in v_c_ratios_after.values() if ratio > 1.0)

    improved_junctions = sum(
        1
        for node_id, ratio_before in v_c_ratios_before.items()
        if v_c_ratios_after.get(node_id, ratio_before) < ratio_before
    )

    unit_coverage = {
        "unit_1": "Urban traffic congestion on Bengaluru ORR corridor - motorisation problem, peak-hour demand surge",
        "unit_2": "Inductive loop detectors and ANPR cameras at major_signalized nodes; DSRC communication modeled via dynamic edge weight updates",
        "unit_3": "TMC: bottleneck optimizer as centralized signal control; ATMS: adaptive green phase extension at saturated junctions; ATIS: VMS-equivalent dashboard with congestion levels; AVCS: over-capacity node alerts trigger ramp metering",
        "unit_4": (
            f"Impact assessment: ANTT reduction of {antt_improvement_percent:.1f}%, "
            f"delay savings of {avg_delay_reduction_seconds:.1f} seconds/vehicle; "
            f"v/c ratio improvement across {improved_junctions} junctions; "
            "ANPR nodes support law enforcement functions"
        ),
        "unit_5": "Smart Cities Mission 2.0 - Bengaluru ATMS integration context; National ITS Architecture alignment",
    }

    detector_feed = optimization_report.get("detector_feed", [])
    sensor_alerts = [
        {
            "node_id": int(entry.get("node_id", -1)),
            "node_label": entry.get("node_label", "Unknown"),
            "timestep": int(entry.get("timestep", 0)),
            "v_c_ratio": float(entry.get("v_c_ratio", 0.0)),
            "vehicle_density": float(entry.get("vehicle_density", 0.0)),
            "detector_type": entry.get("detector_type", "None"),
            "alert_level": entry.get("alert_level", "NORMAL"),
        }
        for entry in detector_feed
    ]

    return {
        "graph_stats": graph_stats,
        "city_context": BENGALURU_TRAFFIC_CONTEXT,
        "its_architecture": ITS_ARCHITECTURE,
        "optimization_report": optimization_report,
        "bottlenecks": bottlenecks,
        "kpi_summary": {
            "avg_antt_before": float(avg_antt_before),
            "avg_antt_after": float(avg_antt_after),
            "antt_improvement_percent": float(antt_improvement_percent),
            "avg_delay_reduction_seconds": float(avg_delay_reduction_seconds),
            "saturated_intersections_before": int(saturated_before),
            "saturated_intersections_after": int(saturated_after),
            "over_capacity_intersections_before": int(over_capacity_before),
            "over_capacity_intersections_after": int(over_capacity_after),
        },
        "its_unit_coverage": unit_coverage,
        "sensor_alerts": sensor_alerts,
    }
