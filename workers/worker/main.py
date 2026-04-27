"""Worker process entrypoint.

Watches the ``cameras:changed`` Redis channel and the ``cameras`` table to
keep one ``CameraWorker`` task alive per enabled camera. Boots the StreamHub
HTTP server on STREAM_HTTP_PORT for the API to proxy.
"""
from __future__ import annotations

import asyncio
import logging
import signal
from contextlib import suppress

import redis.asyncio as aioredis
import structlog
from aiohttp import web
from sqlalchemy import select

from worker.camera_worker import CameraWorker
from worker.config import settings
from worker.db import Camera, SessionLocal
from worker.detector import PersonDetector
from worker.reid import ReIDEngine
from worker.stream_server import StreamHub, make_app


def _configure_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        logger_factory=structlog.PrintLoggerFactory(),
    )


async def _serve_stream(hub: StreamHub, stop: asyncio.Event) -> None:
    app = make_app(hub)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=settings.STREAM_HTTP_PORT)
    await site.start()
    try:
        await stop.wait()
    finally:
        await runner.cleanup()


async def _list_active_cameras() -> dict[int, Camera]:
    with SessionLocal() as session:
        rows = session.execute(select(Camera).where(Camera.display_enabled.is_(True))).scalars().all()
        return {c.id: c for c in rows}


async def _supervise(hub: StreamHub, detector: PersonDetector, reid: ReIDEngine, stop: asyncio.Event) -> None:
    workers: dict[int, tuple[CameraWorker, asyncio.Task]] = {}

    async def _spawn(cid: int) -> None:
        cw = CameraWorker(cid, hub, detector, reid)
        task = asyncio.create_task(cw.run(), name=f"cam-{cid}")
        workers[cid] = (cw, task)

    async def _stop(cid: int) -> None:
        cw, task = workers.pop(cid, (None, None))
        if cw and task:
            cw.stop()
            with suppress(asyncio.CancelledError):
                task.cancel()
                await task

    async def _reconcile() -> None:
        active = await _list_active_cameras()
        wanted = set(active.keys())
        if len(wanted) > settings.WORKER_MAX_CAMERAS:
            wanted = set(list(wanted)[: settings.WORKER_MAX_CAMERAS])
        running = set(workers.keys())
        for cid in running - wanted:
            await _stop(cid)
        for cid in wanted - running:
            await _spawn(cid)

    r = aioredis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, decode_responses=True)
    pubsub = r.pubsub()
    await pubsub.subscribe("cameras:changed")

    await _reconcile()
    last_periodic = asyncio.get_event_loop().time()

    try:
        while not stop.is_set():
            try:
                msg = await asyncio.wait_for(pubsub.get_message(ignore_subscribe_messages=True), timeout=10.0)
            except asyncio.TimeoutError:
                msg = None
            if msg or asyncio.get_event_loop().time() - last_periodic > 30.0:
                await _reconcile()
                last_periodic = asyncio.get_event_loop().time()
    finally:
        for cid in list(workers):
            await _stop(cid)
        await pubsub.unsubscribe()
        await pubsub.close()
        await r.aclose()


async def main() -> None:
    _configure_logging()
    log = structlog.get_logger("worker")
    log.info("starting", max_cameras=settings.WORKER_MAX_CAMERAS)

    detector = PersonDetector()
    reid = ReIDEngine()
    hub = StreamHub()

    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop.set)

    await asyncio.gather(_serve_stream(hub, stop), _supervise(hub, detector, reid, stop))


if __name__ == "__main__":
    asyncio.run(main())
