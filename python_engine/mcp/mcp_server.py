import os
import json
from typing import Dict, Any

class MCPServerBridge:
    """Model Context Protocol (MCP) server bridge exposing tools to LLMs."""

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
                            "test_command": {"type": "string"}
                        }
                    }
                },
                {
                    "name": "read_workspace_file",
                    "description": "Read file contents safely from target workspace",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "relative_path": {"type": "string"}
                        },
                        "required": ["relative_path"]
                    }
                }
            ]
        }

    def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Executes an MCP tool call."""
        if tool_name == "read_workspace_file":
            path = os.path.join(self.workspace_root, arguments["relative_path"])
            if os.path.exists(path):
                with open(path, "r") as f:
                    return {"success": True, "content": f.read()}
            return {"success": False, "error": "File not found"}
        return {"success": False, "error": f"Unknown tool: {tool_name}"}
