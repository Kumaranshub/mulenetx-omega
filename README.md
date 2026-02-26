<div align="center">

<img src="https://img.shields.io/badge/status-active%20research-brightgreen?style=for-the-badge" />
<img src="https://img.shields.io/badge/license-MIT-blue?style=for-the-badge" />
<img src="https://img.shields.io/badge/build-passing-success?style=for-the-badge" />
<img src="https://img.shields.io/github/last-commit/Kumaranshub/mulenetx-omega?style=for-the-badge" />

<br />
<br />

```
███╗   ███╗██╗   ██╗██╗     ███████╗███╗   ██╗███████╗████████╗██╗  ██╗
████╗ ████║██║   ██║██║     ██╔════╝████╗  ██║██╔════╝╚══██╔══╝╚██╗██╔╝
██╔████╔██║██║   ██║██║     █████╗  ██╔██╗ ██║█████╗     ██║    ╚███╔╝ 
██║╚██╔╝██║██║   ██║██║     ██╔══╝  ██║╚██╗██║██╔══╝     ██║    ██╔██╗ 
██║ ╚═╝ ██║╚██████╔╝███████╗███████╗██║ ╚████║███████╗   ██║   ██╔╝ ██╗
╚═╝     ╚═╝ ╚═════╝ ╚══════╝╚══════╝╚═╝  ╚═══╝╚══════╝   ╚═╝   ╚═╝  ╚═╝
                              OMEGA
```

### *Distributed Mule-Account Detection via Graph Analytics, Stochastic Modeling, and Thermodynamic Flow*

<br />

[**Architecture**](#architecture) · [**Research**](#research-foundations) · [**Stack**](#technology-stack) · [**Setup**](#getting-started) · [**Machines**](#deployment) · [**Docs**](docs/)

<br />

</div>

---

## What Is This

MuleNetX Omega is a **distributed, research-grade financial fraud detection platform** built to discover unknown mule-account networks in real time. It does not match rules written by analysts. It learns the structure of fraud from the graph itself.

The system treats a financial network the way a physicist treats a thermodynamic system — money is energy, accounts are nodes, and mule accounts violate conservation principles in ways that are mathematically detectable before any individual transaction triggers an alert. It finds fraud campaigns by detecting when the network *structure itself* shifts, not just when individual accounts behave badly.

This is not a wrapper around a pre-trained model. Every core component — the graph engine, the flow solver, the online GNN, the phase-shift detector — is purpose-built for this problem.

---

## Research Foundations

### Thermodynamic Flow Analysis
The transaction graph is modeled as a resistive electrical network. Each account holds a *flow potential* — a scalar value representing its net pressure in the money-flow field. Mule accounts, regardless of transaction volume, converge toward near-zero potential because they conserve value locally while acting as pure conductors. This is detectable via the Laplacian flow equation `L·φ = b`, solved in real time as the graph evolves.

### Stochastic Structural Baselines
Rather than fixed fraud thresholds, the system maintains a continuously updated probabilistic model of normal graph behavior — degree distributions, clustering coefficients, community entropy, flow variance. Any observation that falls in the tail of that distribution is anomalous by definition. As behavior drifts, the baseline drifts with it using ADWIN-based concept drift detection.

### Graph Neural Network with Native Explainability
A 3-layer hybrid GATv2 + GraphSAGE architecture scores every account based on its full neighborhood context. The GAT attention mechanism is not a black box — it is the explanation. Every fraud score comes with a ranked list of the neighboring accounts that drove it, ready to render as an influence subgraph without any post-hoc approximation.

### Phase-Shift Detection
The system watches the network's macro-state as a dynamical system — spectral features, modularity, flow entropy — and applies change-point detection (PELT algorithm) to their time series. When the macro-state shifts, a campaign-level alert fires. This is the early warning signal that arrives **before** individual account scores catch up.

### Adversarial Continual Learning
The generative model is turned against the detector. The simulation layer synthesizes fraud patterns that the current model nearly misses, injects them into the training buffer, and triggers incremental fine-tuning. The detector adapts to its own blind spots.

---

## Technology Stack

This system is deliberately polyglot. Each language is chosen for a concrete performance or expressiveness reason, not preference.

| Layer | Language | Why |
|---|---|---|
| **Graph Core** | `Rust` | Zero-GC, cache-efficient CSR operations. No GC pause during live graph traversal. Compiled to shared library, called via FFI. |
| **Streaming Engine** | `Go` | Goroutine-native concurrency for Redpanda ingest and gRPC service layer. 4–5× faster than Python for I/O-bound streaming at this scale. |
| **Math & Physics** | `Julia` | Near-C performance with native mathematical syntax. Thermodynamic solvers, spectral analysis, and stochastic models written as equations, not loops. |
| **ML Pipeline** | `Python` | PyTorch Geometric is the honest choice for GNNs. No substitute exists. |
| **Dashboard** | `TypeScript + React + D3` | D3 force-directed graph renders 50K nodes in-browser. Full control over every visual element. WebSocket-native for live updates. |
| **Schemas** | `Protobuf` | Single source of truth for all data contracts between all languages and all machines. |
| **Config** | `YAML / TOML` | Zero hardcoded values anywhere in the codebase. |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     FOUR-MACHINE CLUSTER                        │
├───────────────────────┬─────────────────────────────────────────┤
│   ARCH LINUX (Brain)  │  Everything analytically meaningful     │
│   i5-12450H           │  runs here.                             │
│   16 GB RAM           │                                         │
│   12 Threads          │  • Rust graph engine (CSR, sampling)    │
│   Intel Iris Xe       │  • Go ingest + gRPC service layer       │
│                       │  • Julia flow solver + phase detector   │
│                       │  • Python GNN (training + inference)    │
│                       │  • Redpanda broker (central bus)        │
│                       │  • Redis (shared state)                 │
│                       │  • MLflow (experiment tracking)         │
├───────────────────────┼─────────────────────────────────────────┤
│   Machine 2 (Pump)    │  Synthetic transaction generation.      │
│                       │  Pushes to Redpanda on Arch machine.    │
│                       │  200K–500K transactions/sec.            │
├───────────────────────┼─────────────────────────────────────────┤
│   Machine 3 (Storage) │  PostgreSQL alert archive.              │
│                       │  Compressed graph snapshot store.       │
│                       │  Nginx file server for exports.         │
├───────────────────────┼─────────────────────────────────────────┤
│   Machine 4 (Viz)     │  React + D3 dashboard.                  │
│                       │  Grafana operational monitoring.        │
│                       │  Live WebSocket feed from Go service.   │
└───────────────────────┴─────────────────────────────────────────┘

         All machines communicate over gRPC + Protobuf
                   Message bus: Redpanda
                   State store:  Redis
```

### Thread Allocation on the i5-12450H

```
P-Cores (0–7)  →  GNN inference · Graph updates · Flow solver · Stochastic engine
E-Cores (8–11) →  Background retraining · MLflow logging · Redpanda broker
Iris Xe GPU    →  GNN inference acceleration via Intel Extension for PyTorch
```

---

## Repository Structure

```
mulenetx-omega/
│
├── core/                        # Rust — graph storage engine
│   ├── src/
│   │   ├── graph/
│   │   │   ├── csr.rs           # Compressed Sparse Row graph
│   │   │   ├── sampler.rs       # Neighborhood sampling
│   │   │   └── metrics.rs       # Degree, clustering, betweenness
│   │   └── ffi/
│   │       ├── python.rs        # PyO3 Python bindings
│   │       └── go.rs            # cbindgen C ABI for Go
│   └── Cargo.toml
│
├── engine/                      # Go — streaming + service layer
│   ├── cmd/
│   │   ├── ingest/main.go       # Redpanda consumer
│   │   └── server/main.go       # gRPC server
│   └── internal/
│       ├── stream/              # Consumer + producer
│       ├── scorer/              # Subgraph dispatcher to Python
│       └── alerts/              # Alert publisher
│
├── physics/                     # Julia — math engine
│   ├── ThermodynamicFlow.jl     # Laplacian solver, mule score
│   ├── StochasticBaseline.jl    # KDE baselines, ADWIN drift
│   ├── PhaseShiftDetector.jl    # PELT change-point detection
│   └── SpectralAnalysis.jl      # Eigenvalue graph analysis
│
├── analysis/                    # Python — GNN + ML pipeline
│   ├── models/
│   │   ├── gnn.py               # GATv2 + GraphSAGE architecture
│   │   ├── explainer.py         # Attention-based explanation
│   │   └── online_learner.py    # Continual learning orchestrator
│   └── simulation/
│       ├── generator.py         # Synthetic fraud generation
│       └── adversarial.py       # Hard negative synthesis
│
├── dashboard/                   # TypeScript + React + D3
│   └── src/
│       ├── components/
│       │   ├── GraphCanvas.tsx  # D3 force-directed live graph
│       │   ├── AlertTimeline.tsx
│       │   ├── RiskScorePanel.tsx
│       │   └── ExplainSubgraph.tsx
│       └── hooks/
│           ├── useWebSocket.ts
│           └── useGraphState.ts
│
├── proto/                       # Protobuf schemas (source of truth)
│   ├── transaction.proto
│   ├── graph_state.proto
│   ├── risk_score.proto
│   └── alert.proto
│
├── data/                        # Schemas + fraud templates
│   ├── schema.sql
│   └── fraud_templates/
│       ├── fan_out.yaml
│       ├── layering_ring.yaml
│       └── smurfing.yaml
│
├── docs/                        # Research documentation
│   ├── architecture.md
│   ├── math_primer.md
│   ├── api_reference.md
│   └── getting_started.md
│
├── deploy/                      # Docker + machine configs
│   ├── docker-compose.yml
│   └── machines/
│       ├── arch_engine.env
│       ├── pump.env
│       ├── storage.env
│       └── viz.env
│
├── Makefile
├── .env.example
└── README.md
```

---

## Getting Started

### Prerequisites

| Tool | Version | Required on |
|---|---|---|
| Rust + Cargo | ≥ 1.78 | Arch machine |
| Go | ≥ 1.22 | Arch + Machine 2 |
| Julia | ≥ 1.10 | Arch machine |
| Python | ≥ 3.11 | Arch + Machine 2 |
| Node.js | ≥ 20 | Machine 4 |
| Docker + Compose | latest | All machines |
| Redpanda | latest | Arch machine |
| PostgreSQL | ≥ 16 | Machine 3 |

### Quick Start (Single Machine for Development)

```bash
# Clone
git clone https://github.com/Kumaranshub/mulenetx-omega.git
cd mulenetx-omega

# Build everything
make build

# Generate synthetic data and start the full pipeline
make generate &
make demo
```

### Multi-Machine Deployment

Each machine reads its role from a `.env` file:

```bash
# On Arch machine (Brain)
cp deploy/machines/arch_engine.env .env
docker compose up

# On Machine 2 (Pump)
cp deploy/machines/pump.env .env
docker compose up

# On Machine 3 (Storage)
cp deploy/machines/storage.env .env
docker compose up

# On Machine 4 (Visualization)
cp deploy/machines/viz.env .env
docker compose up
```

---

## Deployment

### Makefile Commands

```bash
make build       # Compile Rust core, Go engine, TypeScript dashboard
make generate    # Start synthetic transaction pump
make train       # Run GNN training pipeline
make demo        # Launch full stack + open dashboard
make test        # Run test suites across all languages
make snapshot    # Serialize current graph state to disk
make clean       # Tear down all services
```

---

## Synthetic Data Capacity

Benchmarked on the i5-12450H with 16GB RAM:

| Metric | Comfortable | Maximum |
|---|---|---|
| Accounts (nodes) | 3–5 million | 7 million |
| Transactions (edges) | 20–30 million | 40 million |
| Transaction throughput | 80K–120K / sec | 500K / sec (generation) |
| GNN inference | 200K nodes / sec (CPU) | 600K+ (Iris Xe) |
| Phase-shift latency | < 2 seconds | — |

Data is **streamed, not stored**. The generator produces synthetic transactions on demand using fixed random seeds — the full dataset is reproducible from a 4KB config file without storing a single transaction on disk.

---

## Research Novelty

This system makes the following claims that are not standard in existing fraud detection literature:

- **Thermodynamic potential as a mule signal** — flow potential computed from the graph Laplacian as a real-time fraud feature, not derived analytically post-hoc
- **Phase-transition alerts** — network macro-state monitoring as an early-warning system that fires before individual account scores propagate
- **Attention-native explainability** — explanation is not a post-hoc approximation; it is the forward pass of the GNN itself
- **Adversarial continual retraining** — the generative model is weaponized against the detector to expose and close blind spots automatically
- **Polyglot performance architecture** — right tool for each layer rather than forcing a single language to handle computation it was not designed for

---

## License

MIT — see [LICENSE](LICENSE) for details.

---

## Author

**Kumaran** — [@Kumaranshub](https://github.com/Kumaranshub)

<div align="center">
<br />
<i>Built to outperform, designed to explain, engineered to adapt.</i>
</div>
