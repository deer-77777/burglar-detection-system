"""OSNet (TorchReID) re-identification.

For each new ByteTrack track we crop the bounding box, embed it with OSNet, and
look up the closest match in a Redis-backed gallery scoped to the camera's Store
group. On a hit (cosine similarity >= 1 - REID_THRESHOLD) we reuse the existing
``person_global_id``; otherwise we mint a new one and add the embedding to the
gallery with a TTL of ``PERSON_GID_TTL_SEC``.
"""
from __future__ import annotations

import struct
import time
import uuid

import numpy as np
import redis
import torch

from worker.config import settings


class ReIDEngine:
    def __init__(self):
        from torchreid.utils import FeatureExtractor  # type: ignore[import-not-found]

        self._extractor = FeatureExtractor(
            model_name=settings.REID_MODEL_NAME,
            model_path=settings.REID_MODEL_PATH,
            device=f"cuda:{settings.WORKER_GPU_DEVICE}" if torch.cuda.is_available() else "cpu",
        )
        self._r = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT)

    def embed(self, crops: list[np.ndarray]) -> np.ndarray:
        if not crops:
            return np.zeros((0, 512), dtype=np.float32)
        feats = self._extractor(crops).cpu().numpy()
        norms = np.linalg.norm(feats, axis=1, keepdims=True) + 1e-9
        return feats / norms

    def match_or_create(self, store_group_id: int | None, embedding: np.ndarray) -> str:
        key = f"reid:gallery:{store_group_id or 'none'}"
        existing = self._r.hgetall(key)
        best_pgid: str | None = None
        best_sim = -1.0
        for raw_pgid, raw_emb in existing.items():
            other = np.frombuffer(raw_emb, dtype=np.float32)
            if other.shape != embedding.shape:
                continue
            sim = float(np.dot(embedding, other))
            if sim > best_sim:
                best_sim = sim
                best_pgid = raw_pgid.decode("utf-8")

        if best_pgid is not None and best_sim >= (1.0 - settings.REID_THRESHOLD):
            self._r.hset(key, best_pgid, embedding.astype(np.float32).tobytes())
            self._r.expire(key, settings.PERSON_GID_TTL_SEC)
            self._r.zadd(f"{key}:lru", {best_pgid: time.time()})
            return best_pgid

        pgid = uuid.uuid4().hex[:16]
        self._r.hset(key, pgid, embedding.astype(np.float32).tobytes())
        self._r.expire(key, settings.PERSON_GID_TTL_SEC)
        self._r.zadd(f"{key}:lru", {pgid: time.time()})
        self._evict_stale(key)
        return pgid

    def _evict_stale(self, key: str) -> None:
        cutoff = time.time() - settings.PERSON_GID_TTL_SEC
        stale = self._r.zrangebyscore(f"{key}:lru", "-inf", cutoff)
        if stale:
            self._r.hdel(key, *stale)
            self._r.zremrangebyscore(f"{key}:lru", "-inf", cutoff)
