from datetime import datetime

from sqlalchemy import (
    BigInteger, Boolean, CheckConstraint, DateTime, Enum, ForeignKey, Integer,
    LargeBinary, String, Text, UniqueConstraint, JSON,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True)
    password_hash: Mapped[str] = mapped_column(String(120))
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=False)
    language: Mapped[str] = mapped_column(String(8), default="en")
    can_manage_users: Mapped[bool] = mapped_column(Boolean, default=False)
    can_manage_groups: Mapped[bool] = mapped_column(Boolean, default=False)
    can_manage_cameras: Mapped[bool] = mapped_column(Boolean, default=False)
    failed_login_count: Mapped[int] = mapped_column(Integer, default=0)
    failed_login_window_start: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Group(Base):
    __tablename__ = "groups"
    __table_args__ = (CheckConstraint("level BETWEEN 1 AND 3", name="chk_groups_level"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    parent_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("groups.id", ondelete="CASCADE"), nullable=True)
    name: Mapped[str] = mapped_column(String(128))
    level: Mapped[int] = mapped_column(Integer)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    parent = relationship("Group", remote_side="Group.id")


class Camera(Base):
    __tablename__ = "cameras"
    __table_args__ = (UniqueConstraint("name", "group_id", name="uq_cameras_name_group"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), default="Camera")
    rtsp_url_enc: Mapped[bytes] = mapped_column(LargeBinary(2048))
    resolution_w: Mapped[int] = mapped_column(Integer, default=1920)
    resolution_h: Mapped[int] = mapped_column(Integer, default=1080)
    group_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("groups.id", ondelete="SET NULL"), nullable=True)
    display_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    dwell_limit_sec: Mapped[int] = mapped_column(Integer, default=180)
    count_limit: Mapped[int] = mapped_column(Integer, default=3)
    count_window_sec: Mapped[int] = mapped_column(Integer, default=86400)
    status: Mapped[str] = mapped_column(String(32), default="pending")
    last_status_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CameraConnectionLog(Base):
    __tablename__ = "camera_connection_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    camera_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("cameras.id", ondelete="CASCADE"), nullable=True)
    attempt_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    success: Mapped[bool] = mapped_column(Boolean)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)


class UserVisibility(Base):
    __tablename__ = "user_visibility"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    group_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("groups.id", ondelete="CASCADE"), nullable=True)
    camera_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("cameras.id", ondelete="CASCADE"), nullable=True)


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    camera_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("cameras.id", ondelete="CASCADE"))
    group_path: Mapped[str] = mapped_column(String(255), default="")
    person_global_id: Mapped[str] = mapped_column(String(64))
    event_type: Mapped[str] = mapped_column(Enum("DWELL", "REVISIT", name="event_type_enum"))
    start_time: Mapped[datetime] = mapped_column(DateTime)
    end_time: Mapped[datetime] = mapped_column(DateTime)
    duration_sec: Mapped[int | None] = mapped_column(Integer, nullable=True)
    appearance_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    snapshot_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    clip_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reviewed_by_user_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    review_status: Mapped[str] = mapped_column(
        Enum("NEW", "REVIEWED", "FALSE_POSITIVE", "ESCALATED", name="review_status_enum"),
        default="NEW",
    )
    review_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class PersonEmbedding(Base):
    __tablename__ = "person_embeddings"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    store_group_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("groups.id", ondelete="CASCADE"), nullable=True)
    person_global_id: Mapped[str] = mapped_column(String(64))
    embedding: Mapped[bytes] = mapped_column(LargeBinary)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime)


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action: Mapped[str] = mapped_column(String(64))
    target_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    target_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    detail: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
