"""YOLO11 person detector wrapper.

Loads a model once per worker process and exposes a single ``detect(frame)``
that returns a list of ``(x1, y1, x2, y2, score)`` for the ``person`` class.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from worker.config import settings


@dataclass
class Detection:
    x1: float
    y1: float
    x2: float
    y2: float
    score: float


class PersonDetector:
    PERSON_CLASS_ID = 0

    def __init__(self, conf: float = 0.35, iou: float = 0.5):
        from ultralytics import YOLO  # type: ignore[import-not-found]

        path = Path(settings.YOLO_MODEL_PATH)
        if not path.exists():
            raise FileNotFoundError(
                f"YOLO11 weights not found at {path}. "
                f"Place the bundled model file there before starting the worker."
            )
        self._model = YOLO(str(path))
        self._conf = conf
        self._iou = iou
        self._device = f"cuda:{settings.WORKER_GPU_DEVICE}"

    def detect(self, frame: np.ndarray) -> list[Detection]:
        results = self._model.predict(
            frame, classes=[self.PERSON_CLASS_ID], conf=self._conf, iou=self._iou,
            device=self._device, verbose=False,
        )
        if not results:
            return []
        r = results[0]
        if r.boxes is None or len(r.boxes) == 0:
            return []
        xyxy = r.boxes.xyxy.cpu().numpy()
        scores = r.boxes.conf.cpu().numpy()
        out: list[Detection] = []
        for (x1, y1, x2, y2), s in zip(xyxy, scores):
            out.append(Detection(float(x1), float(y1), float(x2), float(y2), float(s)))
        return out
