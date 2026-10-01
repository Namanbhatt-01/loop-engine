# Contributing to Loop Engine Core

Thank you for your interest in contributing to **Loop Engine Core**! We welcome bug reports, feature proposals, architectural improvements, and pull requests.

---

## 🛠️ Development Setup

1. **Fork and Clone**:
   ```bash
   git clone https://github.com/Namanbhatt-01/loop-engine-core.git
   cd loop-engine-core
   ```

2. **Install Dependencies**:
   ```bash
   # Go dependencies
   go mod download

   # Python dependencies
   pip install -r requirements.txt
   ```

3. **Verify Existing Tests**:
   ```bash
   # Go tests
   go test -v ./...

   # Python tests
   python3 -m unittest discover -s tests -v
   ```

---

## 📜 Pull Request Process

1. **Create a Feature Branch**:
   ```bash
   git checkout -b feat/your-feature-name
   ```
2. **Code Standards**:
   - Run `gofmt -s -w .` on all Go files.
   - Run `go vet ./...` and ensure zero warnings.
   - Maintain type annotations and clean docstrings in Python modules.
   - Never disable security guardrails or delete tests without consensus.
3. **Commit Messages**:
   Follow [Conventional Commits](https://www.conventionalcommits.org/):
   - `feat: add support for WASM sandboxing`
   - `fix: resolve race condition in circuit breaker`
   - `docs: update quickstart instructions`
4. **Submit PR**: Open a pull request against `main`. All CI checks must be green.
