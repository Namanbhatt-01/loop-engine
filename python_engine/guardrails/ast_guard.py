import ast
from typing import List, Tuple, Set

class ASTGuard:
    """Deterministic AST Code Inspection and Advanced Sandbox Escape Guardrail."""

    DEFAULT_BANNED_IMPORTS: Set[str] = {
        "os", "subprocess", "pty", "shutil", "socket", 
        "urllib", "requests", "http", "pickle", "marshal", "ctypes"
    }

    DEFAULT_BANNED_FUNCTIONS: Set[str] = {
        "eval", "exec", "compile", "__import__", "globals", "locals", 
        "vars", "getattr", "setattr", "delattr", "system", "popen", "spawn"
    }

    DEFAULT_BANNED_ATTRIBUTES: Set[str] = {
        "__subclasses__", "__bases__", "__class__", "__globals__", 
        "__code__", "__builtins__", "__reduce__"
    }

    def __init__(
        self, 
        banned_imports: List[str] = None, 
        banned_functions: List[str] = None,
        banned_attributes: List[str] = None
    ):
        self.banned_imports = set(banned_imports) if banned_imports else self.DEFAULT_BANNED_IMPORTS
        self.banned_functions = set(banned_functions) if banned_functions else self.DEFAULT_BANNED_FUNCTIONS
        self.banned_attributes = set(banned_attributes) if banned_attributes else self.DEFAULT_BANNED_ATTRIBUTES

    def validate_code(self, code_str: str) -> Tuple[bool, List[str]]:
        """Parses Python code into an AST and inspects all syntax nodes for forbidden constructs."""
        errors = []
        try:
            tree = ast.parse(code_str)
        except SyntaxError as se:
            return False, [f"AST SyntaxError at line {se.lineno}: {se.msg}"]

        for node in ast.walk(tree):
            # 1. Banned Function Calls
            if isinstance(node, ast.Call):
                func_name = self._resolve_call_name(node.func)
                for banned in self.banned_functions:
                    if func_name == banned or func_name.endswith(f".{banned}"):
                        errors.append(f"Security Violation: forbidden call '{func_name}' at line {node.lineno}")

            # 2. Banned Module Imports
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    root_mod = alias.name.split('.')[0]
                    if root_mod in self.banned_imports or alias.name in self.banned_imports:
                        errors.append(f"Security Violation: forbidden import '{alias.name}' at line {node.lineno}")

            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    root_mod = node.module.split('.')[0]
                    if root_mod in self.banned_imports or node.module in self.banned_imports:
                        errors.append(f"Security Violation: forbidden import from '{node.module}' at line {node.lineno}")

            # 3. Banned Attribute Access (e.g., __subclasses__, __globals__)
            elif isinstance(node, ast.Attribute):
                if node.attr in self.banned_attributes:
                    errors.append(f"Security Violation: forbidden attribute access '{node.attr}' at line {node.lineno}")

        is_valid = len(errors) == 0
        return is_valid, errors

    def _resolve_call_name(self, node: ast.AST) -> str:
        """Resolves full dotted name of a call target."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            val_name = self._resolve_call_name(node.value)
            return f"{val_name}.{node.attr}" if val_name else node.attr
        return ""
