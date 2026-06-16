"""Live CloudEvents WebSocket for the steward console (Phase 3).

`GET /events/ws` streams every CloudEvent the runtime emits. WebSocket upgrades
bypass the HTTP Zero-Trust middleware, so identity/role are checked here (the dev
stand-in, same model as the X-Florence-* headers; real OIDC later).
"""
from __future__ import annotations

import asyncio

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, status

from ..config import settings
from ..events_stream import hub

router = APIRouter()


@router.websocket("/events/ws")
async def events_ws(websocket: WebSocket,
                    identity: str | None = Query(default=None),
                    role: str | None = Query(default=None)) -> None:
    if settings.require_identity and (not identity or not role):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    await websocket.accept()
    hub.bind_loop(asyncio.get_running_loop())
    queue = hub.subscribe()
    try:
        while True:
            event = await queue.get()
            await websocket.send_json(event)
    except WebSocketDisconnect:
        pass
    finally:
        hub.unsubscribe(queue)
