"""WebSocket hub for the dashboard.

Two endpoints:

* ``/ws/dashboard`` — JSON event stream. Subscribed to Redis ``events:new``;
  forwards each event to dashboards that have visibility on the camera.
* ``/ws/stream/{camera_id}`` — proxies the MPEG-TS byte stream produced by the
  worker process for that camera. The worker runs an internal HTTP server that
  yields an ``ts`` byte stream; the API just relays it to the browser.
"""
from __future__ import annotations

import asyncio
import json
import os

import httpx
import redis.asyncio as aioredis
from fastapi import APIRouter, Cookie, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, visible_camera_ids
from app.config import settings
from app.db.models import User
from app.services.auth import decode_token

router = APIRouter()

WORKERS_HOST = os.getenv("WORKERS_HOST", "workers")
WORKERS_PORT = int(os.getenv("WORKERS_PORT", "9000"))


def _user_from_ws(token: str | None, db: Session) -> User:
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED)
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise HTTPException(status.HTTP_401_UNAUTHORIZED)
        user = db.get(User, int(payload["sub"]))
    except Exception:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED)
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED)
    return user


@router.websocket("/ws/dashboard")
async def ws_dashboard(
    ws: WebSocket,
    token: str | None = Query(default=None),
    access_token: str | None = Cookie(default=None),
    db: Session = Depends(get_db),
) -> None:
    try:
        user = _user_from_ws(token or access_token, db)
    except HTTPException:
        await ws.close(code=4401)
        return

    visible = visible_camera_ids(db, user)
    await ws.accept()

    r = aioredis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, decode_responses=True)
    pubsub = r.pubsub()
    await pubsub.subscribe("events:new", "cameras:status")

    try:
        async for message in pubsub.listen():
            if message["type"] != "message":
                continue
            try:
                data = json.loads(message["data"])
            except (TypeError, json.JSONDecodeError):
                continue
            cam_id = data.get("camera_id")
            if visible is not None and cam_id is not None and cam_id not in visible:
                continue
            await ws.send_json({"channel": message["channel"], "data": data})
    except WebSocketDisconnect:
        pass
    finally:
        await pubsub.unsubscribe()
        await pubsub.close()
        await r.aclose()


@router.websocket("/ws/stream/{camera_id}")
async def ws_stream(
    ws: WebSocket,
    camera_id: int,
    token: str | None = Query(default=None),
    access_token: str | None = Cookie(default=None),
    db: Session = Depends(get_db),
) -> None:
    try:
        user = _user_from_ws(token or access_token, db)
    except HTTPException:
        await ws.close(code=4401)
        return

    visible = visible_camera_ids(db, user)
    if visible is not None and camera_id not in visible:
        await ws.close(code=4403)
        return

    await ws.accept()

    upstream = f"http://{WORKERS_HOST}:{WORKERS_PORT}/stream/{camera_id}.ts"
    try:
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream("GET", upstream) as resp:
                if resp.status_code != 200:
                    await ws.close(code=1011)
                    return
                async for chunk in resp.aiter_bytes():
                    if not chunk:
                        continue
                    await ws.send_bytes(chunk)
    except (WebSocketDisconnect, asyncio.CancelledError):
        return
    except Exception:
        try:
            await ws.close(code=1011)
        except Exception:
            pass
