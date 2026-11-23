# Unified Build Automation for EDR Security Agent & Telemetry Platform
# Aligns with ARCHITECTURE.md directory structure

SHELL := /bin/sh

CORE_DIR := core
COLLECTOR_DIR := collector
RULES_DIR := rules
BIN_DIR := $(CORE_DIR)/bin
RULES_DIST := $(RULES_DIR)/dist

# Detect OS for binary extension
ifeq ($(OS),Windows_NT)
	EXT := .exe
else
	EXT :=
endif

.PHONY: all build build-core build-collector build-rules test clean check-isolation

all: build

## Build all polyglot components (Go Core + Rust Collector + Wasm Rules)
build: build-core build-collector build-rules

## 1. Build Go Agent Core Orchestrator
build-core:
	@echo "[*] Building Go Agent Core..."
	@mkdir -p $(BIN_DIR)
	cd $(CORE_DIR) && go build -o bin/edr-core$(EXT) main.go

## 2. Build Rust ETW Telemetry Collector
build-collector:
	@echo "[*] Building Rust ETW Telemetry Collector..."
	cd $(COLLECTOR_DIR) && cargo build --release

## 3. Compile Rust Detection Heuristics to WebAssembly (.wasm)
## Note: Requires 'rules/Cargo.toml' (WBS Step 5.2.1)
build-rules:
	@echo "[*] Building Wasm Detection Rules..."
	@if [ -f "$(RULES_DIR)/Cargo.toml" ]; then \
		mkdir -p $(RULES_DIST); \
		cd $(RULES_DIR) && cargo build --target wasm32-unknown-unknown --release; \
	else \
		echo "[!] Skipping Wasm rules build: $(RULES_DIR)/Cargo.toml not yet created (WBS 5.2.1)."; \
	fi

## Run unit tests across Go and Rust workspaces
test:
	@echo "[*] Running Go Core tests..."
	cd $(CORE_DIR) && go test ./...
	@echo "[*] Running Rust Collector tests..."
	cd $(COLLECTOR_DIR) && cargo test

## Audit architectural boundary rules (forbids direct networking imports in collector/)
check-isolation:
	@echo "[*] Auditing collector/ for forbidden networking crates..."
	@if grep -E "reqwest|hyper|tokio::net|std::net" $(COLLECTOR_DIR)/Cargo.toml $(COLLECTOR_DIR)/src/*.rs 2>/dev/null; then \
		echo "[ERROR] Architecture violation: network library detected in collector/!"; \
		exit 1; \
	else \
		echo "[OK] Collector sensor isolation verified."; \
	fi

## Clean build artifacts
clean:
	@echo "[*] Cleaning build artifacts..."
	rm -rf $(BIN_DIR) $(RULES_DIST)
	cd $(COLLECTOR_DIR) && cargo clean
