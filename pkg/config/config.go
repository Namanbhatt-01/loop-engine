package config

import (
	"fmt"
	"os"
	"path/filepath"

	"gopkg.in/yaml.v3"
)

// LoopConfig represents the universal project adapter configuration (Loopfile.yaml)
type LoopConfig struct {
	Version string        `yaml:"version"`
	Project ProjectConfig `yaml:"project"`
	Limits  LimitsConfig  `yaml:"limits"`
	Rules   RulesConfig   `yaml:"rules"`
	Verify  VerifyConfig  `yaml:"verification"`
}

type ProjectConfig struct {
	Name     string `yaml:"name"`
	Language string `yaml:"language"` // cpp, go, python, rust, typescript, auto
	Root     string `yaml:"root"`
}

type LimitsConfig struct {
	MaxIterations  int     `yaml:"max_iterations"`
	TimeoutSeconds int     `yaml:"timeout_seconds"`
	MaxDiffLines   int     `yaml:"max_diff_lines"`
	MemoryLimitMB  int     `yaml:"memory_limit_mb"`
	CPUCores       float64 `yaml:"cpu_cores"`
	BudgetLimitUSD float64 `yaml:"budget_limit_usd"`
}

type RulesConfig struct {
	ProtectedPaths []string `yaml:"protected_paths"`
	BannedImports  []string `yaml:"banned_imports"`
}

type VerifyConfig struct {
	BuildCommand  string `yaml:"build_command"`
	TestCommand   string `yaml:"test_command"`
	LinterCommand string `yaml:"linter_command"`
}

// DefaultConfig returns safe fallback defaults for any project
func DefaultConfig() *LoopConfig {
	return &LoopConfig{
		Version: "1.0",
		Project: ProjectConfig{
			Name:     "generic-project",
			Language: "auto",
			Root:     ".",
		},
		Limits: LimitsConfig{
			MaxIterations:  3,
			TimeoutSeconds: 30,
			MaxDiffLines:   250,
			MemoryLimitMB:  512,
			CPUCores:       2.0,
			BudgetLimitUSD: 2.00,
		},
		Rules: RulesConfig{
			ProtectedPaths: []string{".git/**", ".env*", "secrets/**", "*.pem"},
			BannedImports:  []string{"eval", "exec", "os.system", "subprocess.Popen"},
		},
		Verify: VerifyConfig{
			BuildCommand:  "",
			TestCommand:   "go test ./... || pytest || npm test",
			LinterCommand: "",
		},
	}
}

// LoadConfig attempts to parse Loopfile.yaml, fallbacking to smart auto-detection
func LoadConfig(dir string) (*LoopConfig, error) {
	cfgPath := filepath.Join(dir, "Loopfile.yaml")
	if _, err := os.Stat(cfgPath); os.IsNotExist(err) {
		cfgPath = filepath.Join(dir, ".looprules")
	}

	cfg := DefaultConfig()
	data, err := os.ReadFile(cfgPath)
	if err == nil {
		if err := yaml.Unmarshal(data, cfg); err != nil {
			return nil, fmt.Errorf("failed to parse config YAML: %w", err)
		}
	} else {
		// Auto-detect project stack
		cfg.AutoDetectStack(dir)
	}

	return cfg, nil
}

// AutoDetectStack detects build & test commands based on workspace markers
func (c *LoopConfig) AutoDetectStack(dir string) {
	if _, err := os.Stat(filepath.Join(dir, "CMakeLists.txt")); err == nil {
		c.Project.Language = "cpp"
		c.Verify.BuildCommand = "cmake -B build && cmake --build build"
		c.Verify.TestCommand = "ctest --test-dir build --output-on-failure"
	} else if _, err := os.Stat(filepath.Join(dir, "go.mod")); err == nil {
		c.Project.Language = "go"
		c.Verify.BuildCommand = "go build ./..."
		c.Verify.TestCommand = "go test ./..."
	} else if _, err := os.Stat(filepath.Join(dir, "Cargo.toml")); err == nil {
		c.Project.Language = "rust"
		c.Verify.BuildCommand = "cargo check"
		c.Verify.TestCommand = "cargo test"
	} else if _, err := os.Stat(filepath.Join(dir, "package.json")); err == nil {
		c.Project.Language = "typescript"
		c.Verify.BuildCommand = "npm run build"
		c.Verify.TestCommand = "npm test"
	} else if _, err := os.Stat(filepath.Join(dir, "pyproject.toml")); err == nil || hasPyFiles(dir) {
		c.Project.Language = "python"
		c.Verify.TestCommand = "pytest"
	}
}

func hasPyFiles(dir string) bool {
	matches, _ := filepath.Glob(filepath.Join(dir, "*.py"))
	return len(matches) > 0
}
