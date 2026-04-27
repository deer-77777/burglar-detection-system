from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import FileResponse
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.api.deps import client_ip, current_user, get_db, visible_camera_ids
from app.config import settings
from app.db.models import Event, User
from app.schemas.dto import EventOut, EventPage, EventReviewIn
from app.services.audit import write_audit

router = APIRouter(prefix="/api/events", tags=["events"])


@router.get("", response_model=EventPage)
def list_events(
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
    camera_id: int | None = None,
    event_type: str | None = None,
    review_status: str | None = None,
    has_clip: bool | None = None,
    person_global_id: str | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
    notes_q: str | None = None,
    sort: str = "time_desc",
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
) -> EventPage:
    q = db.query(Event)

    visible = visible_camera_ids(db, user)
    if visible is not None:
        if not visible:
            return EventPage(total=0, items=[])
        q = q.filter(Event.camera_id.in_(visible))

    if camera_id is not None:
        q = q.filter(Event.camera_id == camera_id)
    if event_type:
        q = q.filter(Event.event_type == event_type)
    if review_status:
        q = q.filter(Event.review_status == review_status)
    if has_clip is True:
        q = q.filter(Event.clip_path.isnot(None))
    elif has_clip is False:
        q = q.filter(Event.clip_path.is_(None))
    if person_global_id:
        q = q.filter(Event.person_global_id == person_global_id)
    if start:
        q = q.filter(Event.start_time >= start)
    if end:
        q = q.filter(Event.start_time <= end)
    if notes_q:
        like = f"%{notes_q}%"
        q = q.filter(or_(Event.review_notes.like(like)))

    total = q.count()

    sort_map = {
        "time_desc": Event.start_time.desc(),
        "time_asc": Event.start_time.asc(),
        "camera": Event.camera_id.asc(),
        "reviewer": Event.reviewed_by_user_id.asc(),
    }
    q = q.order_by(sort_map.get(sort, Event.start_time.desc()))
    rows = q.offset((page - 1) * page_size).limit(page_size).all()
    return EventPage(total=total, items=[EventOut.model_validate(r) for r in rows])


@router.patch("/{event_id}", response_model=EventOut)
def update_review(
    event_id: int,
    payload: EventReviewIn,
    request: Request,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> Event:
    e = db.get(Event, event_id)
    if not e:
        raise HTTPException(status.HTTP_404_NOT_FOUND)

    visible = visible_camera_ids(db, user)
    if visible is not None and e.camera_id not in visible:
        raise HTTPException(status.HTTP_403_FORBIDDEN)

    e.review_status = payload.review_status
    if payload.review_notes is not None:
        e.review_notes = payload.review_notes
    e.reviewed_by_user_id = user.id
    db.commit()
    db.refresh(e)
    write_audit(
        db, user_id=user.id, action="event_review", target_type="event", target_id=event_id,
        ip=client_ip(request), detail=payload.model_dump(),
    )
    return e


def _safe_path(base: str, rel: str) -> Path:
    base_p = Path(base).resolve()
    candidate = (base_p / rel).resolve()
    if base_p not in candidate.parents and candidate != base_p:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Bad path")
    return candidate


@router.get("/{event_id}/snapshot")
def get_snapshot(event_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)) -> FileResponse:
    e = db.get(Event, event_id)
    if not e or not e.snapshot_path:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    visible = visible_camera_ids(db, user)
    if visible is not None and e.camera_id not in visible:
        raise HTTPException(status.HTTP_403_FORBIDDEN)
    p = _safe_path(settings.SNAPS_DIR, e.snapshot_path)
    if not p.exists():
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    return FileResponse(p, media_type="image/jpeg")


@router.get("/{event_id}/clip")
def get_clip(event_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)) -> FileResponse:
    e = db.get(Event, event_id)
    if not e or not e.clip_path:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    visible = visible_camera_ids(db, user)
    if visible is not None and e.camera_id not in visible:
        raise HTTPException(status.HTTP_403_FORBIDDEN)
    p = _safe_path(settings.CLIPS_DIR, e.clip_path)
    if not p.exists():
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    return FileResponse(p, media_type="video/mp4")
