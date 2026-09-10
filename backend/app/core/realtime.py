import asyncio
import json
from typing import Any, Set
from fastapi import WebSocket


class AlertBroadcaster:
    """In-process realtime alert broadcaster for the PoC.

    Production deployments should back this with Redis Pub/Sub or Kafka so
    alerts can be delivered across multiple API instances.
    """

    def __init__(self) -> None:
        self._clients: Set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._clients.add(websocket)

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._clients.discard(websocket)

    async def broadcast(self, event: dict[str, Any]) -> None:
        payload = json.dumps(event, default=str)
        async with self._lock:
            clients = list(self._clients)
        dead = []
        for client in clients:
            try:
                await client.send_text(payload)
            except Exception:
                dead.append(client)
        if dead:
            async with self._lock:
                for client in dead:
                    self._clients.discard(client)

    def active_count(self) -> int:
        return len(self._clients)


alert_broadcaster = AlertBroadcaster()


