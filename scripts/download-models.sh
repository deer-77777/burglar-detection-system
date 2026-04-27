#!/usr/bin/env bash
# Download model weights into workers/models/ for the detection pipeline.
#
# Usage:
#   ./scripts/download-models.sh
#
# Override which variants to fetch via env vars (comma-separated):
#   YOLO_VARIANTS=yolo11n,yolo11s,yolo11m  ./scripts/download-models.sh
#   REID_VARIANTS=osnet_x0_25,osnet_x1_0   ./scripts/download-models.sh
#
# Defaults pull what the worker boots with: yolo11n + osnet_x0_25.
# For a beefier GPU (e.g. RTX 5090) you'll typically also want yolo11m and
# the larger OSNet variants for higher ReID accuracy.
#
# Requires Docker. No host Python setup needed — runs in a throwaway
# python:3.11-slim container.

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MODELS_DIR="$ROOT/workers/models"
mkdir -p "$MODELS_DIR"

YOLO_VARIANTS="${YOLO_VARIANTS:-yolo11n,yolo11s,yolo11m}"
REID_VARIANTS="${REID_VARIANTS:-osnet_x0_25,osnet_x0_5,osnet_x1_0}"

echo "==> writing to $MODELS_DIR"
echo "    YOLO:  $YOLO_VARIANTS"
echo "    OSNet: $REID_VARIANTS"
echo

docker run --rm \
  -e YOLO_VARIANTS="$YOLO_VARIANTS" \
  -e REID_VARIANTS="$REID_VARIANTS" \
  -e PIP_DISABLE_PIP_VERSION_CHECK=1 \
  -v "$MODELS_DIR:/out" \
  -v "$ROOT/scripts/_download_models.py:/work/_download_models.py:ro" \
  -w /work \
  python:3.11-slim bash -c '
    set -e
    export DEBIAN_FRONTEND=noninteractive
    apt-get update -qq >/dev/null
    apt-get install -y -qq --no-install-recommends \
        libgl1 libglib2.0-0 ca-certificates >/dev/null 2>&1
    pip install --quiet --no-cache-dir --upgrade pip
    pip install --quiet --no-cache-dir \
        "ultralytics==8.3.0" \
        "gdown==5.2.0"
    python /work/_download_models.py
  '

echo
echo "==> $MODELS_DIR contents:"
ls -lh "$MODELS_DIR" | tail -n +2
echo
echo "Done. Set YOLO_MODEL_PATH / REID_MODEL_PATH in .env if you switched variants."
