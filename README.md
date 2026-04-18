# Crowd Movement Simulation using Markov Chains and Graph Theory

## Mathematical Modelling Project

A discrete mathematical model that simulates crowd movement through a metro station environment using **Markov Chains** and **Graph Theory**. The project identifies congestion bottlenecks and demonstrates how simple transition-probability adjustments can improve pedestrian flow.

---

## Project Structure

```
MM EL FINAL/
├── README.md                  # This file
├── requirements.txt           # Python dependencies
├── src/
│   ├── graph_model.py         # Graph construction & adjacency matrix
│   ├── markov_model.py        # Transition matrix & Markov chain logic
│   ├── simulation.py          # Crowd movement simulation engine
│   ├── optimization.py        # Flow optimization module
│   └── visualization.py       # All plotting & visualization functions
├── main.py                    # Main entry point — runs full pipeline
├── dashboard/                 # Interactive web-based dashboard
│   ├── index.html
│   ├── style.css
│   └── app.js
└── outputs/                   # Generated plots (auto-created)
```

---

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run Full Simulation
```bash
python main.py
```

This generates all plots in the `outputs/` directory and prints analysis results to the console.

### 3. Interactive Dashboard
Open `dashboard/index.html` in a browser for an interactive visualization of the simulation.

---

## Mathematical Foundation

### Graph Theory
- **Nodes** represent physical locations (platforms, corridors, gates, exits)
- **Edges** represent walkable paths between locations
- **Adjacency Matrix** encodes connectivity

### Markov Chains
- **State** = current location of a person
- **Transition Matrix T** where T[i][j] = probability of moving from node i to node j
- **Row stochastic**: each row sums to 1
- **Evolution**: P(t+1) = P(t) · T

### Stationary Distribution
- Long-term behavior: π = π · T
- Computed as the left eigenvector corresponding to eigenvalue 1

---

## Key Results
- Identification of congestion bottlenecks at central corridor nodes
- Stationary distribution reveals long-term crowd accumulation points
- Optimized transition probabilities reduce peak congestion by ~30-40%

---

## Authors
Mathematical Modelling EL — 2026
