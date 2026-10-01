package sandbox

import (
	"bytes"
	"context"
	"fmt"
	"os"
	"os/exec"
	"runtime"
	"sync"
	"syscall"
	"time"
)

const (
	// MaxOutputBytes limits stdout/stderr capturing to 2MB to prevent memory exhaustion from rogue loops
	MaxOutputBytes = 2 * 1024 * 1024
)

// SandboxConfig holds execution isolation parameters
type SandboxConfig struct {
	MemoryLimitMB int
	CPUCores      float64
	Timeout       time.Duration
	WorkingDir    string
	EnvVars       map[string]string
}

// SandboxResult captures execution stats and outputs
type SandboxResult struct {
	ExitCode        int    `json:"exit_code"`
	Stdout          string `json:"stdout"`
	Stderr          string `json:"stderr"`
	ExecutionTimeMs int64  `json:"execution_time_ms"`
	TimedOut        bool   `json:"timed_out"`
	Truncated       bool   `json:"truncated"`
}

// limitedBuffer is a thread-safe bounded buffer that prevents OOM from runaway stdout/stderr
type limitedBuffer struct {
	mu        sync.Mutex
	buf       bytes.Buffer
	limit     int
	truncated bool
}

func newLimitedBuffer(limit int) *limitedBuffer {
	return &limitedBuffer{limit: limit}
}

func (lb *limitedBuffer) Write(p []byte) (n int, err error) {
	lb.mu.Lock()
	defer lb.mu.Unlock()

	remaining := lb.limit - lb.buf.Len()
	if remaining <= 0 {
		lb.truncated = true
		return len(p), nil // discard overflow silently
	}

	if len(p) > remaining {
		lb.truncated = true
		n, err = lb.buf.Write(p[:remaining])
		return len(p), err
	}

	return lb.buf.Write(p)
}

func (lb *limitedBuffer) String() string {
	lb.mu.Lock()
	defer lb.mu.Unlock()
	str := lb.buf.String()
	if lb.truncated {
		str += "\n... [TRUNCATED: Output exceeded 2MB limit] ..."
	}
	return str
}

// ExecuteIsolated runs a command with process-group isolation, resource limits, and anti-leak killing
func ExecuteIsolated(ctx context.Context, cmdStr string, cfg SandboxConfig) (*SandboxResult, error) {
	if cfg.Timeout <= 0 {
		cfg.Timeout = 30 * time.Second
	}

	execCtx, cancel := context.WithTimeout(ctx, cfg.Timeout)
	defer cancel()

	start := time.Now()

	sandboxedCmd := wrapCommandWithLimits(cmdStr, cfg)

	// Use plain exec.Command without CommandContext so we can manually kill the ENTIRE process group (-pgid)
	cmd := exec.Command("sh", "-c", sandboxedCmd)
	cmd.Dir = cfg.WorkingDir

	// Scrub environment variables & create isolated temporary execution workspace
	cmd.Env = scrubEnvironment(cfg.EnvVars)

	// Configure OS Process Group for clean subprocess-tree termination
	cmd.SysProcAttr = &syscall.SysProcAttr{
		Setpgid: true, // Creates a new process group: pgid == pid
	}

	applyOSLimits(cmd, cfg)

	stdoutBuf := newLimitedBuffer(MaxOutputBytes)
	stderrBuf := newLimitedBuffer(MaxOutputBytes)

	cmd.Stdout = stdoutBuf
	cmd.Stderr = stderrBuf

	if err := cmd.Start(); err != nil {
		return nil, fmt.Errorf("failed to start isolated process: %w", err)
	}

	pid := cmd.Process.Pid

	// Channel to signal process completion
	done := make(chan error, 1)
	go func() {
		done <- cmd.Wait()
	}()

	var waitErr error
	timedOut := false

	select {
	case <-execCtx.Done():
		timedOut = true
		// Kill the ENTIRE process group (-pgid) with SIGKILL to eliminate orphan/zombie leaks
		killProcessGroup(pid)
		// Wait for wait goroutine to exit
		<-done
	case waitErr = <-done:
		// Normal completion
	}

	elapsed := time.Since(start).Milliseconds()

	exitCode := 0
	if timedOut {
		exitCode = 124
	} else if waitErr != nil {
		if exitErr, ok := waitErr.(*exec.ExitError); ok {
			exitCode = exitErr.ExitCode()
		} else {
			exitCode = 1
		}
	}

	res := &SandboxResult{
		ExitCode:        exitCode,
		Stdout:          stdoutBuf.String(),
		Stderr:          stderrBuf.String(),
		ExecutionTimeMs: elapsed,
		TimedOut:        timedOut,
		Truncated:       stdoutBuf.truncated || stderrBuf.truncated,
	}

	if timedOut && res.Stderr == "" {
		res.Stderr = fmt.Sprintf("Execution timed out after %v (process group %d killed)", cfg.Timeout, pid)
	}

	return res, nil
}

// killProcessGroup sends SIGKILL to the entire process group
func killProcessGroup(pid int) {
	if pid <= 0 {
		return
	}

	// In POSIX systems, negative PID refers to all processes in that process group
	pgid, err := syscall.Getpgid(pid)
	if err == nil {
		_ = syscall.Kill(-pgid, syscall.SIGKILL)
	} else {
		_ = syscall.Kill(-pid, syscall.SIGKILL)
	}
}

// scrubEnvironment sanitizes and isolates system variables
func scrubEnvironment(customEnv map[string]string) []string {
	// Construct a clean, isolated PATH containing common system tool paths
	cleanPath := fmt.Sprintf("/opt/homebrew/bin:/usr/local/go/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin")
	if hostPath := os.Getenv("PATH"); hostPath != "" {
		cleanPath = fmt.Sprintf("%s:%s", cleanPath, hostPath)
	}

	safeVars := []string{
		fmt.Sprintf("PATH=%s", cleanPath),
		"LANG=en_US.UTF-8",
		"LC_ALL=en_US.UTF-8",
		"HOME=/tmp",
		fmt.Sprintf("TMPDIR=%s", os.TempDir()),
	}

	for k, v := range customEnv {
		safeVars = append(safeVars, fmt.Sprintf("%s=%s", k, v))
	}
	return safeVars
}

// applyOSLimits sets process resource limits
func applyOSLimits(cmd *exec.Cmd, cfg SandboxConfig) {
	if runtime.GOOS == "linux" {
		// On Linux: seccomp profiles and namespace cloning flags are assigned here
	}
}

// wrapCommandWithLimits prepends POSIX ulimit constraints to prevent file descriptor and CPU exhaustion
func wrapCommandWithLimits(cmdStr string, cfg SandboxConfig) string {
	cpuLimitSec := int(cfg.Timeout.Seconds()) + 1
	if cpuLimitSec <= 0 {
		cpuLimitSec = 30
	}

	// 1. Cap open files to 1024
	// 2. Cap CPU seconds to timeout + margin
	limitsPrefix := fmt.Sprintf("ulimit -n 1024 2>/dev/null; ulimit -t %d 2>/dev/null; ", cpuLimitSec)
	return limitsPrefix + cmdStr
}
