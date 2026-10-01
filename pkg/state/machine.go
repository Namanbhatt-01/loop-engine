package state

import (
	"fmt"
	"sync"
	"time"

	"github.com/namanbhatt-01/loop-engine-core/pkg/config"
)

type AgentState string

const (
	StateIdle      AgentState = "IDLE"
	StateReasoning AgentState = "REASONING"
	StateParsed    AgentState = "PARSED"
	StateVerifying AgentState = "VERIFYING"
	StateEvaluated AgentState = "EVALUATED"
	StateHalted    AgentState = "HALTED"
	StateCompleted AgentState = "COMPLETED"
)

// validTransitions defines deterministic FSM transition rules
var validTransitions = map[AgentState]map[AgentState]bool{
	StateIdle: {
		StateReasoning: true,
	},
	StateReasoning: {
		StateParsed: true,
		StateHalted: true,
	},
	StateParsed: {
		StateVerifying: true,
		StateHalted:    true,
	},
	StateVerifying: {
		StateEvaluated: true,
		StateHalted:    true,
	},
	StateEvaluated: {
		StateReasoning: true, // Retry loop
		StateCompleted: true, // Success completion
		StateHalted:    true, // Final circuit failure
	},
	StateHalted:    {}, // Terminal
	StateCompleted: {}, // Terminal
}

// ExecutionMetrics tracks real-time usage for circuit breakers
type ExecutionMetrics struct {
	CurrentIteration int        `json:"current_iteration"`
	MaxIterations    int        `json:"max_iterations"`
	TotalTokens      int        `json:"total_tokens"`
	EstimatedCostUSD float64    `json:"estimated_cost_usd"`
	BudgetLimitUSD   float64    `json:"budget_limit_usd"`
	CurrentState     AgentState `json:"current_state"`
	StartTime        time.Time  `json:"start_time"`
}

// CircuitBreaker enforces strict limits on autonomous agent execution
type CircuitBreaker struct {
	mu     sync.Mutex
	Config *config.LoopConfig
	Tasks  map[string]*ExecutionMetrics
}

func NewCircuitBreaker(cfg *config.LoopConfig) *CircuitBreaker {
	return &CircuitBreaker{
		Config: cfg,
		Tasks:  make(map[string]*ExecutionMetrics),
	}
}

// CheckContinuation determines if a task is allowed to proceed to the next iteration
func (cb *CircuitBreaker) CheckContinuation(taskID string, currentIter int, addedTokens int, addedCost float64) (bool, string, bool) {
	cb.mu.Lock()
	defer cb.mu.Unlock()

	metrics, exists := cb.Tasks[taskID]
	if !exists {
		metrics = &ExecutionMetrics{
			CurrentIteration: 0,
			MaxIterations:    cb.Config.Limits.MaxIterations,
			TotalTokens:      0,
			EstimatedCostUSD: 0,
			BudgetLimitUSD:   cb.Config.Limits.BudgetLimitUSD,
			CurrentState:     StateIdle,
			StartTime:        time.Now(),
		}
		cb.Tasks[taskID] = metrics
	}

	metrics.CurrentIteration = currentIter
	metrics.TotalTokens += addedTokens
	metrics.EstimatedCostUSD += addedCost

	// 1. Check Iteration Cap
	if currentIter >= metrics.MaxIterations {
		metrics.CurrentState = StateHalted
		return false, fmt.Sprintf("Circuit Breaker Exceeded: current iteration %d reached max ceiling of %d", currentIter, metrics.MaxIterations), true
	}

	// 2. Check Dollar Budget Limit
	if metrics.EstimatedCostUSD >= metrics.BudgetLimitUSD {
		metrics.CurrentState = StateHalted
		return false, fmt.Sprintf("Circuit Breaker Exceeded: cost $%.4f reached hard limit $%.2f", metrics.EstimatedCostUSD, metrics.BudgetLimitUSD), true
	}

	metrics.CurrentState = StateReasoning
	return true, "Allowed continuation", false
}

// TransitionState updates the task state machine with strict formal validation
func (cb *CircuitBreaker) TransitionState(taskID string, newState AgentState) error {
	cb.mu.Lock()
	defer cb.mu.Unlock()

	metrics, exists := cb.Tasks[taskID]
	if !exists {
		return fmt.Errorf("task %q does not exist in state machine", taskID)
	}

	currentState := metrics.CurrentState
	allowedTargets, ok := validTransitions[currentState]
	if !ok || !allowedTargets[newState] {
		return fmt.Errorf("invalid FSM state transition: %s -> %s", currentState, newState)
	}

	metrics.CurrentState = newState
	return nil
}

// GetMetrics returns a copy of metrics for telemetry inspection
func (cb *CircuitBreaker) GetMetrics(taskID string) (*ExecutionMetrics, bool) {
	cb.mu.Lock()
	defer cb.mu.Unlock()
	m, ok := cb.Tasks[taskID]
	if !ok {
		return nil, false
	}
	copy := *m
	return &copy, true
}
