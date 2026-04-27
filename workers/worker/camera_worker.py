"""Per-camera worker.

Each camera gets one ``CameraWorker`` task that:

1. Opens the RTSP stream with PyAV. Reconnects with exponential backoff on failure.
2. For every demuxed video packet:
   * Pushes the raw packet into the ring buffer (for clip extraction).
   * Re-muxes it as MPEG-TS and publishes to the StreamHub for the dashboard.
3. At the configured target FPS, decodes a frame and runs:
   detector -> ByteTrack -> ReID gallery match -> state-machine update.
4. On a threshold crossing, writes a snapshot, schedules a clip dump, inserts an
   ``events`` row, and PUBLISHes ``events:new`` on Redis so the API forwards it
   to dashboards.
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from datetime import datetime
from io import BytesIO
from pathlib import Path

import av
import cv2
import numpy as np
import redis.asyncio as aioredis

from worker.config import settings
from worker.crypto import decrypt_str
from worker.db import Camera, CameraConnectionLog, Event, SessionLocal, group_path, store_group_id_for
from worker.detector import PersonDetector
from worker.reid import ReIDEngine
from worker.ring_buffer import PacketRingBuffer
from worker.state import CameraStateMachine
from worker.stream_server import StreamHub
from worker.tracker import ByteTracker

log = logging.getLogger(__name__)


class CameraWorker:
    def __init__(self, camera_id: int, hub: StreamHub, detector: PersonDetector, reid: ReIDEngine):
        self.camera_id = camera_id
        self._hub = hub
        self._detector = detector
        self._reid = reid
        self._stop = asyncio.Event()
        self._redis = aioredis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT)

    def stop(self) -> None:
        self._stop.set()

    async def run(self) -> None:
        backoff = 1.0
        while not self._stop.is_set():
            try:
                await self._run_once()
                backoff = 1.0
            except asyncio.CancelledError:
                return
            except Exception as exc:
                log.exception("worker[%s] error: %s", self.camera_id, exc)
                self._log_connection(False, "ERR_UNKNOWN", str(exc)[:1024])
                self._set_status("error")
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 60.0)

    async def _run_once(self) -> None:
        cam = self._load_camera()
        if cam is None or not cam.display_enabled:
            await asyncio.sleep(2.0)
            return

        rtsp_url = decrypt_str(cam.rtsp_url_enc)
        ring = PacketRingBuffer(seconds=settings.RING_BUFFER_SEC)
        tracker = ByteTracker(frame_rate=settings.TARGET_FPS)
        state = CameraStateMachine(cam.dwell_limit_sec, cam.count_limit, cam.count_window_sec)

        with SessionLocal() as session:
            sgid = store_group_id_for(session, cam.group_id)
            gpath = group_path(session, cam.group_id)

        self._set_status("live")
        self._log_connection(True, None, None)

        opts = {"rtsp_transport": "tcp", "stimeout": "5000000", "rw_timeout": "5000000"}
        with av.open(rtsp_url, options=opts, timeout=10.0) as container:
            in_stream = next(s for s in container.streams if s.type == "video")
            in_stream.thread_type = "AUTO"

            from fractions import Fraction
            tb = in_stream.time_base or Fraction(1, 90000)
            ring.remember_stream(
                codec_name=in_stream.codec_context.name,
                width=in_stream.codec_context.width,
                height=in_stream.codec_context.height,
                time_base=tb,
                extradata=in_stream.codec_context.extradata,
            )

            ts_buffer = BytesIO()
            ts_out = av.open(ts_buffer, mode="w", format="mpegts")
            ts_stream = ts_out.add_stream(template=in_stream)

            target_dt = 1.0 / max(settings.TARGET_FPS, 1)
            last_inference = 0.0

            for packet in container.demux(in_stream):
                if self._stop.is_set():
                    break
                if packet.dts is None:
                    continue
                wall_t = time.time()

                try:
                    ring.push(packet, wall_t=wall_t)
                except Exception:
                    log.warning("ring buffer push failed for camera %s", self.camera_id, exc_info=True)

                try:
                    packet.stream = ts_stream
                    ts_out.mux(packet)
                    chunk = ts_buffer.getvalue()
                    if chunk:
                        ts_buffer.seek(0)
                        ts_buffer.truncate()
                        if self._hub.has_subscribers(self.camera_id):
                            await self._hub.publish(self.camera_id, chunk)
                except Exception:
                    pass

                if wall_t - last_inference < target_dt:
                    continue

                if not packet.is_keyframe:
                    continue

                try:
                    frames = packet.decode()
                except av.AVError:
                    frames = []
                if not frames:
                    continue
                frame = frames[-1].to_ndarray(format="bgr24")
                last_inference = wall_t

                detections = await asyncio.to_thread(self._detector.detect, frame)
                tracks = await asyncio.to_thread(tracker.update, detections, frame.shape)
                if not tracks:
                    continue

                crops = []
                for t in tracks:
                    x1, y1, x2, y2 = max(0, int(t.x1)), max(0, int(t.y1)), int(t.x2), int(t.y2)
                    crop = frame[y1:y2, x1:x2]
                    if crop.size == 0:
                        crops.append(np.zeros((128, 64, 3), dtype=np.uint8))
                    else:
                        crops.append(cv2.resize(crop, (64, 128)))

                embeddings = await asyncio.to_thread(self._reid.embed, crops)

                for t, emb in zip(tracks, embeddings):
                    pgid = await asyncio.to_thread(self._reid.match_or_create, sgid, emb)
                    for threshold in state.update_seen(pgid, wall_t):
                        await self._emit_event(cam, gpath, threshold, frame, ring, wall_t)

            ts_out.close()

    def _load_camera(self) -> Camera | None:
        with SessionLocal() as session:
            return session.get(Camera, self.camera_id)

    def _set_status(self, status: str) -> None:
        with SessionLocal() as session:
            cam = session.get(Camera, self.camera_id)
            if cam is None:
                return
            cam.status = status
            cam.last_status_at = datetime.utcnow()
            session.commit()

    def _log_connection(self, success: bool, code: str | None, detail: str | None) -> None:
        with SessionLocal() as session:
            session.add(CameraConnectionLog(
                camera_id=self.camera_id, success=success, error_code=code, error_detail=detail,
            ))
            session.commit()

    async def _emit_event(
        self, cam: Camera, gpath: str, threshold, frame: np.ndarray, ring: PacketRingBuffer, wall_t: float,
    ) -> None:
        ts = datetime.utcfromtimestamp(threshold.start_time).strftime("%Y%m%d_%H%M%S")
        snap_dir = Path(settings.SNAPS_DIR) / str(cam.id)
        clip_dir = Path(settings.CLIPS_DIR) / str(cam.id)
        snap_dir.mkdir(parents=True, exist_ok=True)
        clip_dir.mkdir(parents=True, exist_ok=True)

        snap_rel = f"{cam.id}/{ts}_{threshold.kind}_{threshold.person_global_id}.jpg"
        snap_path = Path(settings.SNAPS_DIR) / snap_rel
        cv2.imwrite(str(snap_path), frame)

        clip_rel = f"{cam.id}/{ts}_{threshold.kind}_{threshold.person_global_id}.ts"
        clip_path = Path(settings.CLIPS_DIR) / clip_rel
        ring.snapshot_after(threshold.end_time, settings.RING_BUFFER_SEC, clip_path)

        with SessionLocal() as session:
            evt = Event(
                camera_id=cam.id,
                group_path=gpath,
                person_global_id=threshold.person_global_id,
                event_type=threshold.kind,
                start_time=datetime.utcfromtimestamp(threshold.start_time),
                end_time=datetime.utcfromtimestamp(threshold.end_time),
                duration_sec=threshold.duration_sec,
                appearance_count=threshold.appearance_count,
                snapshot_path=snap_rel,
                clip_path=clip_rel,
                review_status="NEW",
            )
            session.add(evt)
            session.commit()
            event_id = evt.id

        await self._redis.publish(
            "events:new",
            json.dumps({
                "event_id": event_id,
                "camera_id": cam.id,
                "group_path": gpath,
                "person_global_id": threshold.person_global_id,
                "event_type": threshold.kind,
                "start_time": datetime.utcfromtimestamp(threshold.start_time).isoformat(),
                "end_time": datetime.utcfromtimestamp(threshold.end_time).isoformat(),
                "duration_sec": threshold.duration_sec,
                "appearance_count": threshold.appearance_count,
            }),
        )
