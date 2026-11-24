# Unified Build Automation for EDR Security Agent & Telemetry Platform
# Uses Python helpers where shell builtins/utilities differ across Windows
# (cmd.exe / PowerShell) and macOS/Linux (POSIX sh).

CORE_DIR := core
COLLECTOR_DIR := collector
RULES_DIR := rules
BIN_DIR := $(CORE_DIR)/bin
RULES_DIST := $(RULES_DIR)/dist

PYTHON ?= python
SUITE ?= all
VERIFY_LOG ?= logs/phase1_verify.log
VERIFY_SCRIPT := ../verify_phase1.py

# Detect OS for binary extension
ifeq ($(OS),Windows_NT)
	EXT := .exe
else
	EXT :=
endif

.PHONY: all build build-core build-collector build-rules test clean check-isolation verify-phase1

all: build

## Build all polyglot components (Go Core + Rust Collector + Wasm Rules)
build: build-core build-collector build-rules

## 1. Build Go Agent Core Orchestrator
build-core:
	@echo "[*] Building Go Agent Core..."
	@$(PYTHON) -c "import os, subprocess, sys; os.makedirs('$(BIN_DIR)', exist_ok=True); sys.exit(subprocess.call(['go', 'build', '-o', 'bin/edr-core$(EXT)', 'main.go'], cwd='$(CORE_DIR)'))"

## 2. Build Rust ETW Telemetry Collector
build-collector:
	@echo "[*] Building Rust ETW Telemetry Collector..."
	@$(PYTHON) -c "import subprocess, sys; sys.exit(subprocess.call(['cargo', 'build', '--release'], cwd='$(COLLECTOR_DIR)'))"

## 3. Compile Rust Detection Heuristics to WebAssembly (.wasm)
## Note: Requires 'rules/Cargo.toml' (WBS Step 5.2.1)
build-rules:
	@echo "[*] Building Wasm Detection Rules..."
	@$(PYTHON) -c "import os, subprocess, sys; cargo_toml = os.path.join('$(RULES_DIR)', 'Cargo.toml'); (print('[!] Skipping Wasm rules build: $(RULES_DIR)/Cargo.toml not yet created (WBS 5.2.1).') or sys.exit(0)) if not os.path.isfile(cargo_toml) else (os.makedirs('$(RULES_DIST)', exist_ok=True), sys.exit(subprocess.call(['cargo', 'build', '--target', 'wasm32-unknown-unknown', '--release'], cwd='$(RULES_DIR)')))"

## Run unit tests across Go and Rust workspaces
test:
	@echo "[*] Running Go Core tests..."
	@$(PYTHON) -c "import subprocess, sys; sys.exit(subprocess.call(['go', 'test', './...'], cwd='$(CORE_DIR)'))"
	@echo "[*] Running Rust Collector tests..."
	@$(PYTHON) -c "import subprocess, sys; sys.exit(subprocess.call(['cargo', 'test'], cwd='$(COLLECTOR_DIR)'))"

## Audit architectural boundary rules (forbids direct networking imports in collector/)
check-isolation:
	@echo "[*] Auditing collector/ for forbidden networking crates..."
	@$(PYTHON) -c "import glob, os, re, sys; pat = re.compile(r'\\b(reqwest|hyper)\\b|tokio::net|std::net'); targets = [os.path.join('$(COLLECTOR_DIR)', 'Cargo.toml')] + glob.glob(os.path.join('$(COLLECTOR_DIR)', 'src', '*.rs')); hits = [(p, i+1, line.strip()) for p in targets if os.path.isfile(p) for i, line in enumerate(open(p, encoding='utf-8', errors='replace')) if pat.search(line)]; (print('\\n'.join(f'{p}:{ln}: {txt}' for p, ln, txt in hits)), print('[ERROR] Architecture violation: network library detected in collector/!'), sys.exit(1)) if hits else print('[OK] Collector sensor isolation verified.')"

## Run modular Phase 1 verification suite and write session log
verify-phase1:
	@echo "[*] Running Phase 1 verification (suite=$(SUITE))..."
	$(PYTHON) $(VERIFY_SCRIPT) --root .. --suite $(SUITE) --verbose --log-file $(VERIFY_LOG)

## Clean build artifacts
clean:
	@echo "[*] Cleaning build artifacts..."
	@$(PYTHON) -c "import shutil, subprocess, sys; [shutil.rmtree(d, ignore_errors=True) for d in ('$(BIN_DIR)', '$(RULES_DIST)')]; sys.exit(subprocess.call(['cargo', 'clean'], cwd='$(COLLECTOR_DIR)'))"