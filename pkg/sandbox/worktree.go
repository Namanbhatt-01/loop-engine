package sandbox

import (
	"fmt"
	"io"
	"io/fs"
	"os"
	"os/exec"
	"path/filepath"
	"time"
)

// WorktreeManager creates and cleans up isolated Git worktrees
type WorktreeManager struct {
	BaseDir string
}

type WorktreeInfo struct {
	Path       string
	BranchName string
	IsWorktree bool
}

func NewWorktreeManager(baseDir string) *WorktreeManager {
	absBase, err := filepath.Abs(baseDir)
	if err == nil {
		baseDir = absBase
	}
	return &WorktreeManager{BaseDir: baseDir}
}

// CreateWorktree creates a temporary isolated git worktree or fallback directory copy for a task
func (m *WorktreeManager) CreateWorktree(taskID string, baseBranch string) (*WorktreeInfo, error) {
	if baseBranch == "" {
		baseBranch = "main"
	}

	wtDir := filepath.Join(os.TempDir(), "loop_worktrees", fmt.Sprintf("wt_%s_%d", taskID, time.Now().UnixNano()))
	branchName := fmt.Sprintf("loop-agent-%s", taskID)

	// Attempt Git worktree creation
	cmd := exec.Command("git", "worktree", "add", "-b", branchName, wtDir, baseBranch)
	cmd.Dir = m.BaseDir
	out, err := cmd.CombinedOutput()
	if err == nil {
		return &WorktreeInfo{
			Path:       wtDir,
			BranchName: branchName,
			IsWorktree: true,
		}, nil
	}

	// Fallback: If git worktree fails (e.g., untracked repo or no commits), copy project files
	if errMk := os.MkdirAll(wtDir, 0755); errMk != nil {
		return nil, fmt.Errorf("failed to create fallback directory (git out: %s): %w", string(out), errMk)
	}

	if errCopy := copyDirRecursive(m.BaseDir, wtDir); errCopy != nil {
		_ = os.RemoveAll(wtDir)
		return nil, fmt.Errorf("failed to clone directory to fallback workspace: %w", errCopy)
	}

	return &WorktreeInfo{
		Path:       wtDir,
		BranchName: branchName,
		IsWorktree: false,
	}, nil
}

// CleanupWorktree removes the isolated worktree or directory and cleans up git state
func (m *WorktreeManager) CleanupWorktree(info *WorktreeInfo) error {
	if info == nil || info.Path == "" {
		return nil
	}

	if info.IsWorktree {
		cmd := exec.Command("git", "worktree", "remove", "--force", info.Path)
		cmd.Dir = m.BaseDir
		_ = cmd.Run()

		pruneCmd := exec.Command("git", "worktree", "prune")
		pruneCmd.Dir = m.BaseDir
		_ = pruneCmd.Run()

		delBranchCmd := exec.Command("git", "branch", "-D", info.BranchName)
		delBranchCmd.Dir = m.BaseDir
		_ = delBranchCmd.Run()
	}

	return os.RemoveAll(info.Path)
}

// copyDirRecursive recursively copies project files while ignoring .git and bin
func copyDirRecursive(src, dst string) error {
	return filepath.WalkDir(src, func(path string, d fs.DirEntry, err error) error {
		if err != nil {
			return err
		}

		relPath, err := filepath.Rel(src, path)
		if err != nil {
			return err
		}

		// Skip .git and bin build artifacts
		if d.IsDir() && (d.Name() == ".git" || d.Name() == "bin" || d.Name() == "build") {
			return filepath.SkipDir
		}

		targetPath := filepath.Join(dst, relPath)
		if d.IsDir() {
			return os.MkdirAll(targetPath, 0755)
		}

		return copyFile(path, targetPath)
	})
}

func copyFile(src, dst string) error {
	in, err := os.Open(src)
	if err != nil {
		return err
	}
	defer in.Close()

	out, err := os.Create(dst)
	if err != nil {
		return err
	}
	defer out.Close()

	_, err = io.Copy(out, in)
	return err
}
