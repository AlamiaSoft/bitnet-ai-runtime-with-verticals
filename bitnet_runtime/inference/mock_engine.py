from __future__ import annotations
import asyncio
import re
from typing import Any, AsyncGenerator, Callable, Dict, List, Optional
from .base import CompletionResponse, InferenceEngine, TokenUsage

class MockInferenceEngine(InferenceEngine):
    """
    Deterministic mock inference engine for testing, verification, ReAct loop
    simulation, and offline benchmarking without downloading model weights.
    """

    def __init__(self, default_response: Optional[str] = None):
        self.default_response = default_response
        self.pattern_responses: List[tuple[re.Pattern, str | Callable[[str], str]]] = []
        self._history: List[str] = []

    def register_pattern(self, pattern: str, response: str | Callable[[str], str]) -> None:
        self.pattern_responses.append((re.compile(pattern, re.IGNORECASE), response))

    async def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 1024,
        stop_sequences: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> CompletionResponse:
        self._history.append(prompt)
        full_text = f"{system_prompt}\n{prompt}" if system_prompt else prompt

        # Check registered pattern responses
        for pattern, handler in self.pattern_responses:
            if pattern.search(full_text):
                if callable(handler):
                    resp_text = handler(full_text)
                else:
                    resp_text = handler
                return CompletionResponse(
                    text=resp_text,
                    model="mock-engine-v1",
                    usage=TokenUsage(
                        prompt_tokens=len(full_text.split()),
                        completion_tokens=len(resp_text.split()),
                        total_tokens=len(full_text.split()) + len(resp_text.split()),
                    ),
                )

        if self.default_response:
            resp_text = self.default_response
        elif "summarize" in full_text.lower():
            resp_text = "Summary: The document discusses key operational objectives and milestone deliverables."
        elif "classify" in full_text.lower():
            resp_text = '{"category": "lead_inquiry", "priority": "high", "sentiment": "positive"}'
        elif "action:" in full_text.lower() or "react" in full_text.lower() or "thought:" in full_text.lower():
            resp_text = "Thought: I have analyzed the user request and completed the required steps.\nFinal Answer: Operation completed successfully."
        else:
            resp_text = "Processed input successfully using BitNet Mock Engine."

        return CompletionResponse(
            text=resp_text,
            model="mock-engine-v1",
            usage=TokenUsage(
                prompt_tokens=len(full_prompt_words := full_text.split()),
                completion_tokens=len(resp_words := resp_text.split()),
                total_tokens=len(full_prompt_words) + len(resp_words),
            ),
        )

    async def stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 1024,
        stop_sequences: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> AsyncGenerator[str, None]:
        res = await self.complete(prompt, system_prompt, temperature, max_tokens, stop_sequences, **kwargs)
        for word in res.text.split(" "):
            yield word + " "
            await asyncio.sleep(0.005)
