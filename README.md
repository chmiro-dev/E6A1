# High-Assurance EDR Security & Forensics Agent

A specialized, polyglot endpoint security agent designed for deep system integrity monitoring, rootkit detection, and forensic hardening on high-stakes systems. 

## Architectural Overview

This system uses a strict **Feature-Driven Domain Architecture**[cite: 2]:
* **Go Core (`/core`)**: Manages OS service lifecycle, agent health, concurrency, and the WebAssembly (`wazero`) runtime sandbox[cite: 2].
* **Rust Collector (`/collector`)**: Low-level Windows ETW (Event Tracing for Windows) and kernel event monitoring sensor[cite: 2].
* **Wasm Rules (`/rules`)**: Sandboxed, hot-reloadable behavioral heuristics compiled from Rust to WebAssembly[cite: 2].

For detailed boundaries and specifications, see [ARCHITECTURE.md](./ARCHITECTURE.md)[cite: 2].

## Prerequisites

* **Go**: Version 1.27.1 or higher
* **Rust**: Version 1.99.0 or higher (with MSVC build tools on Windows)

## Getting Started

### 1. Build the Go Agent Core
```bash
cd core
go build -o edr-core.exe main.go