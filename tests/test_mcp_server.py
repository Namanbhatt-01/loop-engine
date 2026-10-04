import unittest
import os
import sys
import json
import io

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from python_engine.mcp.mcp_server import (
    mcp,
    MCPServerBridge,
    read_workspace_file,
    verify_ast_guard,
    run_verification,
    check_circuit_breaker,
    get_config_resource,
    get_health_resource,
    autonomous_tdd_prompt,
)

class TestMCPServer(unittest.TestCase):
    def setUp(self):
        self.workspace = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        self.bridge = MCPServerBridge(workspace_root=self.workspace)

    def test_list_tools(self):
        tools_def = self.bridge.list_tools()
        self.assertIn("tools", tools_def)
        tool_names = [t["name"] for t in tools_def["tools"]]
        self.assertIn("run_verification", tool_names)
        self.assertIn("read_workspace_file", tool_names)
        self.assertIn("check_circuit_breaker", tool_names)
        self.assertIn("verify_ast_guard", tool_names)
        for tool in tools_def["tools"]:
            self.assertIn("annotations", tool)
            self.assertIn("readOnlyHint", tool["annotations"])

    def test_read_workspace_file_safe(self):
        res = self.bridge.execute_tool("read_workspace_file", {"relative_path": "Loopfile.yaml"})
        self.assertTrue(res.get("success"))
        self.assertIn("version:", res.get("content", ""))

    def test_read_workspace_file_path_traversal_blocked(self):
        res = self.bridge.execute_tool("read_workspace_file", {"relative_path": "../../etc/passwd"})
        self.assertFalse(res.get("success"))
        self.assertIn("Access Denied", res.get("error", ""))

    def test_verify_ast_guard_tool_benign(self):
        code = "def multiply(a, b):\n    return a * b\n"
        res = self.bridge.execute_tool("verify_ast_guard", {"proposed_code": code})
        self.assertTrue(res.get("success"))
        data = res.get("result", {})
        self.assertEqual(data.get("status"), "approved")

    def test_verify_ast_guard_tool_malicious(self):
        code = "import os\nos.system('rm -rf /')"
        res = self.bridge.execute_tool("verify_ast_guard", {"proposed_code": code})
        self.assertTrue(res.get("success"))
        data = res.get("result", {})
        self.assertEqual(data.get("status"), "rejected")
        self.assertTrue(len(data.get("violations", [])) > 0)

    def test_unknown_tool(self):
        res = self.bridge.execute_tool("non_existent_tool", {})
        self.assertFalse(res.get("success"))
        self.assertIn("Unknown tool", res.get("error", ""))

    def test_resources(self):
        config_text = get_config_resource()
        self.assertTrue("version" in config_text or "Loopfile.yaml" in config_text)
        health_status = get_health_resource()
        self.assertTrue(isinstance(health_status, str))

    def test_prompts(self):
        prompt_text = autonomous_tdd_prompt("Fix math bug", "src/math.py")
        self.assertIn("Fix math bug", prompt_text)
        self.assertIn("src/math.py", prompt_text)

    def test_stdio_jsonrpc_handshake(self):
        # Simulate standard MCP initialize and tools/list requests over stdio
        init_req = json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"protocolVersion": "2024-11-05", "capabilities": {}}
        })
        tools_req = json.dumps({
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {}
        })

        input_stream = io.StringIO(f"{init_req}\n{tools_req}\n")
        output_stream = io.StringIO()

        orig_stdin, orig_stdout = sys.stdin, sys.stdout
        try:
            sys.stdin = input_stream
            sys.stdout = output_stream
            mcp.run(transport="stdio")
        finally:
            sys.stdin, sys.stdout = orig_stdin, orig_stdout

        output_lines = [json.loads(line) for line in output_stream.getvalue().splitlines() if line.strip()]
        self.assertEqual(len(output_lines), 2)
        
        # Verify initialize response
        init_resp = output_lines[0]
        self.assertEqual(init_resp["id"], 1)
        self.assertEqual(init_resp["result"]["serverInfo"]["name"], "loop-engine")
        self.assertIn("tools", init_resp["result"]["capabilities"])

        # Verify tools/list response
        tools_resp = output_lines[1]
        self.assertEqual(tools_resp["id"], 2)
        tool_names = [t["name"] for t in tools_resp["result"]["tools"]]
        self.assertIn("run_verification", tool_names)
        self.assertIn("read_workspace_file", tool_names)

if __name__ == "__main__":
    unittest.main()
