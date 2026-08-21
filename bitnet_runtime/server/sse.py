from __future__ import annotations
import asyncio
import json
from typing import Any, AsyncGenerator, Dict, List

class EventBroadcaster:
    """Broadcaster for streaming realtime agent events to connected SSE clients."""

    def __init__(self):
        self._listeners: List[asyncio.Queue] = []

    async def subscribe(self) -> AsyncGenerator[str, None]:
        queue = asyncio.Queue()
        self._listeners.append(queue)
        try:
            while True:
                data = await queue.get()
                yield f"data: {json.dumps(data)}\n\n"
        finally:
            self._listeners.remove(queue)

    async def broadcast(self, event_data: Dict[str, Any]) -> None:
        for q in self._listeners:
            await q.put(event_data)

broadcaster = EventBroadcaster()
