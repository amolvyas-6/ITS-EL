# ITS Urban Traffic Management System
## Bengaluru Outer Ring Road — ATMS Simulation
### Intelligent Transportation Systems Application | RV College of Engineering

## 1. Project Overview

This project rebuilds the original Markov-chain transport demo into an **urban traffic management system** for the Bengaluru Outer Ring Road corridor. The model treats intersections as nodes, road movements as directed edges, and vehicle routing as a discrete-time Markov process over signal cycles. It evaluates congestion, identifies saturated junctions through **v/c ratio analysis**, applies adaptive signal timing, and exports both plots and a browser dashboard.

## 2. Road Network Model

- Corridor focus: **Silk Board to Whitefield**, with CBD and southbound exits represented as destination zones.
- Network size: **18 intersections / zones**.
- Base corridor definition: **28 primary movement specifications** from the upgrade brief.
- Modeled graph used in code: **44 directed edges**, because bidirectional movements are expanded with reverse links and destination zones retain absorbing self-loops.
- Node classes:
  - `major_signalized`
  - `signalized`
  - `arterial_merge`
  - `flyover_merge`
  - `destination_zone`

## 3. ITS Architecture Mapping

| ITS Subsystem | Technology | Code / System Mapping |
|---|---|---|
| Data Acquisition | Inductive loop detectors, ANPR cameras | `src/graph_model.py`, `src/its_traffic_context.py`, detector feed export |
| Data Communication | DSRC + 4G LTE backhaul | Dynamic routing and corridor-state propagation in transition updates |
| Traffic Management Centre | Centralized ATMS with adaptive signal control | `src/optimization.py` |
| ATIS | Variable Message Signs, navigation feed equivalent | `dashboard/index.html`, `dashboard/app.js` |
| AVCS | Ramp metering and over-capacity intervention logic | `src/simulation.py`, over-capacity alerts |
| Law Enforcement | ANPR-enabled enforcement points | `major_signalized` junction metadata |

## 4. ITS Syllabus Coverage

- **Unit I**: Bengaluru ORR congestion context, demand surge, corridor-level traffic problem framing.
- **Unit II**: Detector technologies, identification and collection methods, DSRC/backhaul communication mapping.
- **Unit III**: TMC logic, adaptive signal timing, ATMS intervention, ATIS dashboard, AVCS alert handling.
- **Unit IV**: KPI-based impact assessment, ANPR-linked law-enforcement context.
- **Unit V**: National ITS Architecture alignment and Bengaluru Smart City / ATMS deployment context.

## 5. Mathematical Model

- **Directed weighted graph**:
  - Nodes are intersections or destination zones.
  - Edges carry free-flow travel time and movement capacity.
- **Markov routing**:
  - `T[i][j]` is the probability of a vehicle at node `i` moving to node `j` in the next signal cycle.
  - Destination zones are absorbing states.
- **Vehicle density evolution**:
  - `P(t+1) = P(t) · T`
- **Average Network Travel Time (ANTT)**:
  - Computed from **Mean First Passage Time (MFPT)** to destination zones.
- **Volume-capacity ratio**:
  - `v/c = probability_mass * 5000 / operational_capacity`
  - Used for saturated (`> 0.85`) and over-capacity (`> 1.0`) junction detection.

## 6. ATMS Optimization Logic

The optimization step is modeled as **Adaptive Signal Timing with Downstream Coordination**:

- Bottlenecks are ranked by **peak operational v/c ratio** after the initial source injection cycle.
- For each bottleneck, the optimizer reduces the self-loop retention probability, representing **green phase extension**.
- Upstream approaches partially divert flow toward better downstream alternatives, representing **coordination across adjacent signals**.
- The resulting transition matrix stays row-stochastic and preserves destination-zone absorption.

## 7. Key Performance Indicators

Current runtime outputs from `python main.py` include:

- **ANTT improvement**: about **22.5%**
- **Estimated delay saved per vehicle**: about **94.6 seconds**
- **Saturated intersections before optimization**: **2**
- **Over-capacity intersections before optimization**: **1**
- **Detector alert export**:
  - `CRITICAL`
  - `WARNING`
  - `MODERATE`
  - `NORMAL`

Generated dashboard payload keys include:

- `its_report`
- `detector_feed`
- `v_c_history`

## 8. Bengaluru Context

- City: **Bengaluru, Karnataka**
- Corridor: **Outer Ring Road — Silk Board to Whitefield**
- Peak hour: **08:00–09:00 IST**
- Average daily traffic: **285,000 PCU**
- Peak-hour corridor volume: **38,000 PCU**
- Current average delay baseline: **420 seconds**
- ATMS deployment status: **Partial deployment with Bengaluru Traffic Police ATMS operational at 150 junctions as of 2024**
- ANPR deployment context: **1,200 cameras**

## 9. Quick Start

1. Create and activate a virtual environment if needed:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Install dependencies:

```bash
python -m pip install -r requirements.txt
```

3. Run the full pipeline:

```bash
python main.py
```

4. Open `dashboard/index.html` to inspect the exported ITS dashboard.

Artifacts produced:

- `outputs/` for plots, including `v_c_ratio_timeline.png`
- `dashboard/simulation_data.json` for the static dashboard

## 10. References

- ITS architecture and syllabus concepts from the RV College of Engineering ITS application framing used in the project brief.
- Network modeling and routing implementation in:
  - `src/graph_model.py`
  - `src/markov_model.py`
  - `src/simulation.py`
  - `src/optimization.py`
  - `src/its_traffic_context.py`
- Corridor context values embedded in `src/its_traffic_context.py`
