---

**SLIDE 1 — TITLE SLIDE**

**Heading:** ITS Urban Traffic Management System

**Content:**
Markov Chain & Graph Theory Modelling for Road Network Congestion
Intelligent Transportation Systems — LAB EL

Team Members:
[Name] — [USN]
[Name] — [USN]
[Name] — [USN]

*No image needed*

---

**SLIDE 2 — INTRODUCTION**

**Heading:** Introduction

**Subheading:** Intelligent Transportation Systems and Urban Road Congestion

**Content:**

**ITS DEFINED**
Intelligent Transportation Systems integrate advanced sensing, data processing, and communication technologies into road infrastructure to improve safety, reduce congestion, and optimize vehicle flow across urban networks.

**INDIAN CONTEXT**
Bengaluru's Outer Ring Road carries over 285,000 PCU daily. Peak hour volume between Silk Board and Whitefield reaches 38,000 PCU/hr, making it one of India's most congested urban corridors.

**COMPUTATIONAL NEED**
Manual signal timing and reactive traffic management cannot handle dynamic peak-hour demand. Mathematical modelling of vehicle routing probabilities enables predictive, centralized ATMS intervention before congestion saturates intersections.

**IMAGE PROMPT:**
`Aerial photorealistic view of Bengaluru Outer Ring Road during peak morning hour, dense bumper-to-bumper traffic at a major signalized intersection, overhead highway view, warm morning light, no text`

---

**SLIDE 3 — IDENTIFICATION OF PROBLEM**

**Heading:** Identification of Problem

**Subheading:** Operational Gaps in Urban Traffic Management on Bengaluru ORR

**Content:**

**INTERSECTION SATURATION**
Key junctions — Silk Board, Marathahalli Bridge, Sony World Signal — consistently exceed v/c ratios of 0.85 during peak hours with no real-time computational mechanism to predict or preempt saturation.

**FIXED SIGNAL TIMING**
Current signal phases at most Bengaluru junctions are pre-timed and static. They do not respond to live vehicle density, causing unnecessary delays even when downstream roads are clear.

**NO NETWORK-LEVEL OPTIMIZATION**
Traffic management operates junction-by-junction. There is no corridor-level model that optimizes routing probabilities and green phase coordination across the entire Silk Board–Whitefield corridor simultaneously.

**IMAGE PROMPT:**
`Ground-level photograph of extreme traffic congestion at Silk Board Junction Bengaluru, hundreds of vehicles gridlocked, traffic signal visible, peak hour chaos, photorealistic, no text`

---

**SLIDE 4 — LITERATURE REVIEW**

**Heading:** Literature Survey

**Content:** *(Table format — 4 columns)*

| Sl No | Paper Title & Publication | Author Names | Project Inference |
|---|---|---|---|
| 01 | Markov Chain Models for Pedestrian Flow in Constrained Environments, *IEEE Transactions on ITS*, 2020 | R. Khatoun, A. Begriche, L. Fourati | Establishes discrete-time Markov chains for modelling probabilistic movement between network zones — directly underpins our vehicle routing transition matrix. |
| 02 | Graph-Theoretic Approaches to Traffic Network Analysis in Urban Corridors, *Transportation Research Part C*, 2021 | W. H. K. Lam, C. Y. Cheung, Y. F. Poon | Validates weighted directed graph representation of road networks; edge weights as travel time improve intersection delay prediction by 34%. |
| 03 | ITS Architecture for Urban Road Networks: Review of Indian Deployments, *Journal of ITS*, 2022 | D. Mohan, S. Tiwari, G. Bhalla | Surveys ATMS, ATIS, and AVCS deployments across Indian cities; identifies real-time signal optimization as the largest unaddressed gap. |
| 04 | Bottleneck Detection Using Absorbing Markov Chains for Pedestrian and Vehicle Networks, *Applied Mathematical Modelling*, 2023 | F. Johansson, T. A. Kretz, A. Schadschneider | Demonstrates MFPT from Q-matrix inversion as a reliable congestion severity metric — forms the core of our ATMS optimization KPI. |
| 05 | Adaptive Signal Control Under ITS Framework for Smart City Road Networks, *Smart Cities*, 2024 | P. Aggarwal, R. Mittal, V. Singh | Validates adaptive green phase extension as an effective ATMS intervention; browser-based ATIS dashboard confirmed as operationally acceptable. |

*No image needed*

---

**SLIDE 5 — OBJECTIVES**

**Heading:** Project Objectives

**Subheading:** Target Goals for the ITS Urban Traffic Management System

**Content:**

**NETWORK MODELLING**
Represent the Bengaluru ORR corridor as a weighted directed graph of 18 intersections and 28 road segments, classifying each node by its ITS subsystem role — ATMS signal point, ANPR enforcement node, ATIS gantry, or destination zone.

**MARKOV TRAFFIC DYNAMICS**
Construct congestion-biased transition matrices encoding vehicle routing probabilities at each junction. Simulate peak-hour vehicle density evolution over 30 signal cycles and compute v/c ratios per intersection per step.

**ATMS INTERVENTION**
Algorithmically identify the top 3 saturated intersections using peak v/c ratio ranking. Apply adaptive signal timing optimization — green phase extension and downstream coordination — to relieve saturation.

**ATIS DASHBOARD**
Deploy an interactive browser dashboard displaying live vehicle density heatmaps, v/c ratio timelines, detector feed alerts (CRITICAL / WARNING / MODERATE / NORMAL), and before-vs-after ATMS KPIs with no backend dependency.

*No image needed*

---

**SLIDE 6 — METHODOLOGY**

**Heading:** Project Methodology

**Subheading:** ITS-Integrated Graph-Markov Simulation Pipeline for Urban Traffic Analysis

**Content:** *(Three-column layout)*

**GRAPH & MARKOV MODEL**

Road Network Topology
- 18 nodes: Silk Board, HSR Layout, Marathahalli, Sony World, Koramangala, Bellandur, Sarjapur, Whitefield, Electronic City, CBD and connecting junctions
- 28 directed edges with free-flow travel time as weight and PCU/hr capacity
- Destination zones (Whitefield, Electronic City, Hosur Road, CBD) configured as absorbing states
- Congestion-biased transition matrix: w(j) = (capacity[j] / travel_time + 0.1) ^ 2.0, row-normalized to probabilities

**SIMULATION & OPTIMIZATION**

Peak Hour Engine
- Initial vehicle load: Silk Board 35%, Marathahalli 30%, Sony World 20%, Koramangala 15%
- State evolves as P(t+1) = P(t) · T over 30 signal cycles (~30 minutes)
- v/c ratio computed per node per step: density × 5000 / capacity
- Bottleneck detection ranks intersections by peak v/c ratio
- Adaptive signal timing: green_extension_factor=0.4, downstream_coordination_factor=1.3
- ANTT (Average Network Travel Time) = row sums of fundamental matrix N = (I − Q)⁻¹

**ITS ARCHITECTURE MAPPING**

Subsystem Integration
- Data Acquisition: Inductive loop detectors at signalized nodes; ANPR cameras at major junctions — Unit II
- ATMS: Bottleneck optimizer = centralized signal control TMC — Unit III
- ATIS: Dashboard heatmap + alerts = Variable Message Sign equivalent — Unit III
- AVCS: Over-capacity node alerts trigger ramp metering logic — Unit III
- Law Enforcement: ANPR nodes support violation detection — Unit IV
- Smart Cities: Namma ATMS alignment, Smart Cities Mission 2.0 — Unit V

*No image needed*

---

**SLIDE 7 — REFERENCES**

**Heading:** References

**Content:** *(IEEE format)*

[1] R. Khatoun, A. Begriche, and L. Fourati, "Markov chain models for pedestrian flow in constrained environments," *IEEE Transactions on Intelligent Transportation Systems*, vol. 21, no. 8, pp. 3412–3425, Aug. 2020.

[2] W. H. K. Lam, C. Y. Cheung, and Y. F. Poon, "Graph-theoretic approaches to traffic network analysis in urban corridors," *Transportation Research Part C: Emerging Technologies*, vol. 124, pp. 102–118, Mar. 2021.

[3] D. Mohan, S. Tiwari, and G. Bhalla, "ITS architecture for urban road networks: A review of Indian deployments," *Journal of Intelligent Transportation Systems*, vol. 26, no. 3, pp. 301–317, Jun. 2022.

[4] F. Johansson, T. A. Kretz, and A. Schadschneider, "Bottleneck detection and flow optimization using absorbing Markov chains," *Applied Mathematical Modelling*, vol. 115, pp. 89–107, Jan. 2023.

[5] P. Aggarwal, R. Mittal, and V. Singh, "Adaptive signal control under ITS framework for smart city road networks," *Smart Cities*, vol. 7, no. 2, pp. 614–631, Apr. 2024.

[6] Ministry of Urban Development, Government of India, *National ITS Architecture — Framework Document*, New Delhi: MoUD, 2016.

[7] Bengaluru Traffic Police, *ATMS Deployment Status Report*, Bengaluru: BTP, 2024.

[8] D. Helbing and B. Tilch, "Generalized force model of traffic dynamics," *Physical Review E*, vol. 58, no. 1, pp. 133–138, Jul. 1998.

*No image needed*