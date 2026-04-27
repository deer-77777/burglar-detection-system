# Model weights

The detection worker loads its model files from this directory at startup.
Files in here are intentionally *not* committed to git — fetch them once on a
machine with internet access, then ship them as part of the offline USB bundle.

## Quick start

From the repo root, on a machine with Docker:

```bash
./scripts/download-models.sh
```

That writes the default set into this directory:

| File | Purpose | Size (approx) |
|---|---|---|
| `yolo11n.pt` | YOLO11 nano person detector — default, fastest | ~5 MB |
| `yolo11s.pt` | YOLO11 small — better accuracy, still fast | ~19 MB |
| `yolo11m.pt` | YOLO11 medium — recommended on a 5090 | ~40 MB |
| `osnet_x0_25.pth` | OSNet ReID, smallest variant — default | ~4 MB |
| `osnet_x0_5.pth` | OSNet ReID, mid-size | ~8 MB |
| `osnet_x1_0.pth` | OSNet ReID, full-size — best ReID accuracy | ~17 MB |

## Picking variants

Change which sizes the script fetches via env vars (comma-separated, no
spaces):

```bash
YOLO_VARIANTS=yolo11n,yolo11l \
REID_VARIANTS=osnet_x1_0 \
./scripts/download-models.sh
```

The worker boots with `yolo11n.pt` + `osnet_x0_25.pth` by default. To switch,
set `YOLO_MODEL_PATH` / `REID_MODEL_NAME` / `REID_MODEL_PATH` in `.env`:

```
YOLO_MODEL_PATH=/app/models/yolo11m.pt
REID_MODEL_NAME=osnet_x1_0
REID_MODEL_PATH=/app/models/osnet_x1_0.pth
```

then `docker compose --profile gpu restart workers`.
