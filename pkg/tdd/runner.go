package tdd

import (
	"context"
	"fmt"
	"time"

	"github.com/namanbhatt-01/loop-engine-core/pkg/config"
	"github.com/namanbhatt-01/loop-engine-core/pkg/sandbox"
)

// TestRunner manages deterministic TDD verification loops
type TestRunner struct {
	Config *config.LoopConfig
}

func NewTestRunner(cfg *config.LoopConfig) *TestRunner {
	return &TestRunner{Config: cfg}
}

// RunVerification executes the build and test sequence in the sandbox
func (r *TestRunner) RunVerification(ctx context.Context, projectRoot string, customTestCmd string) (*sandbox.SandboxResult, error) {
	sbCfg := sandbox.SandboxConfig{
		MemoryLimitMB: r.Config.Limits.MemoryLimitMB,
		CPUCores:      r.Config.Limits.CPUCores,
		Timeout:       time.Duration(r.Config.Limits.TimeoutSeconds) * time.Second,
		WorkingDir:    projectRoot,
		EnvVars:       map[string]string{},
	}

	// 1. Run Build step if specified
	if r.Config.Verify.BuildCommand != "" {
		buildRes, err := sandbox.ExecuteIsolated(ctx, r.Config.Verify.BuildCommand, sbCfg)
		if err != nil {
			return nil, fmt.Errorf("build execution failed: %w", err)
		}
		if buildRes.ExitCode != 0 {
			buildRes.Stderr = fmt.Sprintf("Build Failure (exit code %d):\n%s\n%s", buildRes.ExitCode, buildRes.Stdout, buildRes.Stderr)
			return buildRes, nil
		}
	}

	// 2. Run Test step
	testCmd := r.Config.Verify.TestCommand
	if customTestCmd != "" {
		testCmd = customTestCmd
	}

	if testCmd == "" {
		testCmd = "go test ./... || pytest"
	}

	testRes, err := sandbox.ExecuteIsolated(ctx, testCmd, sbCfg)
	if err != nil {
		return nil, fmt.Errorf("test execution failed: %w", err)
	}

	return testRes, nil
}
