"""In-memory frame ring buffer for pre/post-event clip dumps.

Stores raw H.264 packets keyed by PTS. ``dump_window`` writes a self-contained MP4
spanning ``pre_seconds`` before ``trigger_t`` and ``post_seconds`` after.
"""
from __future__ import annotations

import threading
import time
from collections import deque
from pathlib import Path
from typing import Deque

import av


class PacketRingBuffer:
    def __init__(self, seconds: int, codec_ctx_input: av.CodecContext | None = None):
        self.seconds = seconds
        self._lock = threading.Lock()
        self._packets: Deque[tuple[float, bytes, int]] = deque()  # (wall_t, packet_bytes, is_keyframe)
        self._stream_template: dict | None = None

    def remember_stream(self, codec_name: str, width: int, height: int, time_base: float, extradata: bytes | None) -> None:
        self._stream_template = {
            "codec_name": codec_name,
            "width": width,
            "height": height,
            "time_base": time_base,
            "extradata": extradata,
        }

    def push(self, packet_bytes: bytes, is_keyframe: bool, wall_t: float | None = None) -> None:
        wall_t = wall_t if wall_t is not None else time.time()
        with self._lock:
            self._packets.append((wall_t, packet_bytes, 1 if is_keyframe else 0))
            cutoff = wall_t - self.seconds
            while self._packets and self._packets[0][0] < cutoff:
                self._packets.popleft()

    def snapshot_after(self, trigger_t: float, post_seconds: int, out_path: Path) -> None:
        """Spawn a background writer that waits for ``post_seconds`` and dumps an MP4.

        The buffer keeps growing as the worker runs; we wait, then slice [trigger_t - pre, trigger_t + post].
        """
        threading.Thread(
            target=self._write_clip,
            args=(trigger_t, post_seconds, out_path),
            daemon=True,
        ).start()

    def _write_clip(self, trigger_t: float, post_seconds: int, out_path: Path) -> None:
        time.sleep(post_seconds + 0.5)
        if self._stream_template is None:
            return
        with self._lock:
            packets = list(self._packets)
        pre = trigger_t - self.seconds
        end = trigger_t + post_seconds
        slice_ = [p for p in packets if pre <= p[0] <= end]
        if not slice_:
            return
        # Find the first keyframe at or before the slice start.
        ki = next((i for i, p in enumerate(slice_) if p[2]), 0)
        slice_ = slice_[ki:]

        out_path.parent.mkdir(parents=True, exist_ok=True)
        with av.open(str(out_path), mode="w", format="mp4") as out:
            tmpl = self._stream_template
            stream = out.add_stream(tmpl["codec_name"])
            stream.width = tmpl["width"]
            stream.height = tmpl["height"]
            if tmpl["extradata"]:
                stream.codec_context.extradata = tmpl["extradata"]
            t0 = slice_[0][0]
            for wall_t, raw, _kf in slice_:
                pkt = av.Packet(raw)
                pkt.pts = int((wall_t - t0) * 90000)
                pkt.dts = pkt.pts
                pkt.time_base = av.time_base = av.time_base  # noqa: F841 - placeholder
                pkt.stream = stream
                try:
                    out.mux(pkt)
                except Exception:
                    continue
