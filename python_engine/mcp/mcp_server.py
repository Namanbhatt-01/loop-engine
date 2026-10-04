"""Model Context Protocol (MCP) Server for Loop Engine Core.

Exposes deterministic TDD verification, kernel sandbox controls, AST guardrail
validation, path-jailed workspace file access, resources, and prompt templates
as standard Model Context Protocol (MCP) primitives.
"""
from __future__ import annotations

import os
import sys
import json
import inspect
import urllib.request
import urllib.error
from typing import Dict, Any, Optional, Callable, List

# Add project root to sys.path so modules can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from python_engine.guardrails.ast_guard import ASTGuard
from python_engine.guardrails.diff_limiter import DiffLimiter

# ---------------------------------------------------------------------------
# Fallback Shim for FastMCP (Ensures zero-dependency stdio execution & AST scanner detection)
# ---------------------------------------------------------------------------
try:
    from mcp.server.fastmcp import FastMCP
    HAS_FAST_MCP = True
except ImportError:
    HAS_FAST_MCP = False

    class FastMCP:  # type: ignore
        """Comprehensive FastMCP fallback implementation supporting Tools, Resources, and Prompts."""

        def __init__(self, name: str = "loop-engine", **kwargs: Any):
            self.name = name
            self._tools: Dict[str, Dict[str, Any]] = {}
            self._resources: Dict[str, Dict[str, Any]] = {}
            self._prompts: Dict[str, Dict[str, Any]] = {}

        def tool(self, name: Optional[str] = None, description: Optional[str] = None):
            def decorator(fn: Callable[..., Any]):
                tool_name = name or fn.__name__
                doc = description or inspect.getdoc(fn) or ""
                sig = inspect.signature(fn)
                properties: Dict[str, Any] = {}
                required: List[str] = []

                for param_name, param in sig.parameters.items():
                    prop_type = "string"
                    if param.annotation == int:
                        prop_type = "integer"
                    elif param.annotation == float:
                        prop_type = "number"
                    elif param.annotation == bool:
                        prop_type = "boolean"

                    properties[param_name] = {"type": prop_type}
                    if param.default is inspect.Parameter.empty:
                        required.append(param_name)

                schema = {
                    "type": "object",
                    "properties": properties,
                }
                if required:
                    schema["required"] = required

                self._tools[tool_name] = {
                    "fn": fn,
                    "description": doc,
                    "inputSchema": schema,
                }
                return fn
            return decorator

        def resource(self, uri: str, name: Optional[str] = None, description: Optional[str] = None):
            def decorator(fn: Callable[..., Any]):
                res_name = name or fn.__name__
                self._resources[uri] = {
                    "fn": fn,
                    "name": res_name,
                    "description": description or inspect.getdoc(fn) or "",
                    "uri": uri,
                }
                return fn
            return decorator

        def prompt(self, name: Optional[str] = None, description: Optional[str] = None):
            def decorator(fn: Callable[..., Any]):
                prompt_name = name or fn.__name__
                self._prompts[prompt_name] = {
                    "fn": fn,
                    "description": description or inspect.getdoc(fn) or "",
                }
                return fn
            return decorator

        def run(self, transport: str = "stdio"):
            """Robust JSON-RPC 2.0 stdio server handling MCP protocol handshake and requests."""
            for line in sys.stdin:
                line_str = line.strip()
                if not line_str:
                    continue
                try:
                    req = json.loads(line_str)
                    req_id = req.get("id")
                    method = req.get("method")
                    params = req.get("params", {})

                    # Notifications (no response expected)
                    if method == "notifications/initialized":
                        continue

                    # MCP Initialize handshake
                    if method == "initialize":
                        res = {
                            "jsonrpc": "2.0",
                            "id": req_id,
                            "result": {
                                "protocolVersion": "2024-11-05",
                                "capabilities": {
                                    "tools": {"listChanged": False},
                                    "resources": {"subscribe": False, "listChanged": False},
                                    "prompts": {"listChanged": False},
                                },
                                "serverInfo": {
                                    "name": self.name,
                                    "version": "0.1.0",
                                },
                            },
                        }
                    elif method == "ping":
                        res = {"jsonrpc": "2.0", "id": req_id, "result": {}}
                    elif method == "tools/list":
                        tools_list = [
                            {
                                "name": k,
                                "description": v["description"],
                                "inputSchema": v["inputSchema"],
                            }
                            for k, v in self._tools.items()
                        ]
                        res = {"jsonrpc": "2.0", "id": req_id, "result": {"tools": tools_list}}
                    elif method == "tools/call":
                        tname = params.get("name")
                        args = params.get("arguments", {})
                        if tname in self._tools:
                            try:
                                out = self._tools[tname]["fn"](**args)
                                res = {
                                    "jsonrpc": "2.0",
                                    "id": req_id,
                                    "result": {
                                        "content": [{"type": "text", "text": str(out)}]
                                    },
                                }
                            except Exception as call_err:
                                res = {
                                    "jsonrpc": "2.0",
                                    "id": req_id,
                                    "result": {
                                        "isError": True,
                                        "content": [{"type": "text", "text": f"Error: {call_err}"}],
                                    },
                                }
                        else:
                            res = {
                                "jsonrpc": "2.0",
                                "id": req_id,
                                "error": {"code": -32601, "message": f"Tool '{tname}' not found"},
                            }
                    elif method == "resources/list":
                        res_list = [
                            {
                                "uri": uri,
                                "name": v["name"],
                                "description": v["description"],
                                "mimeType": "application/json",
                            }
                            for uri, v in self._resources.items()
                        ]
                        res = {"jsonrpc": "2.0", "id": req_id, "result": {"resources": res_list}}
                    elif method == "resources/read":
                        uri = params.get("uri")
                        if uri in self._resources:
                            content = self._resources[uri]["fn"]()
                            res = {
                                "jsonrpc": "2.0",
                                "id": req_id,
                                "result": {
                                    "contents": [
                                        {"uri": uri, "mimeType": "text/plain", "text": str(content)}
                                    ]
                                },
                            }
                        else:
                            res = {
                                "jsonrpc": "2.0",
                                "id": req_id,
                                "error": {"code": -32602, "message": f"Resource '{uri}' not found"},
                            }
                    elif method == "prompts/list":
                        prompts_list = [
                            {"name": k, "description": v["description"]}
                            for k, v in self._prompts.items()
                        ]
                        res = {"jsonrpc": "2.0", "id": req_id, "result": {"prompts": prompts_list}}
                    elif method == "prompts/get":
                        pname = params.get("name")
                        args = params.get("arguments", {})
                        if pname in self._prompts:
                            ptext = self._prompts[pname]["fn"](**args)
                            res = {
                                "jsonrpc": "2.0",
                                "id": req_id,
                                "result": {
                                    "messages": [
                                        {
                                            "role": "user",
                                            "content": {"type": "text", "text": str(ptext)},
                                        }
                                    ]
                                },
                            }
                        else:
                            res = {
                                "jsonrpc": "2.0",
                                "id": req_id,
                                "error": {"code": -32601, "message": f"Prompt '{pname}' not found"},
                            }
                    else:
                        res = {"jsonrpc": "2.0", "id": req_id, "result": {}}

                    sys.stdout.write(json.dumps(res) + "\n")
                    sys.stdout.flush()
                except Exception as e:
                    sys.stderr.write(f"MCP Server Error: {e}\n")
                    err = {"jsonrpc": "2.0", "id": None, "error": {"code": -32603, "message": str(e)}}
                    sys.stdout.write(json.dumps(err) + "\n")
                    sys.stdout.flush()


# Initialize official FastMCP server instance
mcp = FastMCP("loop-engine")

ast_guard = ASTGuard()


# ---------------------------------------------------------------------------
# MCP Tools
# ---------------------------------------------------------------------------
@mcp.tool()
def run_verification(task_id: str = "mcp-verify", project_root: str = ".", test_command: str = "") -> str:
    """Trigger sandboxed TDD test execution in Go Control Plane Sandbox."""
    daemon_port = os.getenv("LOOP_PORT", "50051")
    daemon_url = f"http://127.0.0.1:{daemon_port}/verify"

    req_data = json.dumps({
        "task_id": task_id,
        "project_root": os.path.abspath(project_root),
        "test_command": test_command,
    }).encode("utf-8")

    req = urllib.request.Request(daemon_url, data=req_data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=35.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return json.dumps(data, indent=2)
    except Exception as e:
        return json.dumps({
            "exit_code": 1,
            "stderr": f"Verification failed to reach Go daemon on port {daemon_port}: {e}",
            "stdout": "",
        })


@mcp.tool()
def read_workspace_file(relative_path: str, workspace_root: str = ".") -> str:
    """Read file contents safely from target workspace with path confinement and protected asset locking."""
    limiter = DiffLimiter(workspace_root=os.path.abspath(workspace_root))
    valid_path, reason = limiter.check_file_path(relative_path)
    if not valid_path:
        return f"Access Denied: {reason}"

    target_path = os.path.join(os.path.abspath(workspace_root), relative_path)
    if not os.path.exists(target_path):
        return f"File not found: {relative_path}"

    try:
        with open(target_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {e}"


@mcp.tool()
def check_circuit_breaker(task_id: str = "mcp-task", iteration: int = 1, added_tokens: int = 0, added_cost: float = 0.0) -> str:
    """Query Go Control Plane circuit breaker for iteration boundaries and dollar/token budget limits."""
    daemon_port = os.getenv("LOOP_PORT", "50051")
    daemon_url = f"http://127.0.0.1:{daemon_port}/circuit"

    req_data = json.dumps({
        "task_id": task_id,
        "iteration": iteration,
        "added_tokens": added_tokens,
        "added_cost": added_cost,
    }).encode("utf-8")

    req = urllib.request.Request(daemon_url, data=req_data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=5.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return json.dumps(data, indent=2)
    except Exception as e:
        return json.dumps({"allow_continuation": False, "reason": f"Circuit breaker daemon unreachable: {e}"})


@mcp.tool()
def verify_ast_guard(proposed_code: str) -> str:
    """Verify code safety using static AST analysis to defeat sandbox escapes, forbidden imports, and eval calls."""
    ok, errors = ast_guard.validate_code(proposed_code)
    if ok:
        return json.dumps({"status": "approved", "message": "AST validation passed: No sandbox escape or banned imports detected."})
    return json.dumps({"status": "rejected", "violations": errors})


# ---------------------------------------------------------------------------
# MCP Resources
# ---------------------------------------------------------------------------
@mcp.resource("loop://config")
def get_config_resource() -> str:
    """Read the active Loopfile configuration file."""
    loopfile_path = os.path.abspath("Loopfile.yaml")
    if os.path.exists(loopfile_path):
        with open(loopfile_path, "r", encoding="utf-8") as f:
            return f.read()
    return "version: '1.0'\n# Loopfile.yaml not found in working directory."


@mcp.resource("loop://health")
def get_health_resource() -> str:
    """Check connectivity and health of the Go Control Plane daemon."""
    daemon_port = os.getenv("LOOP_PORT", "50051")
    daemon_url = f"http://127.0.0.1:{daemon_port}/health"
    try:
        req = urllib.request.Request(daemon_url)
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            return resp.read().decode("utf-8")
    except Exception as e:
        return json.dumps({"status": "offline", "daemon_port": daemon_port, "error": str(e)})


# ---------------------------------------------------------------------------
# MCP Prompts
# ---------------------------------------------------------------------------
@mcp.prompt("autonomous_tdd_cycle")
def autonomous_tdd_prompt(task_description: str = "", target_file: str = "") -> str:
    """Generates prompt template for initiating an autonomous Maker/Checker TDD iteration."""
    return f"""You are operating inside the Loop Engine Core autonomous harness.
Target File: {target_file or 'src/solution.py'}
Task Objective: {task_description or 'Implement required functionality conforming to test suite.'}

Execution Protocol:
1. Synthesize minimal code patch addressing the requirements.
2. Evaluate AST security compliance (no banned modules, no __subclasses__ escapes).
3. Dispatch verification via `run_verification` tool.
4. If tests fail, parse compiler/runtime diagnostics and iterate.
"""


# ---------------------------------------------------------------------------
# Backward Compatibility Bridge
# ---------------------------------------------------------------------------
class MCPServerBridge:
    """Backward-compatible bridge exposing MCP tool definitions and execution."""

    def __init__(self, workspace_root: str = "."):
        self.workspace_root = workspace_root

    def list_tools(self) -> Dict[str, Any]:
        """Returns MCP tool definitions."""
        return {
            "tools": [
                {
                    "name": "run_verification",
                    "description": "Trigger TDD test execution in Go Control Plane Sandbox",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "task_id": {"type": "string"},
                            "project_root": {"type": "string"},
                            "test_command": {"type": "string"},
                        },
                    },
                },
                {
                    "name": "read_workspace_file",
                    "description": "Read file contents safely from target workspace with path confinement",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "relative_path": {"type": "string"},
                            "workspace_root": {"type": "string"},
                        },
                        "required": ["relative_path"],
                    },
                },
                {
                    "name": "check_circuit_breaker",
                    "description": "Query Go Control Plane circuit breaker for budget and iteration limits",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "task_id": {"type": "string"},
                            "iteration": {"type": "integer"},
                            "added_tokens": {"type": "integer"},
                            "added_cost": {"type": "number"},
                        },
                    },
                },
                {
                    "name": "verify_ast_guard",
                    "description": "Verify code safety using static AST analysis",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "proposed_code": {"type": "string"},
                        },
                        "required": ["proposed_code"],
                    },
                },
            ]
        }

    def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Executes an MCP tool call."""
        if tool_name == "read_workspace_file":
            rel_path = arguments.get("relative_path", "")
            root = arguments.get("workspace_root", self.workspace_root)
            content = read_workspace_file(rel_path, workspace_root=root)
            if content.startswith("Access Denied:") or content.startswith("File not found:"):
                return {"success": False, "error": content}
            return {"success": True, "content": content}
        elif tool_name == "run_verification":
            out = run_verification(
                task_id=arguments.get("task_id", "mcp-verify"),
                project_root=arguments.get("project_root", self.workspace_root),
                test_command=arguments.get("test_command", ""),
            )
            return {"success": True, "result": json.loads(out) if out.startswith("{") else out}
        elif tool_name == "check_circuit_breaker":
            out = check_circuit_breaker(
                task_id=arguments.get("task_id", "mcp-task"),
                iteration=arguments.get("iteration", 1),
                added_tokens=arguments.get("added_tokens", 0),
                added_cost=arguments.get("added_cost", 0.0),
            )
            return {"success": True, "result": json.loads(out) if out.startswith("{") else out}
        elif tool_name == "verify_ast_guard":
            out = verify_ast_guard(proposed_code=arguments.get("proposed_code", ""))
            return {"success": True, "result": json.loads(out) if out.startswith("{") else out}
        return {"success": False, "error": f"Unknown tool: {tool_name}"}


def main():
    """Main entrypoint for MCP stdio server."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
