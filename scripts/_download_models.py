"""Fetch YOLO11 + OSNet ReID weights into /out.

Runs inside the python:3.11-slim throwaway container spawned by
``scripts/download-models.sh``. Each variant is skipped if a non-empty file
of the same name already exists in /out — re-runs are cheap.

We use Ultralytics for YOLO (its asset URLs change with releases, so the
library is the source of truth) and download OSNet weights directly from
TorchReID's canonical Google Drive model zoo (stable since 2019). The worker
container still uses torchreid for inference; this script only mirrors the
weight files so the worker has them on disk at boot.
"""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

OUT = Path("/out")
OUT.mkdir(parents=True, exist_ok=True)

YOLO_VARIANTS = [v.strip() for v in os.environ.get("YOLO_VARIANTS", "yolo11n").split(",") if v.strip()]
REID_VARIANTS = [v.strip() for v in os.environ.get("REID_VARIANTS", "osnet_x0_25").split(",") if v.strip()]

# Canonical OSNet pretrained weight gdrive IDs from
# https://github.com/KaiyangZhou/deep-person-reid/blob/master/torchreid/utils/model_zoo.py
OSNET_GDRIVE_IDS: dict[str, str] = {
    "osnet_x1_0":     "1LaG1EJpHrxdAxKnSCJ_i0u-nbxSAeiFY",
    "osnet_x0_75":    "1uwA9fElHOk3ZogwbeY5GkLI6QPTX70Hq",
    "osnet_x0_5":     "16DGLbZukvVYgINws8u8deSaOqjybZ83i",
    "osnet_x0_25":    "1rb8UN5ZzPKRc_xvtHlyDh-cSz88YX9hs",
    "osnet_ibn_x1_0": "1sr90V6irlYYDd4_4ISU2iruoRG8J__6l",
    "osnet_ain_x1_0": "1NEEYDHmbnT-ZXCpsBKupg6BdcsdZf-1n",
}


def _have(p: Path, min_bytes: int = 1_000_000) -> bool:
    return p.exists() and p.stat().st_size >= min_bytes


def _human(n: float) -> str:
    for unit in ("B", "K", "M", "G"):
        if n < 1024:
            return f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}T"


# --- YOLO11 -----------------------------------------------------------------
print("\n=== YOLO11 ===")
from ultralytics import YOLO  # type: ignore[import-not-found]

for name in YOLO_VARIANTS:
    out = OUT / f"{name}.pt"
    if _have(out):
        print(f"  ✓ {out.name}  (already present, {_human(out.stat().st_size)})")
        continue
    print(f"  ↓ {name} …")
    YOLO(f"{name}.pt")  # downloads if missing
    candidates = [
        Path.cwd() / f"{name}.pt",
        Path.home() / ".cache" / "ultralytics" / f"{name}.pt",
        Path("/root") / f"{name}.pt",
    ]
    src = next((c for c in candidates if c.exists()), None)
    if not src:
        sys.exit(f"could not locate downloaded {name}.pt")
    shutil.copy(src, out)
    print(f"  ✓ {out.name}  ({_human(out.stat().st_size)})")


# --- OSNet ReID -------------------------------------------------------------
print("\n=== OSNet ReID ===")
import gdown  # type: ignore[import-not-found]

for name in REID_VARIANTS:
    out = OUT / f"{name}.pth"
    if _have(out):
        print(f"  ✓ {out.name}  (already present, {_human(out.stat().st_size)})")
        continue
    gid = OSNET_GDRIVE_IDS.get(name)
    if not gid:
        print(f"  ! unknown OSNet variant: {name}  (known: {sorted(OSNET_GDRIVE_IDS)})")
        continue
    print(f"  ↓ {name}  (gdrive {gid})")
    gdown.download(id=gid, output=str(out), quiet=False)
    if not _have(out):
        sys.exit(f"download failed for {name} — try re-running, gdrive may be rate-limited")
    print(f"  ✓ {out.name}  ({_human(out.stat().st_size)})")


print("\nAll downloads complete in /out.")
