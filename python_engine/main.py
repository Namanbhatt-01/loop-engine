import os
import sys
import json
import urllib.request
import urllib.error
from typing import Dict, Any

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from python_engine.agents.maker import MakerAgent
from python_engine.agents.checker import CheckerAgent
from python_engine.patcher.patcher import WorkspacePatcher

class LoopReasoningEngine:
    def __init__(self, daemon_url: str = "http://127.0.0.1:50051", workspace_root: str = "."):
        self.daemon_url = daemon_url
        self.workspace_root = os.path.abspath(workspace_root)
        self.maker = MakerAgent()
        self.checker = CheckerAgent()
        self.patcher = WorkspacePatcher(workspace_root=self.workspace_root)

    def check_circuit_breaker(self, task_id: str, iteration: int, tokens: int, cost: float) -> Dict[str, Any]:
        """Calls Go Control Plane daemon to check iteration limits and budget ceilings."""
        req_data = json.dumps({
            "task_id": task_id,
            "iteration": iteration,
            "added_tokens": tokens,
            "added_cost": cost
        }).encode("utf-8")

        req = urllib.request.Request(f"{self.daemon_url}/circuit", data=req_data, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.URLError as e:
            return {"allow_continuation": False, "reason": f"Daemon connection failed: {e}"}

    def run_sandbox_verification(self, task_id: str, project_root: str, test_cmd: str = "") -> Dict[str, Any]:
        """Requests Go Control Plane sandbox runner to execute build & TDD tests."""
        req_data = json.dumps({
            "task_id": task_id,
            "project_root": project_root,
            "test_command": test_cmd
        }).encode("utf-8")

        req = urllib.request.Request(f"{self.daemon_url}/verify", data=req_data, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=35.0) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.URLError as e:
            return {"exit_code": 1, "stderr": f"Daemon connection failed: {e}", "stdout": ""}

    def execute_loop(self, task_id: str, task_prompt: str, target_file: str, test_command: str = "", max_iters: int = 3) -> bool:
        """Runs the complete Reason -> Act -> Observe -> Evaluate -> Repeat self-correction loop."""
        print(f"\n=======================================================")
        print(f"🚀 STARTING AUTONOMOUS LOOP [Task: {task_id}]")
        print(f"🎯 Target File: {target_file}")
        print(f"=======================================================\n")

        error_feedback = ""
        iteration = 1
        success = False

        target_abs = os.path.join(self.workspace_root, target_file)

        try:
            while iteration <= max_iters:
                print(f"🔄 --- ITERATION {iteration}/{max_iters} ---")

                # 1. Circuit Breaker Gate
                circuit_resp = self.check_circuit_breaker(task_id, iteration, tokens=1200, cost=0.004)
                if not circuit_resp.get("allow_continuation", True):
                    print(f"🛑 CIRCUIT BREAKER TRIGGERED: {circuit_resp.get('reason')}")
                    break

                # Read current code if file exists
                current_code = ""
                if os.path.exists(target_abs):
                    with open(target_abs, "r", encoding="utf-8") as f:
                        current_code = f.read()

                # 2. Maker Agent synthesizes proposed solution/refactoring
                proposal = self.maker.generate_solution(task_prompt, error_feedback, current_code)
                code = proposal["proposed_code"]
                print(f"✍️  [{self.maker.name}] Synthesized solution ({len(code.splitlines())} lines)")

                # 3. Checker Agent verifies AST and path rules
                approved, check_msg = self.checker.evaluate_proposal(target_file, code)
                print(f"🛡️  {check_msg}")
                if not approved:
                    error_feedback = check_msg
                    iteration += 1
                    continue

                # 4. Apply patch to workspace
                self.patcher.apply_patch(target_file, code)
                print(f"💾 Applied patch to '{target_file}'")

                # 5. Run Sandboxed TDD Verification via Go Control Plane
                print(f"⚡ Requesting Sandboxed TDD Verification from Go Control Plane...")
                verify_res = self.run_sandbox_verification(task_id, self.workspace_root, test_cmd=test_command)

                exit_code = verify_res.get("exit_code", verify_res.get("ExitCode", 1))
                stdout = verify_res.get("stdout", verify_res.get("Stdout", ""))
                stderr = verify_res.get("stderr", verify_res.get("Stderr", ""))

                if exit_code == 0:
                    print(f"\n✅ SUCCESS! All sandboxed verification tests passed (Exit Code 0).")
                    print(f"🎉 Code refactoring validated and committed!")
                    self.patcher.commit()
                    success = True
                    break
                else:
                    print(f"❌ TDD Verification Failed (Exit Code {exit_code}).")
                    combined_err = f"{stderr}\n{stdout}".strip()
                    print(f"🔍 [Diagnostics Details]:\n{combined_err}\n")
                    error_feedback = f"Subprocess Exit Code {exit_code}:\n{combined_err}"
                    print(f"📋 Diagnostics captured. Routing error feedback back to Maker for iteration {iteration + 1}...")
                    iteration += 1

            if not success:
                print(f"⚠️  Task did not converge within {max_iters} iterations. Rolling back workspace...")
                self.patcher.rollback_all()

        except Exception as e:
            print(f"💥 Unhandled exception during loop: {e}. Performing safe rollback...")
            self.patcher.rollback_all()
            raise e

        print(f"\n=======================================================")
        print(f"🏁 LOOP EXECUTION CONCLUDED [Status: {'PASSED' if success else 'FAILED'}]")
        print(f"=======================================================\n")
        return success

if __name__ == "__main__":
    engine = LoopReasoningEngine()
    engine.execute_loop(
        task_id="task-live-demo",
        task_prompt="Write top-level functions `add(a, b)` and `divide(a, b)` (NOT inside a class). In `divide(a, b)`, raise ValueError if b == 0.",
        target_file="src/calculator.py",
        test_command="python3 -m unittest tests/test_calculator.py",
        max_iters=3
    )
