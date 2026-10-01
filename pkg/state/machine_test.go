package state

import (
	"testing"

	"github.com/namanbhatt-01/loop-engine-core/pkg/config"
)

func TestCircuitBreaker_IterationLimit(t *testing.T) {
	cfg := config.DefaultConfig()
	cfg.Limits.MaxIterations = 3
	cb := NewCircuitBreaker(cfg)

	// Iteration 1: Allowed
	allow, _, hitl := cb.CheckContinuation("task-1", 1, 100, 0.01)
	if !allow || hitl {
		t.Errorf("expected iteration 1 to be allowed, got allow=%v, hitl=%v", allow, hitl)
	}

	// Iteration 3: Reached max cap
	allow, reason, hitl := cb.CheckContinuation("task-1", 3, 100, 0.01)
	if allow {
		t.Errorf("expected iteration 3 to be blocked by circuit breaker")
	}
	if !hitl {
		t.Errorf("expected force_human_approval to be true")
	}
	if reason == "" {
		t.Errorf("expected non-empty reason")
	}
}

func TestCircuitBreaker_BudgetLimit(t *testing.T) {
	cfg := config.DefaultConfig()
	cfg.Limits.BudgetLimitUSD = 0.50
	cb := NewCircuitBreaker(cfg)

	// Task spends $0.60
	allow, reason, _ := cb.CheckContinuation("task-budget", 1, 5000, 0.60)
	if allow {
		t.Errorf("expected budget overrun to be blocked")
	}
	if reason == "" {
		t.Errorf("expected reason for budget block")
	}
}

func TestFSM_ValidAndInvalidTransitions(t *testing.T) {
	cfg := config.DefaultConfig()
	cb := NewCircuitBreaker(cfg)
	taskID := "task-fsm"

	// Initialize task
	cb.CheckContinuation(taskID, 0, 0, 0) // Moves from IDLE to REASONING

	// Valid transition: REASONING -> PARSED
	if err := cb.TransitionState(taskID, StateParsed); err != nil {
		t.Fatalf("expected valid transition, got: %v", err)
	}

	// Valid transition: PARSED -> VERIFYING
	if err := cb.TransitionState(taskID, StateVerifying); err != nil {
		t.Fatalf("expected valid transition, got: %v", err)
	}

	// Invalid transition: VERIFYING -> COMPLETED (must go through EVALUATED first!)
	if err := cb.TransitionState(taskID, StateCompleted); err == nil {
		t.Fatalf("expected error for illegal direct jump from VERIFYING to COMPLETED")
	}

	// Valid transition: VERIFYING -> EVALUATED
	if err := cb.TransitionState(taskID, StateEvaluated); err != nil {
		t.Fatalf("expected valid transition, got: %v", err)
	}

	// Valid transition: EVALUATED -> COMPLETED
	if err := cb.TransitionState(taskID, StateCompleted); err != nil {
		t.Fatalf("expected valid transition, got: %v", err)
	}
}
