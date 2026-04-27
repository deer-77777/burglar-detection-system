from sqlalchemy import (
    BigInteger, Boolean, DateTime, Enum, ForeignKey, Integer, LargeBinary, String, Text, create_engine,
)
from sqlalchemy.orm import Mapped, declarative_base, mapped_column, sessionmaker
from datetime import datetime

from worker.config import settings

engine = create_engine(settings.db_url, pool_pre_ping=True, pool_recycle=1800, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
Base = declarative_base()


class Camera(Base):
    __tablename__ = "cameras"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    rtsp_url_enc: Mapped[bytes] = mapped_column(LargeBinary(2048))
    resolution_w: Mapped[int] = mapped_column(Integer)
    resolution_h: Mapped[int] = mapped_column(Integer)
    group_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("groups.id"), nullable=True)
    display_enabled: Mapped[bool] = mapped_column(Boolean)
    dwell_limit_sec: Mapped[int] = mapped_column(Integer)
    count_limit: Mapped[int] = mapped_column(Integer)
    count_window_sec: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(32))
    last_status_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Group(Base):
    __tablename__ = "groups"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    parent_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("groups.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(128))
    level: Mapped[int] = mapped_column(Integer)


class Event(Base):
    __tablename__ = "events"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    camera_id: Mapped[int] = mapped_column(BigInteger)
    group_path: Mapped[str] = mapped_column(String(255))
    person_global_id: Mapped[str] = mapped_column(String(64))
    event_type: Mapped[str] = mapped_column(Enum("DWELL", "REVISIT"))
    start_time: Mapped[datetime] = mapped_column(DateTime)
    end_time: Mapped[datetime] = mapped_column(DateTime)
    duration_sec: Mapped[int | None] = mapped_column(Integer, nullable=True)
    appearance_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    snapshot_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    clip_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    review_status: Mapped[str] = mapped_column(Enum("NEW", "REVIEWED", "FALSE_POSITIVE", "ESCALATED"), default="NEW")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class CameraConnectionLog(Base):
    __tablename__ = "camera_connection_log"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    camera_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("cameras.id"), nullable=True)
    attempt_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    success: Mapped[bool] = mapped_column(Boolean)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)


def store_group_id_for(session, group_id: int | None) -> int | None:
    """Walk up the group tree until we hit level=1 (Store)."""
    if group_id is None:
        return None
    cur = session.get(Group, group_id)
    while cur is not None and cur.level > 1:
        if cur.parent_id is None:
            break
        cur = session.get(Group, cur.parent_id)
    return cur.id if cur is not None else None


def group_path(session, group_id: int | None) -> str:
    parts = []
    cur = session.get(Group, group_id) if group_id else None
    while cur:
        parts.append(cur.name)
        cur = session.get(Group, cur.parent_id) if cur.parent_id else None
    return " / ".join(reversed(parts))
