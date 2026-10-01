import re
from typing import Dict, Any
from python_engine.llm.client import LLMClient

class MakerAgent:
    """The Driver/Maker agent responsible for code generation, bug fixing, and refactoring."""

    SYSTEM_PROMPT = """You are an expert autonomous systems programmer. 
Your goal is to write clean, minimal, production-grade code that satisfies all requirements and unit tests.
Rules:
1. Output ONLY runnable code enclosed in triple backticks (e.g. ```python ... ```).
2. Do not write unnecessary commentary or explanations outside code blocks.
3. Fix all compiler errors and unit test failures indicated in the error feedback.
4. Do not import unvetted or dangerous packages (os, subprocess, socket).
"""

    def __init__(self, name: str = "Maker-Driver", llm_client: LLMClient = None):
        self.name = name
        self.llm = llm_client or LLMClient()

    def generate_solution(self, task_prompt: str, error_feedback: str = "", current_code: str = "") -> Dict[str, Any]:
        """Generates code patch proposal using LLM based on task prompt and real error feedback."""
        user_prompt = f"Goal:\n{task_prompt}\n"
        if current_code:
            user_prompt += f"\nCurrent Implementation:\n```\n{current_code}\n```\n"
        if error_feedback:
            user_prompt += f"\nTEST/COMPILER FAILURE FEEDBACK (You MUST fix this):\n{error_feedback}\n"

        raw_response = self.llm.generate(self.SYSTEM_PROMPT, user_prompt)
        extracted_code = self._extract_code(raw_response)

        return {
            "agent": self.name,
            "raw_response": raw_response,
            "proposed_code": extracted_code,
        }

    def _extract_code(self, response_text: str) -> str:
        """Extracts code block from LLM markdown response."""
        pattern = r"```(?:[a-zA-Z0-9_-]+)?\n(.*?)```"
        matches = re.findall(pattern, response_text, re.DOTALL)
        if matches:
            return matches[0].strip() + "\n"
        return response_text.strip() + "\n"
