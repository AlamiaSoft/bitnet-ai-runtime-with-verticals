from __future__ import annotations
from typing import Any, Dict, List
from bitnet_runtime.inference.base import InferenceEngine
from bitnet_runtime.memory.semantic_memory import SemanticMemory

class PersonalMemoryQueryEngine:
    """Synthesizes answers from local memory vectors and citations."""

    def __init__(self, semantic_memory: SemanticMemory, inference_engine: InferenceEngine):
        self.semantic_memory = semantic_memory
        self.inference_engine = inference_engine

    async def answer_question(self, question: str, top_k: int = 4) -> Dict[str, Any]:
        results = await self.semantic_memory.query(question, top_k=top_k)
        if not results:
            return {
                "question": question,
                "answer": "No relevant local personal memories or documents found for this query.",
                "citations": [],
            }

        context_snippets = []
        citations = []
        for r in results:
            src = r.metadata.get("title") or r.metadata.get("source_path", "Local Document")
            context_snippets.append(f"[{src}]: {r.text_content}")
            citations.append({"title": src, "score": r.score, "chunk_id": r.id})

        prompt = f"""You are Personal Memory OS. Answer the question using ONLY the retrieved local memories below.
If the memories do not contain the answer, say so honestly.

Retrieved Memories:
{chr(10).join(context_snippets)}

Question: {question}
Answer:"""

        resp = await self.inference_engine.complete(prompt)
        return {
            "question": question,
            "answer": resp.text.strip(),
            "citations": citations,
        }
