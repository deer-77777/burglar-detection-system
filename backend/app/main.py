"""FastAPI app entrypoint.

* Creates the camera-credentials Fernet key on first run if missing.
* Seeds the default admin user on first run.
* Mounts auth, users, groups, cameras, events, and websocket routers.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

import structlog
from cryptography.fernet import Fernet
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api import auth as auth_router
from app.api import cameras as cameras_router
from app.api import events as events_router
from app.api import groups as groups_router
from app.api import users as users_router
from app.api import ws as ws_router
from app.config import settings
from app.db.models import User
from app.db.session import SessionLocal, engine
from app.services.auth import hash_password


def _configure_logging() -> None:
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        logger_factory=structlog.PrintLoggerFactory(),
    )


def _ensure_cred_key() -> None:
    p = Path(settings.CAMERA_CRED_KEY_FILE)
    if p.exists() and p.read_bytes().strip():
        return
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(Fernet.generate_key())
    p.chmod(0o600)


def _wait_for_db_and_seed() -> None:
    with engine.begin() as conn:
        conn.execute(text("SELECT 1"))
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.username == "admin").first()
        if admin:
            return
        db.add(
            User(
                username="admin",
                password_hash=hash_password("admin"),
                must_change_password=True,
                can_manage_users=True,
                can_manage_groups=True,
                can_manage_cameras=True,
            )
        )
        db.commit()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    _configure_logging()
    Path(settings.CLIPS_DIR).mkdir(parents=True, exist_ok=True)
    Path(settings.SNAPS_DIR).mkdir(parents=True, exist_ok=True)
    try:
        _ensure_cred_key()
    except PermissionError:
        # In production, the key file is mounted read-only — operator must provide one.
        pass
    _wait_for_db_and_seed()
    yield


app = FastAPI(title="Burglar Detection Support System", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.PUBLIC_ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router)
app.include_router(users_router.router)
app.include_router(groups_router.router)
app.include_router(cameras_router.router)
app.include_router(events_router.router)
app.include_router(ws_router.router)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}
