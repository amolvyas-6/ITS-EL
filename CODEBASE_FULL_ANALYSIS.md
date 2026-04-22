# ITS-EL Full Codebase Analysis

Date: 2026-04-22

## 1) What This Codebase Does

This project models crowd movement inside a metro station using:

- Graph Theory for spatial topology (locations + walkable connections)
- Markov Chains for movement dynamics over discrete time steps
- Optimization heuristics for congestion mitigation
- A static web dashboard for interactive exploration of simulation outputs

At a high level, it answers:

- Where people accumulate over time
- Which nodes become bottlenecks
- How changes in transition probabilities affect evacuation efficiency

The backend is Python and generates both plots and JSON outputs. The frontend is HTML/CSS/JavaScript that visualizes this JSON data.

---

## 2) Complete Repository Inventory

The workspace contains 15 files. Nothing is omitted below.

| File | Type | Lines | Role |
|---|---:|---:|---|
| .gitignore | text | 5 | Ignore local env/build artifacts |
| README.md | text | 77 | User-facing project overview |
| requirements.txt | text | 5 | Python dependency list |
| main.py | python | 282 | End-to-end pipeline entrypoint |
| src/__init__.py | python | 1 | Python package marker |
| src/graph_model.py | python | 185 | Station topology model |
| src/markov_model.py | python | 296 | Transition matrices + Markov analysis |
| src/simulation.py | python | 329 | Time-stepped crowd simulation engine |
| src/optimization.py | python | 360 | Bottleneck detection + transition optimization |
| src/visualization.py | python | 815 | Plot generation pipeline |
| dashboard/index.html | html | 218 | Dashboard structure |
| dashboard/style.css | css | 608 | Dashboard styling + layout |
| dashboard/app.js | javascript | 871 | Dashboard data loading + rendering |
| dashboard/simulation_data.json | json | 1660 | Exported simulation dataset |
| Crowd Movement Modelling.pptx | binary (pptx) | n/a | Presentation artifact with 9 slides |

Total text lines across code/config/data: 5712

---

## 3) End-to-End Execution Pipeline

`main.py` executes nine sequential phases:

1. Build graph model of station layout.
2. Build transition matrices:
   - uniform
   - exit-biased
3. Run baseline simulation (before optimization).
4. Identify bottlenecks from flow and congestion peaks.
5. Optimize transition matrix with a combined strategy.
6. Run optimized simulation.
7. Compare pre/post metrics:
   - stationary distribution
   - mean first passage time (MFPT) to exits
8. Generate full plot suite in outputs/.
9. Export JSON payload for dashboard consumption.

Important runtime products:

- Console report (graph, transition, congestion, optimization metrics)
- Plot image files (17 outputs from visualization orchestrator)
- `dashboard/simulation_data.json` for browser-side rendering

---

## 4) Mathematical Model (Core Theory in Code)

### 4.1 Graph Definition

Station is modeled as weighted undirected graph:

- Nodes: physical places (entrances, gates, corridors, platforms, exits)
- Edges: walkable links
- Edge weights: distance-like costs

The model uses 16 nodes and 25 edges.

### 4.2 Markov Dynamics

State vector at time `t` is `P_t` (probability mass over nodes).

Transition matrix `T` is row-stochastic, and evolution is:

`P_(t+1) = P_t * T`

Matrix properties encoded in code:

- Rows sum to 1
- Entries are non-negative
- Exit nodes are absorbing (`T[exit, exit] = 1`)
- Entrances have zero self-loop in biased model

### 4.3 Biased Transition Weights

For neighbor `nb`, weight is:

`w(nb) = (1 / (d(nb, nearest_exit) + 0.1)) ^ exit_bias`

Then row normalization converts weights to probabilities.

### 4.4 MFPT (Expected Steps to Exit)

Given absorbing targets, transient submatrix `Q` is extracted and:

`N = (I - Q)^(-1)`

Expected time to absorption from each transient state is row-sum of `N`.

### 4.5 Stationary Distribution

Computed from left eigenvector of `T` for eigenvalue near 1.

For absorbing chains with multiple absorbing classes, stationary distribution is not unique globally; chosen eigenvector depends on eigenspace basis selection.

---

## 5) File-by-File Deep Analysis

## 5.1 .gitignore

Contents:

- `venv/`
- `__pycache__/`
- `*.pyc`
- `.DS_Store`
- `outputs/`

Meaning:

- Keeps local virtual environment and bytecode out of version control.
- Ignores generated plots in `outputs/` so repo remains source-focused.

Risk/Note:

- No ignore rules for `.vscode/`, `.pytest_cache/`, or coverage artifacts. Fine for this repo as-is but may matter if testing is added.

---

## 5.2 requirements.txt

Dependencies:

- numpy >= 1.24.0
- matplotlib >= 3.7.0
- networkx >= 3.1
- scipy >= 1.10.0
- seaborn >= 0.12.0

Interpretation:

- This is a numerical + plotting stack, no web backend dependency.
- SciPy is required mainly for linear algebra operations (eigenvectors, inverse/pinv).

Risk/Note:

- No upper bounds, so future major releases could introduce API drifts.

---

## 5.3 README.md

Purpose:

- Provides conceptual summary, quick start, and math context.

Strengths:

- Explains Markov and graph framing clearly for a non-specialist reader.
- Documents run command and dashboard launch path.

Gaps:

- Folder tree header uses `MM EL FINAL/`, which may not match current repository naming.
- No section documenting JSON schema for dashboard interoperability.
- No troubleshooting section (for missing dependencies or absent JSON export).

---

## 5.4 main.py

Role:

- Single orchestrator for the full experiment lifecycle.

High-level mechanics:

- Adds project root to `sys.path` so imports work from direct script execution.
- Imports model, simulation, optimization, and plotting modules.
- Defines two functions:
  - `main()`
  - `export_dashboard_data(...)`

### main()

Behavior by phase:

1. Prints formatted banner.
2. Builds graph and reports graph statistics.
3. Creates adjacency and weighted matrices, prints matrix-level metadata.
4. Builds two transition matrices:
   - uniform (`T_uniform`)
   - biased (`T_biased`, exit_bias=2.0, self_loop_factor=0.1)
5. Runs baseline scenario for `N_STEPS = 20` with entrance-concentrated initialization.
6. Identifies top 3 bottlenecks.
7. Optimizes transitions via `optimize_combined` with:
   - relief_factor=0.4
   - accel_factor=1.3
8. Runs optimized scenario.
9. Compares:
   - stationary distributions
   - MFPT values to exits
10. Prints optimization report.
11. Generates all plots.
12. Exports dashboard JSON.
13. Prints completion summary.

### export_dashboard_data(...)

Constructs JSON payload with keys:

- `nodes`, `edges`
- `transition_matrix_before`, `transition_matrix_after`
- `history_before`, `history_after`
- `stationary_before`, `stationary_after`
- `mfpt_before`, `mfpt_after` (dict keys converted to strings)
- `bottlenecks`
- `n_steps`

Writes output to `dashboard/simulation_data.json`.

Coupling:

- This function is the contract boundary between Python outputs and JS dashboard input.

Risk/Note:

- No schema version field; frontend assumes exact key names and shape.
- Uses Unicode symbols in console rendering; acceptable in most terminals, but not guaranteed in minimal shells.

---

## 5.5 src/__init__.py

Role:

- Marks `src` as a package.

Current behavior:

- Contains a one-line package description comment.

Risk/Note:

- No re-export API is defined (fine for internal-use package structure).

---

## 5.6 src/graph_model.py

Role:

- Encodes station topology and basic graph utilities.

Static data:

- `NODE_DATA`: 16 nodes, each with label, type, and 2D position.
- `EDGE_DATA`: 25 weighted undirected links.

Node types used:

- entrance
- gate
- corridor
- platform
- exit

Functions:

- `build_graph()`:
  - Creates `networkx.Graph`
  - Adds node attributes: label, node_type, pos
  - Adds weighted edges
- `get_adjacency_matrix(G)`:
  - Returns binary adjacency matrix + sorted node list
- `get_weighted_adjacency_matrix(G)`:
  - Returns weight matrix + node list
  - Populates by iterating edges and mirroring values for undirected graph
- `get_node_labels/get_node_types/get_node_positions`
- `print_graph_info(G)`:
  - Prints counts, density, type groups, max degree, average degree

Complexity observations:

- `get_weighted_adjacency_matrix` uses `node_list.index(...)` inside edge loop. For larger graphs this becomes inefficient (`O(E * V)` lookup behavior). A precomputed id->index dict would improve scaling.

Design quality:

- Strong readability and clear semantic labels.
- Physical geometry embedded directly in node data allows consistent drawing in Python and JS.

---

## 5.7 src/markov_model.py

Role:

- Builds transition matrices and advanced Markov diagnostics.

Functions and behavior:

- `compute_exit_distances(G, exit_nodes)`:
  - Computes each node's shortest weighted distance to nearest exit.
- `build_transition_matrix_uniform(G)`:
  - Equal probability among neighbors.
  - Exit nodes set to absorbing states.
- `build_transition_matrix_biased(G, exit_bias=2.0, self_loop_factor=0.1)`:
  - Neighbor weights inversely proportional to nearest-exit distance.
  - Adds self-loop proportionally (`self_loop_factor`) except at entrances.
  - Enforces row-stochasticity with assertion.
- `compute_stationary_distribution(T)`:
  - Eigen decomposition on `T.T`.
  - Picks eigenvector closest to eigenvalue 1.
  - Normalizes and absolute-values to avoid sign artifacts.
- `compute_mean_first_passage_time(T, target_nodes, node_list)`:
  - Extracts transient states and computes fundamental matrix.
  - Falls back to pseudoinverse if inversion fails.
- `validate_transition_matrix(T, name="T")`
- `print_transition_matrix(...)` for human-readable transition inspection.

Modeling notes:

- Exit nodes are absorbing by design, so long-run mass is expected to accumulate at exits.
- Entrance no-self-loop assumption encodes immediate movement from entry points.

Important limitation:

- With multiple absorbing exits, stationary distribution is not unique in general. Current eigenvector selection can arbitrarily collapse onto one absorbing state. In current exported JSON, both before and after stationary vectors place full mass on node 14 only.

Potential robustness improvement:

- For absorbing chains, report absorption probabilities by exit for chosen initial distribution instead of single stationary eigenvector.

---

## 5.8 src/simulation.py

Role:

- Runs discrete-time distribution evolution and computes operational metrics.

Primary class: `CrowdSimulation`

State:

- `T`, `node_list`, `G`, `n_nodes`
- `history` list storing all distributions from `P0` onward
- `congestion_threshold` default 0.15
- label mapping cache

Key methods:

- `set_initial_distribution(P0=None, mode="entrances")`
  - modes: entrances, uniform, random
  - entrance mode places all mass equally on entrance nodes
- `step()` computes next distribution as matrix product
- `run(n_steps=20)` iterates step
- `get_congestion_report(timestep=-1)` sorted node density report with congestion flags
- `get_peak_congestion_over_time()` per-node max density and time index
- `compute_convergence(tolerance=1e-6)` first step with max per-coordinate delta < tolerance
- `compute_total_flow_through()` sum of densities over time per node
- `print_summary(...)` prints:
  - initial/final distributions
  - congested nodes
  - convergence status
  - stationary distribution
  - MFPT ranking

Convenience wrapper:

- `run_scenario(...)` constructs simulation, initializes, runs, prints summary, returns object.

Model interpretation:

- The engine is deterministic over probability mass, not agent-based stochastic sampling.
- This gives smooth trajectory fields and stable comparisons between strategies.

Risk/Note:

- `print_summary` computes stationary distribution from transition matrix, not necessarily from finite-step trajectory endpoint.

---

## 5.9 src/optimization.py

Role:

- Detects congestion bottlenecks and builds optimized transition matrices.

Detection logic:

- `identify_bottlenecks(sim, top_k=3)`
  - For non-entry/non-exit nodes only
  - Score = total_flow_through_node * peak_density
  - Returns top-k scored nodes with metadata

Optimization strategies:

- `optimize_bottleneck_relief(...)`
  - Reduces probability into bottleneck nodes
  - Redistributes relieved mass to other non-bottleneck outgoing neighbors
  - Renormalizes every row
- `optimize_exit_acceleration(...)`
  - Rebuilds matrix with stronger exit bias and reduced self-loop
  - Does not directly use `T_original` except as API compatibility
- `optimize_path_splitting(...)`
  - Detects forward neighbors (closer to exits than current node)
  - If multiple forward options, blends toward equal split:
    - new = 0.7 * equalized + 0.3 * original
  - Renormalizes rows
- `optimize_combined(...)`
  - Runs acceleration -> bottleneck relief -> path splitting in order

Comparison/reporting:

- `compare_distributions(...)` prints before/after stationary values and percent changes.
- `print_optimization_report(...)` prints:
  - bottlenecks
  - convergence before/after
  - peak congestion reduction on bottleneck nodes

Design note:

- Strategies are heuristic and interpretable rather than optimization-solver based.

Risk/Note:

- In `print_optimization_report`, `if conv_before` treats `0` as false. If convergence occurred at step 0 (rare but possible), output would incorrectly say not converged.

---

## 5.10 src/visualization.py

Role:

- Produces all static visual outputs for analysis and reporting.

Global setup:

- Forces non-interactive `Agg` backend.
- Applies dark theme style through `matplotlib.rcParams`.
- Defines `NODE_COLORS` mapping for semantic consistency.
- Creates `outputs/` directory on import.

Utility:

- `_save_fig(fig, filename)` centralizes save path, DPI, background, close, and logging.

Plot functions:

1. `plot_graph` - node-link station graph with optional density-based sizing/highlighting
2. `plot_density_heatmap` - time x node heatmap
3. `plot_distribution_evolution` - all-node time lines + stacked area for key nodes
4. `plot_transition_matrix` - matrix heatmap with cell annotations
5. `plot_stationary_distribution` - categorical bar chart
6. `plot_comparison` - side-by-side before/after heatmaps
7. `plot_comparison_bars` - grouped before/after stationary bars with percent-change annotations
8. `plot_mfpt` - horizontal before/after bars
9. `plot_congestion_timeline` - scatter timeline for threshold exceedances
10. `plot_graph_snapshots` - multiple graph state snapshots over selected timesteps
11. `plot_adjacency_matrix` - binary adjacency visualization

Master orchestrator:

- `generate_all_plots(...)` calls all above and emits 17 files.

Quality notes:

- Visual palette and typography are coherent across all outputs.
- Plot naming convention is explicit and ordered for report assembly.

Minor hygiene notes:

- Imports `matplotlib.colors as mcolors` and `FancyBboxPatch` are unused in current file.

---

## 5.11 dashboard/index.html

Role:

- Defines static dashboard layout and UI controls.

Structural blocks:

- Sticky header with loading/status badge
- Stats bar (nodes, edges, steps, bottlenecks, improvement)
- Graph card (before/after toggle)
- Simulation control panel (time slider, play/pause/reset, speed slider, distribution list)
- Heatmap card (before/after/diff toggle)
- Stationary and MFPT chart cards
- Transition matrix card
- Mathematical foundation card (descriptive equations/concepts)
- Key observations card (filled dynamically)
- Footer

Canvas surfaces:

- Graph, heatmap, stationary, MFPT, matrix are all custom canvas-rendered by JS.

Dependency model:

- Pure static page; no framework, no bundler.
- Loads `style.css` and `app.js` directly.

---

## 5.12 dashboard/style.css

Role:

- Full visual system for dashboard.

Key architecture:

- Root CSS variables for palette, typography, spacing, radii, shadows, transitions.
- Dark theme hierarchy:
  - background tokens
  - semantic accent colors
- Componentized styles:
  - cards, toggles, sliders, buttons, legends, observation blocks
- Responsive breakpoints at 1024px and 640px.

Visual style choices:

- Strong contrast and color-coded semantic entities.
- Modern card layout with subtle hover elevation.
- Styled controls and custom range-thumb aesthetics.

Quality notes:

- Good separation by section comments.
- CSS architecture is readable and maintainable for a single-file stylesheet.

---

## 5.13 dashboard/app.js

Role:

- Data ingestion, state management, all canvas rendering, all interactive behavior.

State model:

- `DATA` JSON payload
- `currentTimestep`, `currentView`, `currentHeatmap`, `currentMatrix`
- playback state (`isPlaying`, `playInterval`, `animSpeed`)
- `DPR` for high-DPI rendering

Initialization flow:

1. `DOMContentLoaded` -> `loadData()`
2. `fetch('simulation_data.json')`
3. On success: `onDataLoaded()` updates stats + draws all views
4. On failure: status badge switched to visible error text

Rendering modules:

- `drawGraph()`
  - projects model coordinates to canvas coordinates
  - draws weighted edges and labels
  - node radius scaled by density at selected timestep
  - congestion glow for high density
- `drawHeatmap()`
  - supports before, after, and diff modes
  - includes vertical timestep indicator and color legend
- `drawStationary()`
  - grouped bars (before/after)
- `drawMFPT()`
  - horizontal bars for non-exit nodes
- `drawTransitionMatrix()`
  - matrix cell shading and optional value annotation
- `updateDistributionList()`
  - sorted list of nodes by current density
- `generateObservations()`
  - creates narrative cards from computed stats and bottleneck identities

Event system:

- Time slider updates graph/heatmap/list instantly.
- Speed slider adjusts playback interval on-the-fly.
- Play/pause/reset control animation loop.
- Toggle groups switch graph view, heatmap mode, matrix mode.
- Window resize triggers redraws via debounce.

Computed metric in UI:

- "Flow Improvement" derived from aggregate MFPT reduction across non-exit nodes (rounded to integer percent and shown as approximate).

Performance note:

- Frequent `Array.find` calls in rendering loops are acceptable for 16 nodes but would become expensive for large networks.

---

## 5.14 dashboard/simulation_data.json

Role:

- Concrete serialized snapshot of one simulation run, consumed by dashboard.

Schema contents:

- `nodes`: 16 objects with id, label, type, x, y
- `edges`: 25 objects with source, target, weight
- `transition_matrix_before`: 16x16 matrix
- `transition_matrix_after`: 16x16 matrix
- `history_before`: 21x16 matrix (t=0..20)
- `history_after`: 21x16 matrix (t=0..20)
- `stationary_before`: length 16 vector
- `stationary_after`: length 16 vector
- `mfpt_before`: dict node_id(string)->float
- `mfpt_after`: dict node_id(string)->float
- `bottlenecks`: `[2, 5, 3]`
- `n_steps`: `20`

Observed semantics from this specific file:

- Initial state mass split equally between Entrance A and Entrance B.
- Optimization decreases MFPT values for all non-exit nodes.
- Bottleneck IDs correspond to Security Check, Main Lobby, Ticket Counter 1.
- Both stationary vectors currently collapse to Exit West only.

Data-contract observations:

- Frontend assumes node ordering in arrays aligns with matrix row/column order.
- MFPT keys are strings, so JS converts numeric IDs to strings for lookup.

---

## 5.15 Crowd Movement Modelling.pptx

Role:

- Presentation artifact documenting project narrative.

Technical nature:

- PPTX (zip archive with Office Open XML structure).
- Contains 9 slides plus themes/layout assets.

Extracted slide-level content summary:

1. Title slide:
   - "Mathematical Modelling of Crowd Movement"
   - Markov Chains + Graph Theory framing
2. Abstract slide:
   - Problem, approach, outcome narrative
3. Literature survey slide:
   - Table with paper/method/key idea/limitation entries
   - 2023-2025 references
4. Introduction slide:
   - Motivation and safety relevance for dense public spaces
5. Project objectives slide:
   - Markov modeling, graph representation, density/congestion analysis, optimization
6. Methodology detail slide:
   - 6-step workflow from graphing through validation
7. Methodology visual pipeline slide
8. Academic references slide:
   - 10 citations
9. Closing slide:
   - Thank you / Q&A

Relationship to codebase:

- The presentation aligns strongly with Python pipeline phases and dashboard narrative.
- It is documentation collateral rather than executable artifact.

---

## 6) Cross-Module Dependency Graph

Primary Python dependency flow:

- `main.py` imports from all `src/*` modules.
- `src/simulation.py` imports Markov utilities from `src/markov_model.py`.
- `src/optimization.py` imports Markov builders/utilities.
- `src/visualization.py` lazily imports adjacency utility from `src/graph_model.py` in master function.

Frontend dependency flow:

- `dashboard/index.html` loads `dashboard/style.css` and `dashboard/app.js`.
- `dashboard/app.js` fetches `dashboard/simulation_data.json`.
- No direct runtime dependency between frontend and Python; coupling is file-based through exported JSON schema.

---

## 7) Data and Control Flow (Detailed)

### Control flow

`main()` is synchronous and linear. There is no async scheduling, threading, or multiprocessing.

### Data flow stages

1. Topology constants -> NetworkX graph
2. Graph -> transition matrices (`T_uniform`, `T_biased`)
3. `T_biased` + initial distribution -> baseline history
4. Baseline history -> bottleneck ranking
5. Bottlenecks + original matrix -> optimized matrix
6. Optimized matrix -> optimized history
7. Histories + matrices -> plots + comparative metrics
8. Full data package -> dashboard JSON

### Invariants preserved

- Transition matrices validated as row-stochastic.
- Simulation state vectors remain probability distributions.
- Exit states absorb probability mass over time.

---

## 8) Engineering Quality Assessment

### Strengths

- Clear modular decomposition by responsibility.
- Strong readability with descriptive function names and docstrings.
- Reproducible deterministic simulation given fixed inputs.
- Good educational clarity: theory-to-code mapping is direct.
- Frontend is dependency-light and easy to run.

### Identified limitations and risks

1. Stationary distribution method is not fully appropriate for multi-absorbing-state interpretation.
2. Several `node_list.index(...)` calls inside loops could hurt scalability.
3. Optimization is heuristic (not solver-backed), so no formal optimality guarantees.
4. JSON schema has no explicit versioning.
5. No automated tests (unit/integration/visual regression).
6. README has minor naming mismatch in project tree root label.
7. Some imports in visualization are unused.
8. Convergence reporting uses truthy check that can mis-handle step 0 edge case.

---

## 9) Numerical Behavior Snapshot (From Current Export)

- Nodes: 16
- Edges: 25
- Steps simulated: 20
- Bottlenecks: Node 2, Node 5, Node 3
- MFPT trend: improved for all non-exit nodes after optimization
- Dashboard-computed aggregate improvement: approximately low-teens percent

Observed long-run behavior:

- Both stationary vectors in exported data assign all mass to Exit West.
- This likely reflects eigenvector-basis selection under absorbing-state degeneracy rather than unique physical truth.

---

## 10) How Every File Contributes to "What We Do"

Minimal role map:

- `.gitignore` keeps repository clean of generated artifacts.
- `requirements.txt` defines scientific stack dependencies.
- `README.md` explains project intent and run instructions.
- `src/graph_model.py` defines station structure.
- `src/markov_model.py` defines movement probabilities and Markov analytics.
- `src/simulation.py` evolves crowd distributions over time.
- `src/optimization.py` modifies flow behavior to reduce congestion.
- `src/visualization.py` translates results into interpretable plots.
- `main.py` runs the full experiment and exports dashboard-ready data.
- `dashboard/index.html` provides visualization shell.
- `dashboard/style.css` defines visual language and responsive behavior.
- `dashboard/app.js` transforms exported data into interactive analytics.
- `dashboard/simulation_data.json` is the concrete bridge from Python to browser.
- `Crowd Movement Modelling.pptx` communicates the same methodology/results as presentation material.

Together, these files form a complete modeling-to-communication pipeline:

- theory -> simulation -> optimization -> visualization -> interactive interpretation -> presentation.

---

## 11) Final Conclusion

This codebase is a complete applied mathematical modeling mini-platform for crowd-flow analysis in constrained transit geometry.

It is strongest as:

- an educational demonstration of graph + Markov integration,
- a practical baseline for congestion analysis,
- and a reproducible before/after optimization study.

Its next maturity step would be:

- stronger statistical validation,
- improved handling of absorbing-chain long-run metrics,
- explicit test coverage and schema versioning.

Even in current form, every file has a clear role and contributes directly to the central objective: modeling and improving movement efficiency in dense public infrastructure.
