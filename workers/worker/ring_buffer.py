"""In-memory packet ring buffer for pre/post-event clip dumps.

The buffer stores raw H.264 video packets with their original ``pts/dts/time_base``
so we can re-mux them into a self-contained MPEG-TS clip without re-encoding.

Why MPEG-TS: it's the same container the live worker→browser pipe uses, supports
mid-stream segmentation, and tolerates being sliced at any keyframe. We pick
TS over MP4 because MP4 needs a moov atom written at file finalize and a clean
B-frame DTS ordering — both painful to recreate from a raw packet stream.

Design:

* ``push(packet)`` is called from the demux loop after each packet. We snapshot
  the packet's ``data`` bytes and timing fields, then drop entries older than
  the window.
* ``snapshot_after(trigger_t, post_seconds, out_path)`` spawns a daemon thread
  that waits ``post_seconds + epsilon`` so the post-event tail accumulates,
  then writes the slice to ``out_path`` as MPEG-TS.
* The first packet in the slice is rebased to PTS/DTS = 0 so the player
  starts at t=0 instead of whatever absolute timestamp the camera emitted.
"""
from __future__ import annotations

import logging
import threading
import time
from collections import deque
from fractions import Fraction
from pathlib import Path
from typing import Deque

import av

log = logging.getLogger(__name__)


class _Stored:
    __slots__ = ("wall_t", "data", "pts", "dts", "is_keyframe")

    def __init__(self, wall_t: float, data: bytes, pts: int | None, dts: int | None, is_keyframe: bool):
        self.wall_t = wall_t
        self.data = data
        self.pts = pts
        self.dts = dts
        self.is_keyframe = is_keyframe


class PacketRingBuffer:
    """Fixed-window deque of recent video packets, thread-safe for one writer + one reader."""

    def __init__(self, seconds: int):
        self.seconds = seconds
        self._lock = threading.Lock()
        self._packets: Deque[_Stored] = deque()
        self._codec_name: str | None = None
        self._width: int | None = None
        self._height: int | None = None
        self._time_base: Fraction | None = None
        self._extradata: bytes | None = None

    def remember_stream(
        self,
        codec_name: str,
        width: int,
        height: int,
        time_base: Fraction,
        extradata: bytes | None,
    ) -> None:
        self._codec_name = codec_name
        self._width = width
        self._height = height
        self._time_base = time_base
        self._extradata = extradata

    def push(self, packet: av.Packet, wall_t: float | None = None) -> None:
        """Snapshot the packet (data + timing) into the ring buffer."""
        wt = wall_t if wall_t is not None else time.time()
        try:
            data = bytes(packet)
        except Exception:
            return
        entry = _Stored(
            wall_t=wt,
            data=data,
            pts=packet.pts,
            dts=packet.dts,
            is_keyframe=bool(packet.is_keyframe),
        )
        with self._lock:
            self._packets.append(entry)
            cutoff = wt - self.seconds
            while self._packets and self._packets[0].wall_t < cutoff:
                self._packets.popleft()

    def snapshot_after(self, trigger_t: float, post_seconds: int, out_path: Path) -> None:
        """Spawn a daemon thread that waits ``post_seconds`` then dumps the slice as TS."""
        threading.Thread(
            target=self._write_clip,
            args=(trigger_t, post_seconds, out_path),
            daemon=True,
            name=f"clip-writer-{out_path.name}",
        ).start()

    def _write_clip(self, trigger_t: float, post_seconds: int, out_path: Path) -> None:
        time.sleep(post_seconds + 0.5)
        if (
            self._codec_name is None
            or self._width is None
            or self._height is None
            or self._time_base is None
        ):
            log.warning("clip writer: stream config not remembered yet")
            return
        with self._lock:
            packets = list(self._packets)

        pre = trigger_t - self.seconds
        end = trigger_t + post_seconds
        slice_ = [p for p in packets if pre <= p.wall_t <= end]
        if not slice_:
            log.warning("clip writer: no packets in window for %s", out_path.name)
            return

        # Drop everything before the first keyframe — H.264 can't decode otherwise.
        first_kf = next((i for i, p in enumerate(slice_) if p.is_keyframe), None)
        if first_kf is None:
            log.warning("clip writer: no keyframe in window for %s", out_path.name)
            return
        slice_ = slice_[first_kf:]

        # Rebase timestamps so the clip starts at PTS=0.
        base_pts = slice_[0].pts if slice_[0].pts is not None else 0
        base_dts = slice_[0].dts if slice_[0].dts is not None else base_pts

        out_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with av.open(str(out_path), mode="w", format="mpegts") as out:
                stream = out.add_stream(self._codec_name)
                stream.width = self._width
                stream.height = self._height
                stream.time_base = self._time_base
                if self._extradata:
                    stream.codec_context.extradata = self._extradata

                for p in slice_:
                    pkt = av.Packet(p.data)
                    pkt.stream = stream
                    pkt.time_base = self._time_base
                    if p.pts is not None:
                        pkt.pts = p.pts - base_pts
                    if p.dts is not None:
                        pkt.dts = p.dts - base_dts
                    if p.is_keyframe:
                        pkt.is_keyframe = True
                    try:
                        out.mux(pkt)
                    except av.AVError as exc:
                        log.debug("clip mux skipped a packet: %s", exc)
                        continue
        except Exception:
            log.exception("clip writer failed for %s", out_path.name)
