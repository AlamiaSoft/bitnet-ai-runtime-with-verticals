from __future__ import annotations
from typing import List

class AgentGuardrails:
    """Enforces execution bounds, loop detection, and safety limits."""

    def __init__(self, max_iterations: int = 10, max_consecutive_errors: int = 3):
        self.max_iterations = max_iterations
        self.max_consecutive_errors = max_consecutive_errors

    def check_iteration_limit(self, current_iteration: int) -> bool:
        return current_iteration < self.max_iterations

    def detect_infinite_loop(self, action_history: List[str]) -> bool:
        """Detects repeated identical action invocations (including arguments)."""
        if len(action_history) >= 3:
            if action_history[-1] == action_history[-2] == action_history[-3]:
                return True
        if len(action_history) >= 4:
            # Alternating loop: A, B, A, B
            if action_history[-1] == action_history[-3] and action_history[-2] == action_history[-4]:
                return True
        return False
