#!/usr/bin/env bash
# Builds the offline USB bundle on a connected build machine.
#
# Outputs a single ./bundle/burglar-bundle-<date>.tar.gz containing:
#   * docker-compose.yml, .env.example, deploy/, backend/migrations/
#   * vendored Python wheels (backend + workers)
#   * vendored npm packages (frontend offline cache)
#   * pre-built frontend dist
#   * docker images (api, workers, mysql, redis, nginx, backup) saved with `docker save`
#   * model weights (yolo11n.pt, osnet_x0_25.pth)
#
# At the store, see scripts/install-bundle.sh.

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DATE="$(date -u +%Y%m%d)"
OUT="$ROOT/bundle"
STAGE="$OUT/stage"

rm -rf "$STAGE"
mkdir -p "$STAGE/wheels/backend" "$STAGE/wheels/workers" "$STAGE/images" "$STAGE/models" "$STAGE/frontend"

echo "==> vendoring Python wheels"
pip download -r "$ROOT/backend/requirements.txt" -d "$STAGE/wheels/backend"
pip download -r "$ROOT/workers/requirements.txt" -d "$STAGE/wheels/workers"

echo "==> downloading model weights (skipped if already present)"
"$ROOT/scripts/download-models.sh"
cp -a "$ROOT/workers/models/." "$STAGE/models/"

echo "==> building frontend"
( cd "$ROOT/frontend" && npm install --no-audit --no-fund && npm run build )
cp -a "$ROOT/frontend/dist" "$STAGE/frontend/dist"

echo "==> building docker images"
( cd "$ROOT" && docker compose build )
echo "==> saving docker images"
docker save \
  $(docker compose -f "$ROOT/docker-compose.yml" config | awk '/image:/ {print $2}' | sort -u) \
  | gzip -c > "$STAGE/images/images.tar.gz"

echo "==> packaging support files"
cp -a "$ROOT/docker-compose.yml" "$ROOT/.env.example" "$ROOT/deploy" "$ROOT/backend/app/migrations" "$STAGE/"
cp -a "$ROOT/scripts/install-bundle.sh" "$STAGE/install.sh"
chmod +x "$STAGE/install.sh"

TAR="$OUT/burglar-bundle-$DATE.tar.gz"
( cd "$STAGE/.." && tar -czf "$TAR" stage )
echo "==> wrote $TAR"
