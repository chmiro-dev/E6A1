package main

import (
	"context"
	"fmt"
	"log"
	"os"
	"os/signal"
	"syscall"
	"time"
)

type AgentCore struct {
	isrunning bool
}

func NewAgentCore() *AgentCore {
	return &AgentCore{isrunning: false}
}

func (a *AgentCore) Start(ctx context.Context) error {
	a.isrunning = true
	log.Println("[+] Go Agent Core successfully initialized and running.")

	// Main orchestration loop
	// In production, this manages the Wasm engine, IPC server, and telemetry pipeline.
	ticker := time.NewTicker(3 * time.Second)
	defer ticker.Stop()

	for {
		select {
		case <-ctx.Done():
			log.Println("[*] Stop signal received. Initiating graceful shutdown...")
			return a.Stop()
		case <-ticker.C:
			// Placeholder: Periodic health check or telemetry queue status check
			log.Println("[*] Agent core active. Monitoring telemetry pipeline...")
		}
	}
}

func (a *AgentCore) Stop() error {
	// Perform cleanup tasks: flush logs, close IPC handles to the Rust collector, unload Wasm modules
	log.Println("[*] Flushing buffers and closing IPC channels...")
	time.Sleep(1 * time.Second) // Simulate teardown work
	a.isrunning = false
	log.Println("[+] Agent core shut down cleanly.")
	return nil
}

func main() {
	log.Println("[*] Starting EDR Agent Orchestrator (Go Core)...")

	// Create a root context that cancels on termination signals
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	// Set up OS signal interception (SIGINT, SIGTERM, and Windows equivalent handling)
	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, os.Interrupt, syscall.SIGINT, syscall.SIGTERM)

	agent := NewAgentCore()

	// Run the agent core in a separate goroutine so we can block on signals below
	errChan := make(chan error, 1)
	go func() {
		if err := agent.Start(ctx); err != nil {
			errChan <- err
		}
	}()

	// Block until we receive a termination signal or an error occurs
	select {
	case sig := <-sigChan:
		fmt.Printf("\n[!] Captured OS Signal: %v\n", sig)
		cancel() // Trigger context cancellation for graceful shutdown
	case err := <-errChan:
		log.Fatalf("[!] Agent core encountered a fatal error: %v", err)
	}

	// Give the shutdown routine a brief moment to finish logging
	time.Sleep(500 * time.Millisecond)
	log.Println("[*] Agent process exited successfully.")
}
