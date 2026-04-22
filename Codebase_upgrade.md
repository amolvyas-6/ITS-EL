=== CODING AGENT PROMPT: ITS Urban Traffic Management System ===
=== Complete Rebuild from Metro Crowd Simulation Codebase ===

CONTEXT:
You are rebuilding an existing Python + HTML/JS codebase that modeled 
metro station crowd movement using Graph Theory and Markov Chains.
The mathematical skeleton (graph model, Markov simulation, optimization,
visualization, dashboard) stays intact. Every module gets a domain 
transplant: metro station → urban road network. The output must function 
as a complete Intelligent Transportation Systems (ITS) demonstration 
covering all 5 syllabus units with road traffic as the subject.

WHAT THE NEW SYSTEM CALCULATES:
- Road network modeled as a weighted directed graph
  (intersections = nodes, road segments = edges)
- Vehicle density evolves across intersections over discrete time steps
  using Markov chain transition matrices (vehicle routing probabilities
  at each junction — equivalent to turn fractions in traffic engineering)
- Travel time to destination zones computed as Mean First Passage Time
  from the Markov fundamental matrix
- Saturated/bottleneck intersections detected from peak vehicle density
- Signal timing optimization redistributes green phases to relieve
  saturated intersections, improving average travel time
- Before vs. after optimization compared as ITS impact assessment KPIs
- Full ITS architecture layer: loop detectors (data acquisition),
  TMC (optimization engine), VMS boards (ATIS), signal controllers (ATMS)

CITY CONTEXT: Bengaluru outer ring road corridor, peak hour 8:00–9:00 AM

THE EXISTING FILE STRUCTURE TO REBUILD (keep filenames identical):
- main.py
- src/graph_model.py
- src/markov_model.py
- src/simulation.py
- src/optimization.py
- src/visualization.py
- dashboard/index.html
- dashboard/style.css
- dashboard/app.js
- dashboard/simulation_data.json

===================================================================
TASK 1 — REBUILD src/graph_model.py
===================================================================

Replace metro station topology with a Bengaluru urban road network.

NETWORK DEFINITION — 18 nodes (intersections), 28 directed edges:

Node list (id, label, type, x, y for dashboard layout):
0  — "Silk Board Junction"           type="major_signalized"   x=0.15, y=0.50
1  — "HSR Layout Signal"             type="signalized"          x=0.25, y=0.35
2  — "Agara Junction"                type="signalized"          x=0.25, y=0.65
3  — "BTM Layout Signal"             type="signalized"          x=0.38, y=0.25
4  — "Koramangala 5th Block"         type="signalized"          x=0.38, y=0.50
5  — "Koramangala 1st Block"         type="signalized"          x=0.38, y=0.70
6  — "Sony World Signal"             type="major_signalized"    x=0.52, y=0.20
7  — "Intermediate Ring Road"        type="arterial_merge"      x=0.52, y=0.45
8  — "Domlur Flyover"                type="flyover_merge"       x=0.52, y=0.65
9  — "Marathahalli Bridge"           type="major_signalized"    x=0.65, y=0.20
10 — "Outer Ring Road East"          type="arterial_merge"      x=0.65, y=0.45
11 — "Bellandur Signal"              type="signalized"          x=0.65, y=0.70
12 — "Sarjapur Road Junction"        type="major_signalized"    x=0.78, y=0.30
13 — "Kadubeesanahalli Signal"       type="signalized"          x=0.78, y=0.55
14 — "Whitefield Road"               type="destination_zone"    x=0.90, y=0.20
15 — "Electronic City"               type="destination_zone"    x=0.90, y=0.50
16 — "Hosur Road Toll"               type="destination_zone"    x=0.90, y=0.75
17 — "CBD (MG Road)"                 type="destination_zone"    x=0.05, y=0.50

Node type meanings:
- "major_signalized": high-volume signalized intersection, bottleneck candidate
- "signalized": standard signalized intersection
- "arterial_merge": arterial road merge point, no signal
- "flyover_merge": grade-separated merge
- "destination_zone": absorbing state (vehicles exit the modeled network here)

Edge list (source, target, weight=travel_time_seconds, capacity_pcu_per_hour):
Build directed edges representing actual ORR corridor connectivity.
Weight = free-flow travel time in seconds between intersections.
Capacity = PCU (Passenger Car Units) per hour, used in optimization.

Use these edges (add reciprocal edge for bidirectional roads):
(0,1,90,1800), (0,2,85,1800), (1,3,75,1400), (1,4,80,1600),
(2,4,70,1400), (2,5,65,1200), (3,6,110,1600), (4,7,95,1800),
(5,8,100,1400), (6,9,120,2000), (7,10,85,1800), (7,8,70,1200),
(8,11,90,1400), (9,12,130,2000), (10,12,95,1800), (10,13,80,1600),
(11,13,75,1400), (11,16,110,1200), (12,14,140,2000), (13,15,120,1800),
(0,17,150,2200), (3,17,160,1600), (6,17,180,1800),
(14,14,0,0), (15,15,0,0), (16,16,0,0), (17,17,0,0)

(Last 4 are self-loops for absorbing destination zone nodes.)

For bidirectional roads, add reverse edges with same weight and 80% capacity.

Add to the module:
- ROAD_CAPACITY dict: node_id → capacity (PCU/hr) derived from type
  major_signalized: 3600, signalized: 2400, arterial_merge: 3000,
  flyover_merge: 3600, destination_zone: 9999
- SIGNAL_NODES list: all node IDs where type contains "signalized"
- get_traffic_node_metadata(graph) function returning for each node:
  "label", "type", "its_subsystem", "detector_type", "signal_phase_capable"
  its_subsystem: "ATMS" for signalized, "AVCS" for merges, "ATIS_Gantry" for ORR
  detector_type: "Inductive_Loop" for signalized, "ANPR_Camera" for major_signalized,
                 "None" for destination zones
  signal_phase_capable: True if type contains "signalized"

===================================================================
TASK 2 — REBUILD src/markov_model.py
===================================================================

Keep the exact same mathematical structure. Change domain semantics.

TRANSITION MATRIX SEMANTICS (new):
- Each row i represents an intersection
- T[i][j] = probability that a vehicle at intersection i proceeds to 
  adjacent intersection j on its next movement
- This is equivalent to turn fraction assignment in traffic engineering
- Destination zone nodes remain absorbing states (T[dest, dest] = 1)

UNIFORM MATRIX:
- Equal probability split across all outgoing edges (unchanged logic)
- Represents random routing with no congestion awareness

CONGESTION-BIASED MATRIX (replaces exit-biased):
- Weight for neighbor j from node i:
  w(j) = (capacity[j] / (travel_time(i,j) + 0.1)) ^ congestion_bias
- Higher capacity and lower travel time = more vehicles routed that way
- congestion_bias parameter = 2.0 (same role as exit_bias)
- Row normalize to probabilities

MFPT SEMANTICS (new):
- MFPT from node i = expected number of time steps for a vehicle 
  originating at i to reach any destination zone
- Represents Average Network Travel Time (ANTT) in traffic engineering
- Computed identically: N = (I - Q)^-1, row sums of N

STATIONARY DISTRIBUTION SEMANTICS:
- Long-run proportion of time vehicles spend at each intersection
- Proxy for intersection utilization / saturation level

Add function compute_volume_capacity_ratio(state_vector, capacity_dict) -> dict:
- v/c ratio for node i = state_vector[i] * SCALE_FACTOR / capacity_dict[i]
- SCALE_FACTOR = 5000 (scales probability mass to approximate PCU counts)
- Returns dict: node_id -> v/c ratio
- v/c > 0.85 = saturated, v/c > 1.0 = over-capacity (used in optimization)

===================================================================
TASK 3 — REBUILD src/simulation.py
===================================================================

Keep the identical time-stepped Markov evolution engine.

INITIALIZATION CHANGE:
- Initial vehicle distribution concentrated at origin nodes:
  Silk Board (node 0): 0.35 probability mass
  Marathahalli Bridge (node 9): 0.30 probability mass  
  Sony World Signal (node 6): 0.20 probability mass
  Koramangala 5th Block (node 4): 0.15 probability mass
- This represents peak-hour vehicle injection from multiple entry corridors

SIMULATION PARAMETERS:
- N_STEPS = 30 (representing 30 signal cycles, approx 30 minutes of peak hour)
- Time step semantic: one signal cycle (~60 seconds)

Add to simulation output per step:
- v_c_ratios: dict from compute_volume_capacity_ratio at each step
- saturated_nodes: list of node IDs where v/c > 0.85 at that step
- over_capacity_nodes: list of node IDs where v/c > 1.0 at that step

===================================================================
TASK 4 — REBUILD src/optimization.py
===================================================================

Keep identical optimization structure. Replace metro semantics with 
traffic signal optimization semantics.

BOTTLENECK DETECTION (reframe):
- Bottleneck = intersection with highest peak v/c ratio across all steps
- Rank by: max(v_c_ratio[node]) across all timesteps
- Top 3 bottlenecks = candidates for adaptive signal timing intervention

OPTIMIZATION STRATEGY — "Adaptive Signal Timing":
- For bottleneck node b, reduce its self-loop weight (representing 
  vehicles held at red phase) — equivalent to extending green time
- For bottleneck node b, increase transition probability toward 
  lower-capacity downstream nodes — equivalent to signal coordination
- Rename optimize_combined() parameters:
  relief_factor=0.4 → green_extension_factor=0.4 
  (reduces probability mass retention at bottleneck node)
  accel_factor=1.3 → downstream_coordination_factor=1.3
  (increases routing toward less-saturated downstream intersections)

OPTIMIZATION REPORT must include:
- "strategy": "Adaptive Signal Timing with Downstream Coordination"
- "intervention_type": "ATMS — Centralized Signal Control"
- "bottleneck_intersections": [node labels of top 3 bottlenecks]
- "v_c_before": dict of bottleneck node v/c ratios before optimization
- "v_c_after": dict of bottleneck node v/c ratios after optimization
- "antt_improvement_percent": float (MFPT reduction %)

===================================================================
TASK 5 — NEW FILE: src/its_traffic_context.py
===================================================================

Create from scratch. This is the ITS architecture and evaluation layer.

ITS_ARCHITECTURE dict:
  "data_acquisition": {
    "technology": "Inductive Loop Detectors + ANPR Cameras",
    "mapped_to": "graph_model node detector_type field",
    "unit_syllabus": "Unit II — Detection, Identification and Collection Methods"
  }
  "data_communication": {
    "technology": "DSRC (Dedicated Short Range Communication) + 4G LTE backhaul",
    "mapped_to": "Edge weight updates in transition matrix",
    "unit_syllabus": "Unit II — Communication Tools"
  }
  "traffic_management_centre": {
    "technology": "Centralized ATMS with adaptive signal control",
    "mapped_to": "optimization.py — bottleneck detection + signal timing",
    "unit_syllabus": "Unit III — Traffic Management Centre, ATMS"
  }
  "traveller_information": {
    "technology": "Variable Message Signs (VMS) + Navigation App feeds",
    "mapped_to": "dashboard — congestion heatmap + ANTT display",
    "unit_syllabus": "Unit III — Advanced Traveller Information System (ATIS)"
  }
  "vehicle_control": {
    "technology": "Ramp metering + Incident detection on ORR",
    "mapped_to": "over_capacity_nodes alert in simulation output",
    "unit_syllabus": "Unit III — Advance Vehicle Control Systems (AVCS)"
  }
  "law_enforcement": {
    "technology": "ANPR cameras at major junctions for violation detection",
    "mapped_to": "major_signalized nodes with ANPR_Camera detector_type",
    "unit_syllabus": "Unit IV — ITS for Law Enforcement"
  }

BENGALURU_TRAFFIC_CONTEXT dict:
  "city": "Bengaluru, Karnataka"
  "corridor": "Outer Ring Road — Silk Board to Whitefield"
  "peak_hour": "08:00 — 09:00 IST (AM Peak)"
  "avg_daily_traffic_pcu": 285000
  "peak_hour_volume_pcu": 38000
  "current_avg_delay_seconds": 420
  "target_delay_reduction_percent": 25
  "smart_city_mission": True
  "atms_deployment_status": "Partial — Bengaluru Traffic Police ATMS operational at 150 junctions as of 2024"
  "anpr_cameras_deployed": 1200

Function: generate_traffic_its_report(graph_stats, bottlenecks, 
  mfpt_before, mfpt_after, v_c_ratios_before, v_c_ratios_after,
  optimization_report) -> dict

Must compute and return:
  "kpi_summary":
    - avg_antt_before: float (average MFPT before, in signal cycles)
    - avg_antt_after: float (average MFPT after)
    - antt_improvement_percent: float
    - avg_delay_reduction_seconds: float 
      (antt_improvement_percent / 100 * 420 — maps to real delay context)
    - saturated_intersections_before: int (count of nodes with v/c > 0.85)
    - saturated_intersections_after: int
    - over_capacity_intersections_before: int (v/c > 1.0)
    - over_capacity_intersections_after: int
  
  "its_unit_coverage":
    unit_1: "Urban traffic congestion on Bengaluru ORR corridor — 
             motorisation problem, peak-hour demand surge"
    unit_2: "Inductive loop detectors and ANPR cameras at 
             major_signalized nodes; DSRC communication modeled 
             via dynamic edge weight updates"
    unit_3: "TMC: bottleneck optimizer as centralized signal control; 
             ATMS: adaptive green phase extension at saturated junctions; 
             ATIS: VMS-equivalent dashboard with congestion levels; 
             AVCS: over-capacity node alerts trigger ramp metering"
    unit_4: "Impact assessment: ANTT reduction of X%, delay savings of 
             Y seconds/vehicle; v/c ratio improvement across Z junctions; 
             ANPR nodes support law enforcement functions"
    unit_5: "Smart Cities Mission 2.0 — Bengaluru ATMS integration 
             context; National ITS Architecture alignment"

  "sensor_alerts": list of dicts per node per timestep with:
    node_id, node_label, timestep, v_c_ratio, vehicle_density,
    detector_type, alert_level 
    (alert_level: "CRITICAL" if v/c>1.0, "WARNING" if v/c>0.85, 
     "MODERATE" if v/c>0.6, "NORMAL" otherwise)

Function: simulate_detector_feed(node_list, history, capacity_dict) -> list[dict]
  Same structure as previous sensor simulation but with:
  - "detector_type": from get_traffic_node_metadata
  - "v_c_ratio": computed per node per timestep
  - "estimated_queue_length_vehicles": int(v_c_ratio * 15) if v/c > 0.85 else 0
  - "signal_intervention_recommended": True if v/c > 0.85

===================================================================
TASK 6 — REBUILD src/visualization.py
===================================================================

Keep the identical plot pipeline. Rename and reframe all plot titles 
and labels for road traffic domain. Key changes:

- "Crowd Density" → "Vehicle Density (Normalized PCU)"
- "Stationary Distribution" → "Long-Run Intersection Utilization"
- "MFPT" → "Average Network Travel Time (Signal Cycles)"
- "Bottleneck" → "Saturated Intersection"
- "Exit Nodes" → "Destination Zones"
- "Baseline" / "Before" label → "Pre-ATMS Intervention"
- "Optimized" / "After" label → "Post-ATMS Signal Optimization"
- Node color in graph plots:
  major_signalized: deep red (#C0392B)
  signalized: orange (#E67E22)
  arterial_merge: blue (#2980B9)
  flyover_merge: teal (#16A085)
  destination_zone: dark green (#27AE60)
- Add a new plot: v_c_ratio_timeline.png
  Line chart showing v/c ratio over 30 time steps for the top 5 
  most congested nodes, before and after optimization.
  X-axis: Signal Cycle (time step), Y-axis: v/c Ratio
  Horizontal dashed lines at 0.85 (saturation threshold) and 1.0 
  (over-capacity threshold), labeled.

===================================================================
TASK 7 — REBUILD main.py
===================================================================

Keep identical phase structure. Replace all metro semantics.

CONFIGURATION CONSTANTS:
  N_STEPS = 30
  CONGESTION_BIAS = 2.0  (replaces exit_bias)
  GREEN_EXTENSION_FACTOR = 0.4  (replaces relief_factor)
  DOWNSTREAM_COORD_FACTOR = 1.3  (replaces accel_factor)
  TOP_N_BOTTLENECKS = 3

Phase changes:
- Phase 2: "Building transition matrices (Uniform Routing + Congestion-Biased Routing)"
- Phase 3: "Running baseline simulation — Pre-ATMS Intervention (Peak Hour)"
- Phase 4: "Identifying saturated intersections via v/c ratio analysis"
- Phase 5: "Optimizing signal timing — Adaptive Green Phase Extension"
- Phase 6: "Running optimized simulation — Post-ATMS Intervention"
- Phase 7: "Comparing ANTT and v/c ratio improvements"
- Phase 8: "Generating traffic analysis plots"
- Phase 9: "Exporting dashboard data"
- Phase 10 (NEW): "Generating ITS System Evaluation Report"

Phase 10 imports and calls generate_traffic_its_report from 
src/its_traffic_context.py with all computed values.

Console ITS report block (print after Phase 10):

╔══════════════════════════════════════════════════════════════╗
║         ITS TRAFFIC MANAGEMENT EVALUATION REPORT            ║
║   Bengaluru ORR Corridor — Silk Board to Whitefield         ║
║              Peak Hour: 08:00 – 09:00 IST                   ║
╚══════════════════════════════════════════════════════════════╝

CORRIDOR: Bengaluru Outer Ring Road
NETWORK : 18 intersections | 28 directed road segments
PEAK VOLUME: ~38,000 PCU/hr entry load

ITS UNIT COVERAGE:
  Unit I  : [unit_1 value from its_report]
  Unit II : [unit_2 value]
  Unit III: [unit_3 value]
  Unit IV : [unit_4 value]
  Unit V  : [unit_5 value]

TRAFFIC KPIs — ATMS INTERVENTION IMPACT:
  Avg Travel Time Before  : X.XX signal cycles
  Avg Travel Time After   : X.XX signal cycles
  Travel Time Improvement : XX.X%
  Est. Delay Saved/Vehicle: XX.X seconds
  Saturated Junctions Before : N  (v/c > 0.85)
  Saturated Junctions After  : N
  Over-Capacity Before       : N  (v/c > 1.00)
  Over-Capacity After        : N

DETECTOR ALERT SUMMARY:
  CRITICAL (v/c > 1.00) : N junction-cycles
  WARNING  (v/c > 0.85) : N junction-cycles
  MODERATE (v/c > 0.60) : N junction-cycles
  NORMAL               : N junction-cycles

TOP SATURATED INTERSECTIONS:
  1. [Node label] — Peak v/c: X.XX
  2. [Node label] — Peak v/c: X.XX
  3. [Node label] — Peak v/c: X.XX

===================================================================
TASK 8 — REBUILD dashboard/index.html, style.css, app.js
===================================================================

Keep identical panel structure. Rename and reframe for traffic domain.

HTML CHANGES:
- Page title: "ITS Traffic Management Dashboard — Bengaluru ORR"
- Panel 1 (graph view): "Road Network — Intersection Graph"
- Panel 2 (heatmap): "Vehicle Density Heatmap"
- Panel 3 (stationary): "Long-Run Intersection Utilization"
- Panel 4 (MFPT): "Average Network Travel Time (ANTT)"
- Panel 5 (matrix): "Vehicle Routing Probability Matrix"

ADD THREE NEW ITS PANELS (same as previous prompt, traffic domain):

PANEL A — "ITS Architecture":
Table:
| ITS Subsystem | Technology | This System |
|---|---|---|
| Data Acquisition | Inductive Loop Detectors, ANPR | Entry/Major Signalized Nodes |
| Communication | DSRC + 4G LTE Backhaul | Edge weight update mechanism |
| Traffic Management Centre | Centralized ATMS Server | Signal Timing Optimizer |
| ATIS (Variable Message Signs) | VMS, Navigation App API | This Dashboard |
| AVCS (Vehicle Control) | Ramp Metering, Incident Detection | Over-capacity Alerts |
| Law Enforcement | ANPR Violation Detection | ANPR nodes in network |

PANEL B — "Live Detector Feed":
Table updating per time step slider:
Junction Name | Detector Type | v/c Ratio | Queue (vehicles) | Alert Level
Color coded: CRITICAL=#c0392b, WARNING=#e67e22, MODERATE=#f1c40f, NORMAL=#27ae60

PANEL C — "ATMS KPI Dashboard":
- Travel Time Improvement % (large display)
- Saturated Junctions Before → After (arrow display)
- Estimated delay saved per vehicle in seconds
- Bengaluru ATMS context badge
- 5 ITS unit coverage badges

app.js CHANGES:
- renderDetectorFeed(timestep): filters detector_feed from JSON, 
  renders table with v/c ratios and alert colors
- renderATMSKPI(): renders ATMS KPI panel from its_report.kpi_summary
- Node color mapping in drawGraph(): use type field to assign colors
  (major_signalized=red, signalized=orange, merge=blue, destination=green)
- Edge thickness in drawGraph(): scale by edge capacity value

===================================================================
TASK 9 — REBUILD README.md
===================================================================

# ITS Urban Traffic Management System
## Bengaluru Outer Ring Road — ATMS Simulation
### Intelligent Transportation Systems Application | RV College of Engineering

Sections:
1. Project Overview
2. Road Network Model (18 intersections, 28 directed segments, ORR corridor)
3. ITS Architecture Mapping (full table: subsystem → technology → code module)
4. ITS Syllabus Coverage (all 5 units, explicit mapping)
5. Mathematical Model (Markov chain routing, v/c ratio, MFPT as ANTT)
6. ATMS Optimization Logic (adaptive signal timing explanation)
7. Key Performance Indicators
8. Bengaluru Context (ORR traffic, ATMS deployment status)
9. Quick Start
10. References

===================================================================
CONSTRAINTS
===================================================================

1. Do NOT change requirements.txt — same numpy/matplotlib/networkx/
   scipy/seaborn stack. No new pip dependencies.
2. The JSON export schema only adds keys — never removes existing ones.
   New keys: "its_report", "detector_feed", "v_c_history"
3. Dashboard remains a static single-page app, vanilla JS only.
4. Transition matrix must remain row-stochastic at all times.
5. Destination zone nodes (14,15,16,17) must remain absorbing states.
6. v/c ratio computation must use the SCALE_FACTOR=5000 approach 
   so ratios are in a realistic 0.4–1.2 range during peak simulation.
7. MFPT computation logic is unchanged — only semantics are relabeled.
8. All plot files must regenerate correctly in outputs/ directory.

===================================================================
VERIFICATION CHECKLIST
===================================================================

[ ] python main.py runs without error
[ ] Console shows "Bengaluru ORR Corridor" report with non-zero KPIs
[ ] v/c ratios for Silk Board and Marathahalli are in range 0.7–1.1
[ ] At least 2 nodes show v/c > 0.85 (saturated) before optimization
[ ] Optimization reduces average MFPT by at least 10%
[ ] simulation_data.json contains "its_report", "detector_feed", "v_c_history"
[ ] Dashboard renders detector feed table with color-coded alert levels
[ ] ATMS KPI panel shows non-zero travel time improvement
[ ] Node colors in graph view differ by intersection type
[ ] v_c_ratio_timeline.png generated in outputs/ with threshold lines
[ ] python -c "from src.its_traffic_context import generate_traffic_its_report; print('OK')"