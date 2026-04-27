#!/usr/bin/env bash
# Run on the in-store server with the unpacked bundle.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"

echo "==> loading docker images"
gunzip -c "$HERE/images/images.tar.gz" | docker load

echo "==> placing model weights"
mkdir -p "$HERE/workers/models"
cp -n "$HERE/models/"*.pt  "$HERE/workers/models/" 2>/dev/null || true
cp -n "$HERE/models/"*.pth "$HERE/workers/models/" 2>/dev/null || true

echo "==> placing frontend"
mkdir -p "$HERE/frontend"
cp -a "$HERE/frontend/dist" "$HERE/frontend/" 2>/dev/null || true

if [[ ! -f "$HERE/.env" ]]; then
  cp "$HERE/.env.example" "$HERE/.env"
  echo "Edit $HERE/.env with site-specific values, then re-run this script."
  exit 0
fi

echo "==> generating camera credential key if missing"
mkdir -p "$HERE/secrets"
if [[ ! -s "$HERE/secrets/camera_cred.key" ]]; then
  python3 - <<'PY'
from cryptography.fernet import Fernet
import sys, pathlib
pathlib.Path("secrets/camera_cred.key").write_bytes(Fernet.generate_key())
PY
  chmod 600 "$HERE/secrets/camera_cred.key"
fi

echo "==> docker compose up"
( cd "$HERE" && docker compose up -d )
echo "Done. Visit https://<host>/ and log in as admin/admin (you'll be prompted to change the password)."
