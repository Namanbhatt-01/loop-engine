package sandbox

import (
	"os"
	"path/filepath"
	"testing"
)

func TestWorktreeManager_CreateAndCleanup(t *testing.T) {
	// Create a temporary base directory simulating a repo
	tempBase, err := os.MkdirTemp("", "loop_base_repo_*")
	if err != nil {
		t.Fatalf("failed to create temp dir: %v", err)
	}
	defer os.RemoveAll(tempBase)

	// Write a test source file in base
	testFile := filepath.Join(tempBase, "main.go")
	if err := os.WriteFile(testFile, []byte("package main\n"), 0644); err != nil {
		t.Fatalf("failed to write test file: %v", err)
	}

	mgr := NewWorktreeManager(tempBase)
	info, err := mgr.CreateWorktree("test-task-1", "main")
	if err != nil {
		t.Fatalf("failed to create worktree: %v", err)
	}

	// Verify that the cloned/worktree workspace exists
	if _, err := os.Stat(info.Path); os.IsNotExist(err) {
		t.Fatalf("expected worktree path to exist: %s", info.Path)
	}

	// Verify the source file was copied/present
	clonedFile := filepath.Join(info.Path, "main.go")
	if _, err := os.Stat(clonedFile); os.IsNotExist(err) {
		t.Fatalf("expected main.go to exist in isolated workspace: %s", clonedFile)
	}

	// Test Cleanup
	if err := mgr.CleanupWorktree(info); err != nil {
		t.Fatalf("failed to cleanup worktree: %v", err)
	}

	if _, err := os.Stat(info.Path); !os.IsNotExist(err) {
		t.Fatalf("expected worktree path to be removed after cleanup: %s", info.Path)
	}
}
