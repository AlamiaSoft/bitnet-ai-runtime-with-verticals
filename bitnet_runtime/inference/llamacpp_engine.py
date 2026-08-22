from __future__ import annotations
import asyncio
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Optional
from ..logging import logger
from .base import CompletionResponse, InferenceEngine, TokenUsage

class LlamaCppEngine(InferenceEngine):
    """
    Fallback CPU inference engine for quantized GGUF models using llama-cpp-python.
    """

    def __init__(self, model_path: Optional[str] = None, threads: int = 4, context_window: int = 4096):
        self.model_path = model_path
        self.threads = threads
        self.context_window = context_window
        self._llm = None
        self._load_model()

    def _load_model(self) -> None:
        if not self.model_path or not Path(self.model_path).exists():
            return
        try:
            from llama_cpp import Llama
            self._llm = Llama(
                model_path=str(self.model_path),
                n_threads=self.threads,
                n_ctx=self.context_window,
                verbose=False,
            )
            logger.info(f"Loaded LlamaCpp model from {self.model_path}")
        except ImportError:
            logger.debug("llama-cpp-python is not installed.")
        except Exception as e:
            logger.warning(f"Failed to load LlamaCpp model: {e}")

    async def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 1024,
        stop_sequences: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> CompletionResponse:
        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt

        if self._llm is not None:
            loop = asyncio.get_running_loop()
            output = await loop.run_in_executor(
                None,
                lambda: self._llm(
                    full_prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    stop=stop_sequences or [],
                ),
            )
            text = output["choices"][0]["text"]
            usage = output.get("usage", {})
            return CompletionResponse(
                text=text,
                model=Path(self.model_path).name if self.model_path else "llamacpp-gguf",
                usage=TokenUsage(
                    prompt_tokens=usage.get("prompt_tokens", len(full_prompt.split())),
                    completion_tokens=usage.get("completion_tokens", len(text.split())),
                    total_tokens=usage.get("total_tokens", len(full_prompt.split()) + len(text.split())),
                ),
                raw_output=output,
            )

        return CompletionResponse(
            text="[llama.cpp Offline / Model Not Loaded]",
            model="llamacpp-offline",
            usage=TokenUsage(
                prompt_tokens=len(full_prompt.split()),
                completion_tokens=5,
                total_tokens=len(full_prompt.split()) + 5,
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
        for chunk in res.text.split(" "):
            yield chunk + " "
            await asyncio.sleep(0.01)
