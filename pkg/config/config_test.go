package config

import (
	"testing"
)

func TestDefaultConfig(t *testing.T) {
	cfg := DefaultConfig()
	if cfg == nil {
		t.Fatalf("expected non-nil default config")
	}

	if cfg.Limits.MaxIterations != 3 {
		t.Errorf("expected MaxIterations to be 3, got %d", cfg.Limits.MaxIterations)
	}

	if cfg.Limits.MemoryLimitMB != 512 {
		t.Errorf("expected MemoryLimitMB to be 512, got %d", cfg.Limits.MemoryLimitMB)
	}
}
