"""HTTP server that exposes per-camera MPEG-TS streams to the FastAPI WS proxy.

The worker writes to an asyncio queue per camera; clients receive a continuous
``video/MP2T`` byte stream. We do simple fan-out: each subscriber gets newly
queued chunks from the moment they connect (no historical replay).
"""
from __future__ import annotations

import asyncio
import logging
from typing import Dict, Set

from aiohttp import web

log = logging.getLogger(__name__)


class StreamHub:
    def __init__(self):
        self._subs: Dict[int, Set[asyncio.Queue[bytes]]] = {}
        self._lock = asyncio.Lock()

    async def publish(self, camera_id: int, chunk: bytes) -> None:
        async with self._lock:
            queues = list(self._subs.get(camera_id, ()))
        for q in queues:
            if q.full():
                try:
                    q.get_nowait()
                except asyncio.QueueEmpty:
                    pass
            await q.put(chunk)

    async def subscribe(self, camera_id: int) -> asyncio.Queue[bytes]:
        q: asyncio.Queue[bytes] = asyncio.Queue(maxsize=128)
        async with self._lock:
            self._subs.setdefault(camera_id, set()).add(q)
        return q

    async def unsubscribe(self, camera_id: int, q: asyncio.Queue[bytes]) -> None:
        async with self._lock:
            subs = self._subs.get(camera_id)
            if subs and q in subs:
                subs.remove(q)
                if not subs:
                    del self._subs[camera_id]

    def has_subscribers(self, camera_id: int) -> bool:
        return bool(self._subs.get(camera_id))


def make_app(hub: StreamHub) -> web.Application:
    app = web.Application()

    async def stream_handler(request: web.Request) -> web.StreamResponse:
        cid = int(request.match_info["camera_id"])
        resp = web.StreamResponse(
            status=200,
            headers={
                "Content-Type": "video/MP2T",
                "Cache-Control": "no-store",
                "Connection": "keep-alive",
            },
        )
        await resp.prepare(request)

        q = await hub.subscribe(cid)
        try:
            while True:
                chunk = await q.get()
                await resp.write(chunk)
        except (asyncio.CancelledError, ConnectionResetError):
            pass
        finally:
            await hub.unsubscribe(cid, q)
        return resp

    async def health(_: web.Request) -> web.Response:
        return web.json_response({"status": "ok"})

    app.add_routes([
        web.get("/stream/{camera_id}.ts", stream_handler),
        web.get("/health", health),
    ])
    return app
