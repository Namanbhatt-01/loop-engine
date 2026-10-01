from typing import Dict, Any, Tuple
from python_engine.guardrails.ast_guard import ASTGuard
from python_engine.guardrails.diff_limiter import DiffLimiter

class CheckerAgent:
    """The Navigator/Checker agent acting as scorekeeper, evaluating safety and verification results."""

    def __init__(self, name: str = "Checker-Judge"):
        self.name = name
        self.ast_guard = ASTGuard()
        self.diff_limiter = DiffLimiter()

    def evaluate_proposal(self, filepath: str, code_str: str) -> Tuple[bool, str]:
        """Evaluates a code proposal against static AST guardrails and path/diff limits."""
        # 1. Path Safety Check
        path_ok, path_msg = self.diff_limiter.check_file_path(filepath)
        if not path_ok:
            return False, f"[{self.name}] REJECTED: {path_msg}"

        # 2. Diff Size Check
        diff_ok, diff_msg = self.diff_limiter.check_diff_size(code_str)
        if not diff_ok:
            return False, f"[{self.name}] REJECTED: {diff_msg}"

        # 3. AST Static Inspection (for Python files)
        if filepath.endswith(".py"):
            ast_ok, ast_errors = self.ast_guard.validate_code(code_str)
            if not ast_ok:
                return False, f"[{self.name}] REJECTED: AST Static Validation Failed:\n" + "\n".join(ast_errors)

        return True, f"[{self.name}] APPROVED: Static verification passed cleanly."
