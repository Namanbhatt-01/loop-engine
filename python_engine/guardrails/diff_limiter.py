import os
import fnmatch
from typing import List, Tuple

class DiffLimiter:
    """Enforces protected file paths, workspace jail confinement, and maximum diff line limits."""

    def __init__(self, workspace_root: str = None, protected_paths: List[str] = None, max_diff_lines: int = 250):
        self.workspace_root = os.path.abspath(workspace_root or os.getcwd())
        self.protected_paths = protected_paths or [".git/**", ".git*", ".env*", "secrets/**", "*.pem", "*.key"]
        self.max_diff_lines = max_diff_lines

    def check_file_path(self, filepath: str) -> Tuple[bool, str]:
        """Validates that filepath is safely jailed within workspace and does not touch protected resources."""
        # 1. Resolve absolute canonical path to defeat traversal attacks (e.g. ../../.env)
        target_abs = os.path.abspath(os.path.join(self.workspace_root, filepath))

        # 2. Workspace Jail Confinement Check
        try:
            common = os.path.commonpath([target_abs, self.workspace_root])
            if common != self.workspace_root:
                return False, f"Path Traversal Violation: target path '{filepath}' escapes workspace root '{self.workspace_root}'"
        except ValueError:
            return False, f"Path Traversal Violation: target path '{filepath}' is on an invalid drive/path"

        # 3. Check relative path against protected patterns
        rel_path = os.path.relpath(target_abs, self.workspace_root)
        rel_parts = rel_path.split(os.sep)

        for pattern in self.protected_paths:
            # Match against full relative path, filename, and directory components
            if (fnmatch.fnmatch(rel_path, pattern) or 
                fnmatch.fnmatch(os.path.basename(target_abs), pattern) or
                any(fnmatch.fnmatch(part, pattern.rstrip("/*")) for part in rel_parts)):
                return False, f"Path Restriction Violation: target path '{filepath}' matches protected pattern '{pattern}'"

        return True, "Path allowed"

    def check_diff_size(self, code_str: str) -> Tuple[bool, str]:
        """Ensures diff size does not exceed maximum allowable lines per iteration."""
        line_count = len(code_str.splitlines())
        if line_count > self.max_diff_lines:
            return False, f"Diff Limit Violation: diff contains {line_count} lines, exceeding max cap of {self.max_diff_lines} lines"
        return True, "Diff size within limits"
