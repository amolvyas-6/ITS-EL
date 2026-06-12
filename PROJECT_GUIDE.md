# ITS Urban Traffic Management System

## What This Project Is About

This project simulates **urban traffic flow on the Bengaluru Outer Ring Road corridor** using:

- **Graph Theory** to model intersections and road segments
- **Markov Chains** to model how vehicle density moves through the network over signal cycles
- **v/c ratio analysis** to detect saturated and over-capacity junctions
- **Adaptive signal timing optimization** to reduce congestion and improve travel time
- A **static dashboard** to visualize the network, detector feed, KPIs, and routing behavior

The system is built as an **Intelligent Transportation Systems (ITS)** demonstration. It maps the simulation to common ITS subsystems such as:

- Data acquisition
- Traffic management centre (ATMS)
- Traveller information (ATIS)
- Vehicle control / over-capacity alerts
- Law enforcement through ANPR-enabled major junctions

## What The Project Outputs

When you run the project, it produces three main types of output:

### 1. Console Report

The terminal prints:

- Graph and network summary
- Transition matrix validation
- Baseline traffic simulation summary
- Bottleneck/saturated intersection ranking
- Optimization report
- ITS traffic management evaluation report

Key metrics include:

- Average Network Travel Time (ANTT)
- v/c ratios
- Saturated intersections
- Over-capacity intersections
- Delay reduction estimate

### 2. Plot Files

The project generates traffic-analysis plots in the `outputs/` directory, including:

- Road network graph
- Vehicle density heatmaps
- Vehicle density evolution plots
- Long-run intersection utilization plots
- ANTT comparison plots
- Saturated intersection timeline plots
- Graph snapshots across signal cycles
- `v_c_ratio_timeline.png`

### 3. Dashboard Data

The project exports a static dashboard payload to:

`dashboard/simulation_data.json`

This JSON includes:

- Node and edge data
- Transition matrices before and after optimization
- Simulation histories
- MFPT / ANTT values
- Bottleneck list
- ITS report
- Detector feed
- v/c history

You can then open the dashboard UI in:

`dashboard/index.html`

## How To Run The Project

### 1. Create a Virtual Environment

From the project root:

```bash
python3 -m venv .venv
```

### 2. Activate the Virtual Environment

On Linux/macOS:

```bash
source .venv/bin/activate
```

### 3. Install Dependencies

```bash
python -m pip install -r requirements.txt
```

### 4. Run the Full Simulation

```bash
python main.py
```

This will:

- run the traffic simulation
- apply the optimization
- generate plots in `outputs/`
- export dashboard data to `dashboard/simulation_data.json`
- print the ITS evaluation report in the terminal

### 5. Open the Dashboard

Open this file in a browser:

`dashboard/index.html`

## Main Files

- `main.py` — runs the full pipeline
- `src/graph_model.py` — road network definition
- `src/markov_model.py` — transition matrix and Markov logic
- `src/simulation.py` — time-stepped traffic simulation
- `src/optimization.py` — adaptive signal timing logic
- `src/its_traffic_context.py` — ITS architecture and KPI reporting
- `src/visualization.py` — plot generation
- `dashboard/index.html` — dashboard structure
- `dashboard/style.css` — dashboard styling
- `dashboard/app.js` — dashboard rendering logic

## Expected Generated Locations

- Plots: `outputs/`
- Dashboard JSON: `dashboard/simulation_data.json`
- Dashboard UI: `dashboard/index.html`

## Quick Run Summary

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python main.py
```
