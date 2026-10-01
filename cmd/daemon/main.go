package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/namanbhatt-01/loop-engine-core/pkg/config"
	"github.com/namanbhatt-01/loop-engine-core/pkg/sandbox"
	"github.com/namanbhatt-01/loop-engine-core/pkg/state"
	"github.com/namanbhatt-01/loop-engine-core/pkg/tdd"
)

type ControlDaemon struct {
	Config   *config.LoopConfig
	Runner   *tdd.TestRunner
	Breaker  *state.CircuitBreaker
	Worktree *sandbox.WorktreeManager
}

type VerificationReq struct {
	TaskID      string `json:"task_id"`
	ProjectRoot string `json:"project_root"`
	TestCmd     string `json:"test_command"`
}

type CircuitReq struct {
	TaskID      string  `json:"task_id"`
	Iteration   int     `json:"iteration"`
	AddedTokens int     `json:"added_tokens"`
	AddedCost   float64 `json:"added_cost"`
}

func main() {
	port := os.Getenv("LOOP_PORT")
	if port == "" {
		port = "50051"
	}

	workDir, _ := os.Getwd()
	cfg, err := config.LoadConfig(workDir)
	if err != nil {
		log.Fatalf("Failed to load Loopfile config: %v", err)
	}

	daemon := &ControlDaemon{
		Config:   cfg,
		Runner:   tdd.NewTestRunner(cfg),
		Breaker:  state.NewCircuitBreaker(cfg),
		Worktree: sandbox.NewWorktreeManager(workDir),
	}

	mux := http.NewServeMux()
	mux.HandleFunc("/verify", daemon.handleVerify)
	mux.HandleFunc("/circuit", daemon.handleCircuit)
	mux.HandleFunc("/health", daemon.handleHealth)
	mux.HandleFunc("/metrics", daemon.handleMetrics)

	addr := fmt.Sprintf("127.0.0.1:%s", port)
	server := &http.Server{
		Addr:    addr,
		Handler: mux,
	}

	// Trap OS termination signals for clean, graceful daemon shutdown
	stopChan := make(chan os.Signal, 1)
	signal.Notify(stopChan, os.Interrupt, syscall.SIGTERM)

	go func() {
		log.Printf("🚀 Loop Engine Go Control Plane Daemon running on %s (Project: %s, Lang: %s)", addr, cfg.Project.Name, cfg.Project.Language)
		if err := server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatalf("Daemon server failed: %v", err)
		}
	}()

	<-stopChan
	log.Println("🛑 Shutdown signal received. Performing graceful shutdown...")

	shutdownCtx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	if err := server.Shutdown(shutdownCtx); err != nil {
		log.Printf("Error during server shutdown: %v", err)
	}
	log.Println("👋 Control Plane Daemon safely exited.")
}

func (d *ControlDaemon) handleVerify(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed. Use POST.", http.StatusMethodNotAllowed)
		return
	}

	var req VerificationReq
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, fmt.Sprintf("Bad Request: %v", err), http.StatusBadRequest)
		return
	}

	root := req.ProjectRoot
	if root == "" {
		root = d.Config.Project.Root
	}

	res, err := d.Runner.RunVerification(r.Context(), root, req.TestCmd)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(res)
}

func (d *ControlDaemon) handleCircuit(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed. Use POST.", http.StatusMethodNotAllowed)
		return
	}

	var req CircuitReq
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, fmt.Sprintf("Bad Request: %v", err), http.StatusBadRequest)
		return
	}

	allow, reason, forceHitl := d.Breaker.CheckContinuation(req.TaskID, req.Iteration, req.AddedTokens, req.AddedCost)

	resp := map[string]interface{}{
		"allow_continuation":   allow,
		"reason":               reason,
		"force_human_approval": forceHitl,
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(resp)
}

func (d *ControlDaemon) handleHealth(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]string{
		"status":   "healthy",
		"language": d.Config.Project.Language,
		"project":  d.Config.Project.Name,
	})
}

func (d *ControlDaemon) handleMetrics(w http.ResponseWriter, r *http.Request) {
	taskID := r.URL.Query().Get("task_id")
	if taskID == "" {
		http.Error(w, "Missing task_id query parameter", http.StatusBadRequest)
		return
	}

	metrics, ok := d.Breaker.GetMetrics(taskID)
	if !ok {
		http.Error(w, "Task not found", http.StatusNotFound)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(metrics)
}
