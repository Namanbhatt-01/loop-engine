# 🔁 Loop Engine Core

[![CI](https://github.com/Namanbhatt-01/loop-engine-core/actions/workflows/ci.yml/badge.svg)](https://github.com/Namanbhatt-01/loop-engine-core/actions/workflows/ci.yml)
[![Go Version](https://img.shields.io/badge/go-1.22%2B-blue.svg)](https://golang.org)
[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)

> **High-Performance Autonomous Loop Harness & Compiler-Driven TDD Control Plane**

**Loop Engine Core** is a hybrid polyglot framework combining a hardened **Go Control Plane & Sandbox Substrate** with a **Python Reasoning Engine**. It is designed to safely execute autonomous self-correction development loops across **any project codebase** (C++, Go, Python, Rust, TypeScript).

---

## 🏛️ Architecture Overview

```
               +-------------------------------------------------+
               |  USER / TRIGGER (Webhook, Issue, Slack, CLI)    |
               +-------------------------------------------------+
                                       |
                                       v
               +-------------------------------------------------+
               |   GO CONTROL PLANE & SANDBOX OPERATOR           |
               |   - Formal FSM Engine      - Process Group Kill |
               |   - Bounded Output Buffers - POSIX Resource Caps|
               |   - Universal Loopfile     - Ephemeral Worktree |
               +-------------------------------------------------+
                          |                         ^
        1. Run Task       |                         | 4. Return Status
        (HTTP / gRPC)     v                         | (Validated JSON)
               +-------------------------------------------------+
               |   PYTHON REASONING & PAIR-PROGRAMMING ENGINE    |
               |   - AST Static Guardrail   - Path Jail Limiter  |
               |   - Maker & Checker Agents - Local LLM / Ollama |
               |   - Transactional Patcher  - Context Compaction |
               +-------------------------------------------------+
                          |                         ^
        2. Execute Code   |                         | 3. Diagnostics
        (Isolated Group)  v                         | (STDOUT/STDERR)
               +-------------------------------------------------+
               |   HARDENED SANDBOX RUNTIME (ulimit & setpgid)   |
               +-------------------------------------------------+
```

---

## 🛡️ Key Features

1. **Polyglot Hybrid Architecture**:
   - **Go Control Plane**: Fast, deterministic process isolation, POSIX `ulimit` enforcement, process-group `SIGKILL` subtree termination, and Git worktree isolation.
   - **Python Reasoning Layer**: Pluggable into local **Ollama** (`qwen2.5-coder`, `dolphin-llama3`, etc.) or Cloud Frontier APIs (Gemini, Claude, OpenAI).

2. **4-Layer Defense & Safety Pipeline**:
   - **Layer 1 (AST Static Guard)**: Blocks `eval()`, `exec()`, `__subclasses__` sandbox escapes, and unvetted imports before execution.
   - **Layer 2 (Path & Diff Confinement)**: Canonical path jail (`os.path.commonpath`) defeating path traversal (`../../`), protecting sensitive files (`.env*`, `.git/**`).
   - **Layer 3 (Kernel Sandbox Substrate)**: Bounded buffers (2MB max) preventing host OOM attacks; process-group termination eliminating orphan/zombie leaks.
   - **Layer 4 (Circuit Breaker & Token Budget)**: Hard caps on self-correction iterations (default: 3 max) and dollar/token ceilings.

3. **Transactional Workspace Patching**:
   - Automatic pre-loop snapshotting.
   - Instant rollback if the loop fails to converge or hits circuit breaker ceilings.

4. **Universal Project Adapter (`Loopfile.yaml`)**:
   - Drop into any repository (C++, Go, Python, Rust, TypeScript).
   - Auto-detects project stack or loads explicit build/test commands.

---

## 🚀 Quickstart

### 1. Prerequisites
- **Go**: 1.22+
- **Python**: 3.9+
- *(Optional)* **Ollama**: running locally on `http://localhost:11434`

### 2. Installation
```bash
git clone https://github.com/Namanbhatt-01/loop-engine-core.git
cd loop-engine-core
```

### 3. Running the Autonomous Loop
```bash
./scripts/run_loop.sh
```

---

## ⚙️ Configuration (`Loopfile.yaml`)

Configure target project constraints:

```yaml
version: "1.0"
project:
  name: "loop-engine-core"
  language: "go" # auto | cpp | go | python | rust | typescript
  root: "."

limits:
  max_iterations: 3
  timeout_seconds: 30
  max_diff_lines: 250
  memory_limit_mb: 512
  cpu_cores: 2.0
  budget_limit_usd: 2.00

rules:
  protected_paths:
    - ".git/**"
    - ".env*"
    - "secrets/**"
  banned_imports:
    - "eval"
    - "exec"
    - "os.system"

verification:
  build_command: "go build ./..."
  test_command: "go test ./..."
  linter_command: "go vet ./..."
```

---

## 🧪 Running Test Suites

Execute both Go and Python test suites:

```bash
# Run Go unit tests
go test -v ./...

# Run Python guardrails and patcher tests
python3 -m unittest discover -s tests -v
```

---

## 📄 License
This project is licensed under the [MIT License](LICENSE).
