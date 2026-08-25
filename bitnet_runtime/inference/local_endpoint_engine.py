from __future__ import annotations
import httpx
from typing import Any, AsyncGenerator, Dict, List, Optional
from ..logging import logger
from .base import CompletionResponse, InferenceEngine, TokenUsage

class LocalEndpointEngine(InferenceEngine):
    """
    Adapter for local OpenAI-compatible endpoints (Ollama, LM Studio, vLLM, LocalAI).
    Zero cloud data transit ? points directly to localhost.
    """

    def __init__(
        self,
        endpoint_url: Optional[str] = None,
        model_name: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: float = 60.0,
    ):
        import os
        self.endpoint_url = (endpoint_url or os.getenv("BITNET_LOCAL_ENDPOINT_URL", "http://127.0.0.1:8080/v1")).rstrip("/")
        self.model_name = model_name or os.getenv("BITNET_LOCAL_MODEL_NAME", "llama3.2:1b")
        self.api_key = api_key or os.getenv("BITNET_API_KEY", "local")
        self.timeout = timeout

    async def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 1024,
        stop_sequences: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> CompletionResponse:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stop": stop_sequences,
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.post(f"{self.endpoint_url}/chat/completions", json=payload, headers=headers)
                res.raise_for_status()
                data = res.json()

            choice = data["choices"][0]["message"]
            text = choice.get("content", "")
            usage_data = data.get("usage", {})
            return CompletionResponse(
                text=text,
                model=self.model_name,
                usage=TokenUsage(
                    prompt_tokens=usage_data.get("prompt_tokens", 0),
                    completion_tokens=usage_data.get("completion_tokens", 0),
                    total_tokens=usage_data.get("total_tokens", 0),
                ),
                raw_output=data,
            )
        except Exception as e:
            logger.warning(f"Local endpoint call failed: {e}. Returning offline fallback.")
            return CompletionResponse(
                text="[Local Endpoint Offline] Processed prompt in offline fallback mode.",
                model=self.model_name,
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
