# ================================================================
#  MuleNetX Omega
#  Distributed Mule-Account Detection Platform
#  Rust · Go · Julia · Python · TypeScript
# ================================================================

.PHONY: help proto core engine physics analysis dashboard \
        build generate train demo test snapshot clean

# Colours
BOLD   := \033[1m
GREEN  := \033[32m
CYAN   := \033[36m
YELLOW := \033[33m
RED    := \033[31m
RESET  := \033[0m

# ----------------------------------------------------------------
#  help — shown when you just type: make
# ----------------------------------------------------------------

help:
	@echo ""
	@echo "$(BOLD)  MuleNetX Omega$(RESET)"
	@echo "  Distributed mule-account detection across four machines."
	@echo ""
	@echo "$(CYAN)  Build$(RESET)"
	@echo "    make proto        Generate protobuf bindings for Go + Python"
	@echo "    make core         Compile the Rust graph engine"
	@echo "    make engine       Compile the Go streaming + gRPC server"
	@echo "    make physics      Instantiate the Julia environment"
	@echo "    make analysis     Set up the Python ML environment"
	@echo "    make dashboard    Install the React + D3 frontend deps"
	@echo "    make build        Do all of the above in order"
	@echo ""
	@echo "$(CYAN)  Run$(RESET)"
	@echo "    make generate     Start the synthetic transaction pump"
	@echo "    make train        Run the GNN training pipeline"
	@echo "    make demo         Launch the full stack + open the dashboard"
	@echo ""
	@echo "$(CYAN)  Other$(RESET)"
	@echo "    make test         Run tests across all layers"
	@echo "    make snapshot     Save current graph state to disk"
	@echo "    make clean        Remove all build artifacts"
	@echo ""

# ----------------------------------------------------------------
#  proto — generate bindings for Go and Python from .proto files
# ----------------------------------------------------------------

proto:
	@echo "$(CYAN)  Generating protobuf bindings...$(RESET)"
	@protoc \
		--go_out=engine/pkg/proto \
		--go-grpc_out=engine/pkg/proto \
		proto/*.proto
	@. .venv/bin/activate && python -m grpc_tools.protoc \
		-I proto \
		--python_out=analysis \
		--grpc_python_out=analysis \
		proto/*.proto
	@echo "$(GREEN)  Done — bindings written to engine/pkg/proto and analysis/$(RESET)"

# ----------------------------------------------------------------
#  core — Rust graph engine
# ----------------------------------------------------------------

core:
	@echo "$(CYAN)  Building Rust graph engine...$(RESET)"
	@echo "  This compiles the CSR graph core, neighbor sampler,"
	@echo "  and FFI bindings for Go and Python."
	@cd core && cargo build --release
	@echo "$(GREEN)  Done — binary at core/target/release/$(RESET)"

# ----------------------------------------------------------------
#  engine — Go streaming + gRPC service layer
# ----------------------------------------------------------------

engine:
	@echo "$(CYAN)  Building Go engine...$(RESET)"
	@echo "  Compiling the Redpanda ingest consumer and gRPC server."
	@cd engine && go mod tidy
	@cd engine/cmd/server && go build -o server .
	@cd engine/cmd/ingest && go build -o ingest .
	@echo "$(GREEN)  Done — binaries at engine/cmd/server and engine/cmd/ingest$(RESET)"

# ----------------------------------------------------------------
#  physics — Julia environment
# ----------------------------------------------------------------

physics:
	@echo "$(CYAN)  Setting up Julia physics environment...$(RESET)"
	@echo "  Instantiating packages: thermodynamic solver, PELT"
	@echo "  change-point detector, spectral analysis."
	@julia --project=physics -e 'using Pkg; Pkg.instantiate()'
	@echo "$(GREEN)  Done — Julia environment ready$(RESET)"

# ----------------------------------------------------------------
#  analysis — Python ML environment
# ----------------------------------------------------------------

analysis:
	@echo "$(CYAN)  Setting up Python ML environment...$(RESET)"
	@echo "  Creating virtualenv and installing PyTorch Geometric,"
	@echo "  River, MLflow, and the rest of the analysis stack."
	@python3 -m venv .venv
	@. .venv/bin/activate && pip install --quiet --upgrade pip
	@. .venv/bin/activate && pip install --quiet -r analysis/requirements.txt
	@echo "$(GREEN)  Done — activate with: source .venv/bin/activate$(RESET)"

# ----------------------------------------------------------------
#  dashboard — React + D3 frontend
# ----------------------------------------------------------------

dashboard:
	@echo "$(CYAN)  Installing dashboard dependencies...$(RESET)"
	@echo "  React, D3, TypeScript, Vite, WebSocket client."
	@cd dashboard && npm install --silent
	@echo "$(GREEN)  Done — start with: cd dashboard && npm run dev$(RESET)"

# ----------------------------------------------------------------
#  build — build everything in the right order
# ----------------------------------------------------------------

build: proto core engine physics analysis dashboard
	@echo ""
	@echo "$(GREEN)$(BOLD)  Everything built successfully.$(RESET)"
	@echo "  Run $(BOLD)make demo$(RESET) to start the full stack."
	@echo ""

# ----------------------------------------------------------------
#  generate — start the synthetic transaction pump
# ----------------------------------------------------------------

generate:
	@echo "$(CYAN)  Starting synthetic transaction pump...$(RESET)"
	@echo "  Generating accounts, transactions, and fraud ring"
	@echo "  injections from templates in data/fraud_templates/."
	@. .venv/bin/activate && python analysis/simulation/generator.py

# ----------------------------------------------------------------
#  train — run the GNN training pipeline
# ----------------------------------------------------------------

train:
	@echo "$(CYAN)  Starting GNN training pipeline...$(RESET)"
	@echo "  Graph sampling → GATv2 forward pass → loss → update."
	@echo "  MLflow tracking at http://localhost:5000"
	@. .venv/bin/activate && python analysis/training/train.py

# ----------------------------------------------------------------
#  demo — launch the full stack
# ----------------------------------------------------------------

demo:
	@echo ""
	@echo "$(BOLD)  Launching MuleNetX Omega...$(RESET)"
	@echo ""
	@echo "  $(CYAN)Services starting:$(RESET)"
	@echo "    Redpanda broker       → localhost:9092"
	@echo "    Redis state store     → localhost:6379"
	@echo "    Go gRPC server        → localhost:50051"
	@echo "    MLflow tracking UI    → localhost:5000"
	@echo "    React dashboard       → localhost:5173"
	@echo ""
	docker compose -f deploy/docker-compose.yml up

# ----------------------------------------------------------------
#  test — run all test suites
# ----------------------------------------------------------------

test:
	@echo "$(CYAN)  Running Rust tests...$(RESET)"
	@cd core && cargo test
	@echo "$(CYAN)  Running Go tests...$(RESET)"
	@cd engine && go test ./...
	@echo "$(CYAN)  Running Python tests...$(RESET)"
	@. .venv/bin/activate && python -m pytest analysis/
	@echo "$(CYAN)  Running TypeScript tests...$(RESET)"
	@cd dashboard && npm test -- --watchAll=false
	@echo "$(GREEN)  All tests passed.$(RESET)"

# ----------------------------------------------------------------
#  snapshot — serialise the current graph state to disk
# ----------------------------------------------------------------

snapshot:
	@echo "$(CYAN)  Taking graph snapshot...$(RESET)"
	@. .venv/bin/activate && python -c \
		"from analysis.models.online_learner import snapshot; snapshot()"
	@echo "$(GREEN)  Snapshot saved to data/snapshots/$(RESET)"

# ----------------------------------------------------------------
#  clean — remove all build artifacts
# ----------------------------------------------------------------

clean:
	@echo "$(YELLOW)  Cleaning build artifacts...$(RESET)"
	@rm -rf core/target
	@rm -rf engine/cmd/server/server
	@rm -rf engine/cmd/ingest/ingest
	@rm -rf .venv
	@rm -rf dashboard/node_modules
	@rm -rf dashboard/dist
	@find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@find . -name "*.pyc" -delete 2>/dev/null || true
	@echo "$(GREEN)  Clean.$(RESET)"
