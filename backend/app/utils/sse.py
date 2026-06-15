"""Server-Sent Events utilities."""

import asyncio
import json
from typing import Any, AsyncGenerator


class SSEManager:
    """Manages SSE connections for document status updates."""

    def __init__(self):
        self._listeners: list[asyncio.Queue] = []

    def add_listener(self) -> asyncio.Queue:
        """Register a new listener and return its queue."""
        queue: asyncio.Queue = asyncio.Queue()
        self._listeners.append(queue)
        return queue

    def remove_listener(self, queue: asyncio.Queue):
        """Remove a listener."""
        if queue in self._listeners:
            self._listeners.remove(queue)

    async def broadcast(self, event: str, data: dict[str, Any]):
        """Send an event to all connected listeners."""
        message = f"event: {event}\ndata: {json.dumps(data)}\n\n"
        for queue in self._listeners:
            await queue.put(message)

    async def stream(self, queue: asyncio.Queue) -> AsyncGenerator[str, None]:
        """Yield events from a listener's queue."""
        try:
            while True:
                message = await asyncio.wait_for(queue.get(), timeout=30.0)
                yield message
        except asyncio.TimeoutError:
            # Send keepalive
            yield ": keepalive\n\n"
        except asyncio.CancelledError:
            pass


# Global instance for document status events
status_sse_manager = SSEManager()
