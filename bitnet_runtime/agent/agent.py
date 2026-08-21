from __future__ import annotations
import asyncio
import json
import re
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator, Callable, Dict, List, Optional
from ..inference.base import InferenceEngine
from ..logging import logger
from ..memory.episodic_memory import EpisodicMemory
from ..memory.semantic_memory import SemanticMemory
from ..tools.base import ToolResult
from ..tools.registry import ToolRegistry
from .guardrails import AgentGuardrails
from .prompt_templates import REACT_SYSTEM_PROMPT

@dataclass
class AgentStepResult:
    step_number: int
    thought: Optional[str] = None
    action: Optional[str] = None
    action_input: Optional[Dict[str, Any]] = None
    observation: Optional[str] = None
    is_final: bool = False
    final_answer: Optional[str] = None

@dataclass
class AgentRunResult:
    session_id: str
    success: bool
    final_answer: str
    steps: List[AgentStepResult] = field(default_factory=list)
    total_iterations: int = 0
    error: Optional[str] = None

class Agent:
    """
    ReAct autonomous agent orchestrator executing step-by-step reasoning
    and tool execution locally with BitNet/edge LLMs.
    """

    def __init__(
        self,
        name: str,
        inference_engine: InferenceEngine,
        tool_registry: ToolRegistry,
        episodic_memory: Optional[EpisodicMemory] = None,
        semantic_memory: Optional[SemanticMemory] = None,
        guardrails: Optional[AgentGuardrails] = None,
        system_prompt: Optional[str] = None,
        timeout_seconds: float = 60.0,
    ):
        self.name = name
        self.inference_engine = inference_engine
        self.tool_registry = tool_registry
        self.episodic_memory = episodic_memory
        self.semantic_memory = semantic_memory
        self.guardrails = guardrails or AgentGuardrails()
        self.custom_system_prompt = system_prompt
        self.timeout_seconds = timeout_seconds

    def _build_system_prompt(self) -> str:
        tools_desc = self.tool_registry.get_tools_description()
        if self.custom_system_prompt:
            return f"{self.custom_system_prompt}\n\nAvailable Tools:\n{tools_desc}"
        return REACT_SYSTEM_PROMPT.format(tools_description=tools_desc)

    def _parse_react_output(self, text: str) -> tuple[Optional[str], Optional[str], Optional[Dict[str, Any]], Optional[str]]:
        """Extract Thought, Action, Action Input, and Final Answer."""
        # Check for Final Answer
        final_match = re.search(r"Final Answer:\s*(.*)", text, re.DOTALL | re.IGNORECASE)
        if final_match:
            thought_match = re.search(r"Thought:\s*(.*?)(?=Final Answer:|$)", text, re.DOTALL | re.IGNORECASE)
            thought = thought_match.group(1).strip() if thought_match else None
            return thought, None, None, final_match.group(1).strip()

        thought_match = re.search(r"Thought:\s*(.*?)(?=Action:|$)", text, re.DOTALL | re.IGNORECASE)
        thought = thought_match.group(1).strip() if thought_match else text.strip()

        action_match = re.search(r"Action:\s*([a-zA-Z0-9_\-]+)", text, re.IGNORECASE)
        action = action_match.group(1).strip() if action_match else None

        action_input = {}
        input_match = re.search(r"Action Input:\s*(.*?)(?=Observation:|$)", text, re.DOTALL | re.IGNORECASE)
        if input_match:
            raw_val = input_match.group(1).strip()
            # Strip markdown code fences if present
            raw_val = re.sub(r"^```(?:json)?\s*", "", raw_val)
            raw_val = re.sub(r"\s*```$", "", raw_val)
            
            # Find json block { ... }
            brace_match = re.search(r"(\{.*\})", raw_val, re.DOTALL)
            if brace_match:
                try:
                    action_input = json.loads(brace_match.group(1).strip())
                except Exception:
                    action_input = {"raw": raw_val}
            else:
                action_input = {"raw": raw_val} if raw_val else {}

        return thought, action, action_input, None

    async def run(
        self,
        prompt: str,
        session_id: Optional[str] = None,
        event_callback: Optional[Callable[[Dict[str, Any]], Any]] = None,
    ) -> AgentRunResult:
        if not session_id and self.episodic_memory:
            session_id = self.episodic_memory.create_session(title=f"Task: {prompt[:30]}")
        session_id = session_id or "ephemeral_session"

        if self.episodic_memory:
            self.episodic_memory.log_event(session_id, 0, "user_prompt", prompt)

        system_prompt = self._build_system_prompt()
        conversation_history = f"User Request: {prompt}\n"
        steps: List[AgentStepResult] = []
        action_history: List[str] = []

        iteration = 0
        while self.guardrails.check_iteration_limit(iteration):
            iteration += 1

            if event_callback:
                await event_callback({"type": "iteration_start", "iteration": iteration})

            # Retrieve semantic context if query is relevant with strict isolation boundaries
            context_snippet = ""
            if self.semantic_memory and iteration == 1:
                mem_results = await self.semantic_memory.query(prompt, top_k=2)
                if mem_results:
                    context_snippet = "\n<retrieved_local_context>\n" + "\n".join(
                        [f"- [{r.metadata.get('title', 'doc')}] {r.text_content}" for r in mem_results]
                    ) + "\n</retrieved_local_context>\n"

            llm_prompt = f"{conversation_history}{context_snippet}\nThought:"
            try:
                resp = await asyncio.wait_for(
                    self.inference_engine.complete(
                        prompt=llm_prompt,
                        system_prompt=system_prompt,
                        temperature=0.2,
                        stop_sequences=["Observation:"],
                    ),
                    timeout=self.timeout_seconds,
                )
            except asyncio.TimeoutError:
                final_ans = f"Execution timed out after {self.timeout_seconds}s waiting for model inference."
                return AgentRunResult(session_id=session_id, success=False, final_answer=final_ans, steps=steps, total_iterations=iteration, error=final_ans)

            thought, action, action_input, final_answer = self._parse_react_output(resp.text)

            if final_answer:
                step_res = AgentStepResult(
                    step_number=iteration,
                    thought=thought,
                    is_final=True,
                    final_answer=final_answer,
                )
                steps.append(step_res)
                if self.episodic_memory:
                    self.episodic_memory.log_event(session_id, iteration, "final_answer", final_answer)
                if event_callback:
                    await event_callback({"type": "final_answer", "answer": final_answer})

                return AgentRunResult(
                    session_id=session_id,
                    success=True,
                    final_answer=final_answer,
                    steps=steps,
                    total_iterations=iteration,
                )

            if action:
                # Include serialized args in history for precise loop detection
                action_signature = f"{action}:{json.dumps(action_input or {}, sort_keys=True)}"
                action_history.append(action_signature)
                if self.guardrails.detect_infinite_loop(action_history):
                    final_ans = "Execution halted: Infinite tool loop detected."
                    return AgentRunResult(session_id=session_id, success=False, final_answer=final_ans, steps=steps, total_iterations=iteration, error=final_ans)

                if event_callback:
                    await event_callback({"type": "tool_call", "action": action, "input": action_input})

                tool_result: ToolResult = await self.tool_registry.execute_tool(action, **(action_input or {}))
                obs_text = tool_result.to_string()

                step_res = AgentStepResult(
                    step_number=iteration,
                    thought=thought,
                    action=action,
                    action_input=action_input,
                    observation=obs_text,
                )
                steps.append(step_res)

                if self.episodic_memory:
                    self.episodic_memory.log_event(session_id, iteration, "thought", thought or "")
                    self.episodic_memory.log_event(session_id, iteration, "tool_call", f"{action}({action_input})")
                    self.episodic_memory.log_event(session_id, iteration, "tool_output", obs_text)

                conversation_history += f"\nThought: {thought}\nAction: {action}\nAction Input: {json.dumps(action_input)}\nObservation: {obs_text}\n"
            else:
                # No action and no explicit final answer
                final_ans = resp.text.replace("Thought:", "").strip()
                step_res = AgentStepResult(step_number=iteration, thought=thought, is_final=True, final_answer=final_ans)
                steps.append(step_res)
                return AgentRunResult(session_id=session_id, success=True, final_answer=final_ans, steps=steps, total_iterations=iteration)

        # Iteration limit reached
        final_ans = "Execution halted: Maximum iteration budget reached."
        return AgentRunResult(session_id=session_id, success=False, final_answer=final_ans, steps=steps, total_iterations=iteration, error=final_ans)
