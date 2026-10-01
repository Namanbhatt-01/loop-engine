package tdd

import (
	"context"
	"strings"
	"testing"

	"github.com/namanbhatt-01/loop-engine-core/pkg/config"
)

func TestTestRunner_SuccessfulVerification(t *testing.T) {
	cfg := config.DefaultConfig()
	cfg.Limits.TimeoutSeconds = 5
	cfg.Verify.BuildCommand = "echo 'build success'"
	cfg.Verify.TestCommand = "echo 'test success'"

	runner := NewTestRunner(cfg)
	res, err := runner.RunVerification(context.Background(), ".", "")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if res.ExitCode != 0 {
		t.Errorf("expected exit code 0, got %d", res.ExitCode)
	}

	if !strings.Contains(res.Stdout, "test success") {
		t.Errorf("expected stdout to contain 'test success'")
	}
}

func TestTestRunner_BuildFailureShortCircuits(t *testing.T) {
	cfg := config.DefaultConfig()
	cfg.Limits.TimeoutSeconds = 5
	// Failing build command
	cfg.Verify.BuildCommand = "sh -c 'echo \"syntax error in main.go\" >&2; exit 2'"
	cfg.Verify.TestCommand = "echo 'this should not run'"

	runner := NewTestRunner(cfg)
	res, err := runner.RunVerification(context.Background(), ".", "")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if res.ExitCode != 2 {
		t.Errorf("expected exit code 2 from failed build, got %d", res.ExitCode)
	}

	if strings.Contains(res.Stdout, "this should not run") {
		t.Errorf("test step ran even though build step failed!")
	}

	if !strings.Contains(res.Stderr, "Build Failure") {
		t.Errorf("expected stderr to indicate build failure, got: %q", res.Stderr)
	}
}
