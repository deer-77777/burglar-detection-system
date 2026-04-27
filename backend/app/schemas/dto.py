from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class _Base(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class LoginIn(BaseModel):
    username: str
    password: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    must_change_password: bool = False


class ChangePasswordIn(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)


class UserOut(_Base):
    id: int
    username: str
    language: str
    can_manage_users: bool
    can_manage_groups: bool
    can_manage_cameras: bool
    must_change_password: bool
    last_login_at: datetime | None = None


class UserCreateIn(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=8, max_length=128)
    language: str = "en"
    can_manage_users: bool = False
    can_manage_groups: bool = False
    can_manage_cameras: bool = False


class UserUpdateIn(BaseModel):
    password: str | None = Field(default=None, min_length=8, max_length=128)
    language: str | None = None
    can_manage_users: bool | None = None
    can_manage_groups: bool | None = None
    can_manage_cameras: bool | None = None


class UserVisibilityIn(BaseModel):
    group_ids: list[int] = []
    camera_ids: list[int] = []


class GroupIn(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    parent_id: int | None = None
    sort_order: int = 0


class GroupOut(_Base):
    id: int
    parent_id: int | None
    name: str
    level: int
    sort_order: int


class CameraIn(BaseModel):
    name: str = Field("Camera", min_length=1, max_length=128)
    rtsp_url: str = Field(min_length=7, max_length=2048, pattern=r"^rtsps?://")
    resolution_w: int = Field(1920, ge=16, le=7680)
    resolution_h: int = Field(1080, ge=16, le=7680)
    group_id: int | None = None
    display_enabled: bool = True
    dwell_limit_sec: int | None = Field(default=None, ge=1, le=86400)
    count_limit: int | None = Field(default=None, ge=1, le=10000)
    count_window_sec: int | None = Field(default=None, ge=1, le=7 * 86400)


class CameraUpdateIn(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    rtsp_url: str | None = Field(default=None, min_length=7, max_length=2048, pattern=r"^rtsps?://")
    resolution_w: int | None = Field(default=None, ge=16, le=7680)
    resolution_h: int | None = Field(default=None, ge=16, le=7680)
    group_id: int | None = None
    display_enabled: bool | None = None
    dwell_limit_sec: int | None = Field(default=None, ge=1, le=86400)
    count_limit: int | None = Field(default=None, ge=1, le=10000)
    count_window_sec: int | None = Field(default=None, ge=1, le=7 * 86400)


class CameraOut(_Base):
    id: int
    name: str
    resolution_w: int
    resolution_h: int
    group_id: int | None
    display_enabled: bool
    dwell_limit_sec: int
    count_limit: int
    count_window_sec: int
    status: str
    last_status_at: datetime | None = None


class CameraTestIn(BaseModel):
    rtsp_url: str
    onvif_user: str | None = None
    onvif_password: str | None = None
    onvif_port: int = 80


class CameraTestOut(BaseModel):
    success: bool
    error_code: str | None = None
    error_detail: str | None = None
    width: int | None = None
    height: int | None = None
    onvif_resolutions: list[tuple[int, int]] | None = None


class EventOut(_Base):
    id: int
    camera_id: int
    group_path: str
    person_global_id: str
    event_type: Literal["DWELL", "REVISIT"]
    start_time: datetime
    end_time: datetime
    duration_sec: int | None
    appearance_count: int | None
    snapshot_path: str | None
    clip_path: str | None
    review_status: Literal["NEW", "REVIEWED", "FALSE_POSITIVE", "ESCALATED"]
    review_notes: str | None
    reviewed_by_user_id: int | None


class EventReviewIn(BaseModel):
    review_status: Literal["NEW", "REVIEWED", "FALSE_POSITIVE", "ESCALATED"]
    review_notes: str | None = None


class Page(BaseModel):
    total: int
    items: list


class EventPage(Page):
    items: list[EventOut]
