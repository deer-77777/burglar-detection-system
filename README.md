# Burglar Detection Support System

Implementation of the spec in `Burglar_Detection_System_Spec.docx` (v1.0,
2026-04-26). Decision-support for in-store loss-prevention staff: continuously
analyzes IP-camera footage, raises Dwell and Revisit events, and surfaces them
on a single dashboard. Runs entirely on the in-store LAN.

## Layout

```
backend/    FastAPI app (auth, CRUD, history, WS hub).
workers/    Per-camera detection workers (YOLO11 + ByteTrack + OSNet ReID),
            ring-buffer clip dump, MPEG-TS stream server.
frontend/   React 18 + Vite + Tailwind UI (EN/JA).
deploy/     Nginx (TLS, static + proxy) and the nightly mysqldump container.
scripts/    Offline USB bundle build + install scripts.
```

## Architecture (matches §6.1 of the spec)

```
Cameras (RTSP) ─▶ workers ─▶ Redis (events:new) ─▶ api ─▶ MySQL
                          │                              │
                          └─▶ MPEG-TS HTTP ◀─ api ◀─▶ browser (nginx)
```

* Workers process one camera per asyncio task. Detection + tracking + ReID
  share a single GPU. Dwell/Revisit events go to MySQL and the
  `events:new` Redis pub-sub.
* The API `/ws/dashboard` filters and forwards events; `/ws/stream/{id}`
  proxies the worker's MPEG-TS byte stream to the browser.
* Nginx terminates TLS and serves the SPA; everything else is internal.

## Working assumptions on §7 open questions

These are the answers I've baked in. Override with `.env` / per-camera fields
when the stakeholder weighs in.

| # | Question | Assumption |
|---|----------|------------|
| 1 | NVR vendor | Deferred. No adapter implemented; events still record their own 10 s pre/post clips. |
| 2 | Default revisit window | 24 h (`DEFAULT_COUNT_WINDOW_SEC=86400`). |
| 3 | Person-Global-ID lifetime | 24 h of inactivity (`PERSON_GID_TTL_SEC=86400`). |
| 4 | Max cameras per server | 8 (`WORKER_MAX_CAMERAS=8`), matching the §5.2 GPU sizing. |
| 5 | Cross-camera revisits | Out of scope for v1. ReID gallery is keyed per Store, but Revisit thresholds count per single camera. |
| 6 | Languages | EN + JA only. |
| 7 | Backup destination | Local disk only (`BACKUP_DIR`); NAS mount path can be substituted via `.env`. |

## Run locally (dev)

Requires Docker, the NVIDIA container toolkit (for the workers container), and
~16 GB disk for images.

```bash
cp .env.example .env
mkdir -p secrets
python3 -c "from cryptography.fernet import Fernet; open('secrets/camera_cred.key','wb').write(Fernet.generate_key())"
chmod 600 secrets/camera_cred.key

# Download model weights (one-shot, runs in a throwaway container):
./scripts/download-models.sh
# → populates workers/models/ with yolo11n/s/m.pt and osnet_x0_25/0_5/1_0.pth.

# Build the SPA:
( cd frontend && npm install && npm run build )

docker compose up -d
```

Then browse https://localhost/ and log in as `admin / admin` — you'll be forced
to change the password.

### CPU-only / no-GPU dev run

To exercise the UI (login, users, groups, the camera form, history) on a
machine without an NVIDIA GPU:

* `workers` is behind the `gpu` compose profile, so `docker compose up -d`
  brings up only `mysql`, `redis`, `api`, `nginx`, and `backup`. Add
  `--profile gpu` later when you have a GPU.
* Set `DEV_SKIP_RTSP_PROBE=true` in `.env` so `/api/cameras/test` returns a
  synthetic success and camera create/update skip the probe. Lets you see and
  save the Add Camera form without a real RTSP source. Live MPEG-TS playback on
  the dashboard will still be blank because `workers` produces the stream.

## Build the offline USB bundle

On a build machine with internet access:

```bash
./scripts/build-bundle.sh
# → bundle/burglar-bundle-YYYYMMDD.tar.gz
```

On the in-store server (no internet):

```bash
tar -xzf burglar-bundle-YYYYMMDD.tar.gz
cd stage
./install.sh           # first run: copies .env.example → .env, asks you to edit
$EDITOR .env           # set MYSQL_*, PUBLIC_ORIGIN, BACKUP_DIR, etc.
./install.sh           # second run: brings up docker compose
```

## What's intentionally not done

* **Tests.** No test suite is included. The structure supports one — `pytest`
  for the API, fixture-driven `worker.state` tests, and Playwright for the SPA
  — but writing it is a separate milestone.
* **NVR adapter.** Stub only. When a vendor is selected, add an adapter under
  `backend/app/services/nvr/` and link it from the History detail view.
* **Prometheus / Grafana / Loki.** Spec calls for them as off-by-default. Not
  bundled here; add to `docker-compose.yml` once you decide what to scrape.
* **Hot-reloading model weights.** Worker reads weights at process start; bump
  the worker container to roll out new weights.
* **Cross-camera revisit events.** See §7 #5 — keyed off per Store; flip to
  cross-camera by counting appearances across all cameras with the same Store
  ancestor, in `worker.state`.

## Repo notes

* MySQL schema lives in `backend/app/migrations/001_schema.sql` and is mounted
  into MySQL's `docker-entrypoint-initdb.d` for first-run init. The default
  admin user is seeded by the API on first start (so we can use a real bcrypt
  hash rather than a precomputed one).
* Camera RTSP URLs are encrypted at rest with Fernet; the key file
  (`secrets/camera_cred.key`) is generated once and must be backed up.
* All write operations are logged to `audit_log`. Failed-login throttling is
  the spec's 5-in-5min → 15-min lock.
