"""ByteTrack wrapper.

Ultralytics ships a ByteTrack implementation; we use it directly with a thin
adapter so the rest of the pipeline stays decoupled.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class Track:
    track_id: int
    x1: float
    y1: float
    x2: float
    y2: float
    score: float


class ByteTracker:
    def __init__(self, frame_rate: int = 8):
        from ultralytics.trackers.byte_tracker import BYTETracker  # type: ignore[import-not-found]
        from types import SimpleNamespace

        args = SimpleNamespace(
            track_high_thresh=0.5,
            track_low_thresh=0.1,
            new_track_thresh=0.6,
            track_buffer=30,
            match_thresh=0.8,
            fuse_score=True,
        )
        self._t = BYTETracker(args, frame_rate=frame_rate)

    def update(self, detections: list, frame_shape: tuple[int, int]) -> list[Track]:
        if not detections:
            return []
        h, w = frame_shape[:2]
        det_arr = np.array(
            [[d.x1, d.y1, d.x2, d.y2, d.score, 0] for d in detections], dtype=np.float32
        )

        class _Boxes:
            def __init__(self, arr):
                self.xyxy = arr[:, :4]
                self.conf = arr[:, 4]
                self.cls = arr[:, 5]
                self.xywh = np.column_stack(
                    [
                        (arr[:, 0] + arr[:, 2]) / 2,
                        (arr[:, 1] + arr[:, 3]) / 2,
                        arr[:, 2] - arr[:, 0],
                        arr[:, 3] - arr[:, 1],
                    ]
                )

        results_like = type("R", (), {"conf": det_arr[:, 4], "xywh": _Boxes(det_arr).xywh, "cls": det_arr[:, 5], "xyxy": det_arr[:, :4]})
        tracks_arr = self._t.update(results_like, img=np.zeros((h, w, 3), dtype=np.uint8))
        out: list[Track] = []
        for row in tracks_arr:
            x1, y1, x2, y2, tid, score, _cls = row[:7]
            out.append(Track(int(tid), float(x1), float(y1), float(x2), float(y2), float(score)))
        return out
