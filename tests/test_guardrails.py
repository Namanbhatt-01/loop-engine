import unittest
import os
import sys

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from python_engine.guardrails.ast_guard import ASTGuard
from python_engine.guardrails.diff_limiter import DiffLimiter

class TestASTGuard(unittest.TestCase):
    def setUp(self):
        self.guard = ASTGuard()

    def test_benign_code(self):
        code = """
def add(a, b):
    return a + b

class Vector:
    def __init__(self, x, y):
        self.x = x
        self.y = y
"""
        ok, errors = self.guard.validate_code(code)
        self.assertTrue(ok)
        self.assertEqual(len(errors), 0)

    def test_banned_import_os(self):
        code = "import os\nprint('hello')"
        ok, errors = self.guard.validate_code(code)
        self.assertFalse(ok)
        self.assertTrue(any("forbidden import 'os'" in e for e in errors))

    def test_banned_from_import(self):
        code = "from subprocess import Popen\nPopen(['ls'])"
        ok, errors = self.guard.validate_code(code)
        self.assertFalse(ok)
        self.assertTrue(any("forbidden import from 'subprocess'" in e for e in errors))

    def test_banned_eval(self):
        code = "res = eval('2 + 2')"
        ok, errors = self.guard.validate_code(code)
        self.assertFalse(ok)
        self.assertTrue(any("forbidden call 'eval'" in e for e in errors))

    def test_sandbox_escape_subclasses(self):
        code = "x = ().__class__.__bases__[0].__subclasses__()"
        ok, errors = self.guard.validate_code(code)
        self.assertFalse(ok)
        self.assertTrue(any("forbidden attribute access '__subclasses__'" in e for e in errors))

class TestDiffLimiter(unittest.TestCase):
    def setUp(self):
        self.workspace = os.path.abspath(os.path.dirname(__file__))
        self.limiter = DiffLimiter(workspace_root=self.workspace, max_diff_lines=10)

    def test_path_traversal_blocked(self):
        # Attempting to escape workspace root
        ok, msg = self.limiter.check_file_path("../../.bashrc")
        self.assertFalse(ok)
        self.assertIn("Path Traversal Violation", msg)

    def test_protected_path_env(self):
        ok, msg = self.limiter.check_file_path(".env")
        self.assertFalse(ok)
        self.assertIn("Path Restriction Violation", msg)

    def test_protected_path_git(self):
        ok, msg = self.limiter.check_file_path(".git/config")
        self.assertFalse(ok)
        self.assertIn("Path Restriction Violation", msg)

    def test_valid_source_file(self):
        ok, msg = self.limiter.check_file_path("src/app.py")
        self.assertTrue(ok)

    def test_diff_size_exceeded(self):
        code = "\n".join([f"line_{i} = {i}" for i in range(20)])
        ok, msg = self.limiter.check_diff_size(code)
        self.assertFalse(ok)
        self.assertIn("Diff Limit Violation", msg)

if __name__ == "__main__":
    unittest.main()
