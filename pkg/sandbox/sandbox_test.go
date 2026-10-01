package sandbox

import (
	"context"
	"os/exec"
	"strings"
	"testing"
	"time"
)

func TestExecuteIsolated_StdoutStderrSeparation(t *testing.T) {
	cfg := SandboxConfig{
		Timeout:    5 * time.Second,
		WorkingDir: ".",
	}

	cmd := `echo "stdout message"; echo "stderr message" >&2`
	res, err := ExecuteIsolated(context.Background(), cmd, cfg)
	if err != nil {
		t.Fatalf("unexpected execution error: %v", err)
	}

	if res.ExitCode != 0 {
		t.Errorf("expected exit code 0, got %d", res.ExitCode)
	}

	if !strings.Contains(res.Stdout, "stdout message") {
		t.Errorf("expected stdout to contain 'stdout message', got: %q", res.Stdout)
	}

	if !strings.Contains(res.Stderr, "stderr message") {
		t.Errorf("expected stderr to contain 'stderr message', got: %q", res.Stderr)
	}

	if strings.Contains(res.Stdout, "stderr message") {
		t.Errorf("stdout was polluted with stderr: %q", res.Stdout)
	}
}

func TestExecuteIsolated_TimeoutKillsProcessGroup(t *testing.T) {
	cfg := SandboxConfig{
		Timeout:    500 * time.Millisecond,
		WorkingDir: ".",
	}

	// Spawn a background process in subshell that tries to detach and leak
	cmd := `sleep 20 & sleep 20`
	start := time.Now()
	res, err := ExecuteIsolated(context.Background(), cmd, cfg)
	elapsed := time.Since(start)

	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if !res.TimedOut {
		t.Errorf("expected res.TimedOut to be true, got false")
	}

	if elapsed > 2*time.Second {
		t.Errorf("timeout took too long to abort: %v", elapsed)
	}

	// Verify no orphaned sleep 20 processes exist
	out, _ := exec.Command("pgrep", "-f", "sleep 20").Output()
	if len(strings.TrimSpace(string(out))) > 0 {
		t.Errorf("Found orphaned sleep 20 processes running on host! PID: %s", string(out))
		// Clean up
		_ = exec.Command("pkill", "-9", "-f", "sleep 20").Run()
	}
}

func TestExecuteIsolated_OutputTruncation(t *testing.T) {
	cfg := SandboxConfig{
		Timeout:    5 * time.Second,
		WorkingDir: ".",
	}

	// Generate 3MB of stdout using python or perl/yes
	cmd := `python3 -c "print('A' * (3 * 1024 * 1024))"`
	res, err := ExecuteIsolated(context.Background(), cmd, cfg)
	if err != nil {
		t.Fatalf("execution failed: %v", err)
	}

	if !res.Truncated {
		t.Errorf("expected res.Truncated to be true for 3MB output, got false")
	}

	if !strings.Contains(res.Stdout, "[TRUNCATED: Output exceeded 2MB limit]") {
		t.Errorf("expected truncation warning in stdout")
	}
}
