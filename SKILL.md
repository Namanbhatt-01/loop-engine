---
name: loop-engineering
description: Rules, architectural patterns, and execution constraints for autonomous loop engineering, compiler-driven TDD verification, and sandboxed self-correction.
---

# 🔁 Loop Engineering Skill Guidelines

## 1. Core Operating Principles
- **Maker/Checker Separation**: Code generation is decoupled from grading. The Maker agent synthesizes code proposals, while the Checker agent acts as an independent validator.
- **Deterministic Verification**: Never rely on LLM self-grading. Always verify outputs using exit codes, compiler diagnostics, and AST static analysis.
- **Circuit Breakers as Physical Bounds**: Enforce a hard ceiling on self-correction retries (default: 3 iterations max) and real-time dollar/token limits.
- **Zero-Trust Process Sandboxing**: Run all generated tests inside isolated process groups (`Setpgid: true`) with strict POSIX resource limits (`ulimit -n 1024`, `ulimit -t`) and process tree kill (`syscall.Kill(-pgid, SIGKILL)`).

## 2. Universal Project Adaptation
Any target codebase can configure execution boundaries via `Loopfile.yaml`:
- **Limits**: Max iterations, timeout seconds, memory caps, max diff lines.
- **Rules**: Protected paths (`.git/**`, `.env*`, `secrets/**`), banned imports (`os.system`, `eval`, `exec`).
- **Verification**: `build_command`, `test_command`, `linter_command`.
