from datetime import datetime

import redis
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import client_ip, current_user, get_db, require_perm, visible_camera_ids
from app.config import settings
from app.db.models import Camera, CameraConnectionLog, User
from app.schemas.dto import CameraIn, CameraOut, CameraTestIn, CameraTestOut, CameraUpdateIn
from app.services.audit import write_audit
from app.services.crypto import decrypt_str, encrypt_str
from app.services.rtsp_probe import onvif_discover, probe_rtsp, split_rtsp

router = APIRouter(prefix="/api/cameras", tags=["cameras"])

_redis = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, decode_responses=True)


def _publish_camera_change(camera_id: int, kind: str) -> None:
    try:
        _redis.publish("cameras:changed", f"{kind}:{camera_id}")
    except Exception:
        pass  # workers will pick up on next poll


def _log_attempt(db: Session, camera_id: int | None, success: bool, error_code: str | None, detail: str | None) -> None:
    db.add(CameraConnectionLog(camera_id=camera_id, success=success, error_code=error_code, error_detail=detail))
    db.commit()


@router.get("", response_model=list[CameraOut])
def list_cameras(user: User = Depends(current_user), db: Session = Depends(get_db)) -> list[Camera]:
    q = db.query(Camera).order_by(Camera.id.asc())
    visible = visible_camera_ids(db, user)
    if visible is not None:
        q = q.filter(Camera.id.in_(visible) if visible else Camera.id.in_([0]))
    return q.all()


@router.post("/test", response_model=CameraTestOut)
async def test_camera(payload: CameraTestIn, _: User = Depends(require_perm("can_manage_cameras"))) -> CameraTestOut:
    if settings.DEV_SKIP_RTSP_PROBE:
        return CameraTestOut(success=True, width=1920, height=1080, error_detail="probe skipped (DEV_SKIP_RTSP_PROBE)")
    res = await probe_rtsp(payload.rtsp_url)
    onvif_resolutions: list[tuple[int, int]] | None = None
    if payload.onvif_user is not None and payload.onvif_password is not None:
        host, _port, _u, _p = split_rtsp(payload.rtsp_url)
        if host:
            onvif_resolutions = await onvif_discover(host, payload.onvif_port, payload.onvif_user, payload.onvif_password)
    return CameraTestOut(
        success=res.success,
        error_code=res.error_code,
        error_detail=res.error_detail,
        width=res.width,
        height=res.height,
        onvif_resolutions=onvif_resolutions,
    )


@router.post("", response_model=CameraOut, status_code=status.HTTP_201_CREATED)
async def create_camera(
    payload: CameraIn,
    request: Request,
    actor: User = Depends(require_perm("can_manage_cameras")),
    db: Session = Depends(get_db),
) -> Camera:
    if not settings.DEV_SKIP_RTSP_PROBE:
        probe = await probe_rtsp(payload.rtsp_url)
        if not probe.success:
            _log_attempt(db, None, False, probe.error_code, probe.error_detail)
            raise HTTPException(status.HTTP_400_BAD_REQUEST, probe.error_code or "ERR_UNKNOWN")

        if probe.width and probe.height and (
            probe.width != payload.resolution_w or probe.height != payload.resolution_h
        ):
            _log_attempt(db, None, False, "ERR_RESOLUTION_MISMATCH",
                         f"camera reports {probe.width}x{probe.height}, configured {payload.resolution_w}x{payload.resolution_h}")
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "ERR_RESOLUTION_MISMATCH")

    cam = Camera(
        name=payload.name,
        rtsp_url_enc=encrypt_str(payload.rtsp_url),
        resolution_w=payload.resolution_w,
        resolution_h=payload.resolution_h,
        group_id=payload.group_id,
        display_enabled=payload.display_enabled,
        dwell_limit_sec=payload.dwell_limit_sec or settings.DEFAULT_DWELL_LIMIT_SEC,
        count_limit=payload.count_limit or settings.DEFAULT_COUNT_LIMIT,
        count_window_sec=payload.count_window_sec or settings.DEFAULT_COUNT_WINDOW_SEC,
        status="pending",
        last_status_at=datetime.utcnow(),
    )
    db.add(cam)
    db.commit()
    db.refresh(cam)
    _log_attempt(db, cam.id, True, None, None)
    _publish_camera_change(cam.id, "created")
    write_audit(
        db, user_id=actor.id, action="camera_create", target_type="camera", target_id=cam.id,
        ip=client_ip(request), detail={"name": cam.name, "group_id": cam.group_id},
    )
    return cam


@router.patch("/{camera_id}", response_model=CameraOut)
async def update_camera(
    camera_id: int,
    payload: CameraUpdateIn,
    request: Request,
    actor: User = Depends(require_perm("can_manage_cameras")),
    db: Session = Depends(get_db),
) -> Camera:
    cam = db.get(Camera, camera_id)
    if not cam:
        raise HTTPException(status.HTTP_404_NOT_FOUND)

    data = payload.model_dump(exclude_unset=True)
    if "rtsp_url" in data:
        new_url = data.pop("rtsp_url")
        if not settings.DEV_SKIP_RTSP_PROBE:
            probe = await probe_rtsp(new_url)
            if not probe.success:
                _log_attempt(db, camera_id, False, probe.error_code, probe.error_detail)
                raise HTTPException(status.HTTP_400_BAD_REQUEST, probe.error_code or "ERR_UNKNOWN")
        cam.rtsp_url_enc = encrypt_str(new_url)
    for k, v in data.items():
        setattr(cam, k, v)
    db.commit()
    db.refresh(cam)
    _publish_camera_change(cam.id, "updated")
    write_audit(
        db, user_id=actor.id, action="camera_update", target_type="camera", target_id=cam.id,
        ip=client_ip(request), detail={k: v for k, v in data.items() if k != "rtsp_url"},
    )
    return cam


@router.delete("/{camera_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_camera(
    camera_id: int,
    request: Request,
    actor: User = Depends(require_perm("can_manage_cameras")),
    db: Session = Depends(get_db),
) -> None:
    cam = db.get(Camera, camera_id)
    if not cam:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    db.delete(cam)
    db.commit()
    _publish_camera_change(camera_id, "deleted")
    write_audit(db, user_id=actor.id, action="camera_delete", target_type="camera", target_id=camera_id, ip=client_ip(request))


@router.get("/{camera_id}/connection-log")
def connection_log(
    camera_id: int,
    limit: int = 50,
    _: User = Depends(require_perm("can_manage_cameras")),
    db: Session = Depends(get_db),
) -> list[dict]:
    rows = (
        db.query(CameraConnectionLog)
        .filter(CameraConnectionLog.camera_id == camera_id)
        .order_by(CameraConnectionLog.attempt_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": r.id,
            "attempt_at": r.attempt_at,
            "success": r.success,
            "error_code": r.error_code,
            "error_detail": r.error_detail,
        }
        for r in rows
    ]


@router.get("/{camera_id}/rtsp-url-decoded")
def reveal_rtsp_url(
    camera_id: int,
    _: User = Depends(require_perm("can_manage_cameras")),
    db: Session = Depends(get_db),
) -> dict:
    """Returns the decrypted RTSP URL — used by the worker over the internal network only."""
    cam = db.get(Camera, camera_id)
    if not cam:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    return {"rtsp_url": decrypt_str(cam.rtsp_url_enc)}
