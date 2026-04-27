from typing import Iterator

from fastapi import Cookie, Depends, Header, HTTPException, Request, status
from jose import JWTError
from sqlalchemy.orm import Session

from app.db.models import User, UserVisibility
from app.db.session import SessionLocal
from app.services.auth import decode_token


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _extract_token(authorization: str | None, access_token_cookie: str | None) -> str | None:
    if authorization and authorization.lower().startswith("bearer "):
        return authorization.split(" ", 1)[1].strip()
    return access_token_cookie


# Endpoints a user with must_change_password=True is still allowed to call.
# Everything else returns 409 until they pick a new password.
_PASSWORD_CHANGE_ALLOWED = frozenset({
    "/api/auth/me",
    "/api/auth/change-password",
    "/api/auth/logout",
    "/api/auth/refresh",
    "/api/health",
})


def current_user(
    request: Request,
    db: Session = Depends(get_db),
    authorization: str | None = Header(default=None),
    access_token: str | None = Cookie(default=None),
) -> User:
    token = _extract_token(authorization, access_token)
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Wrong token type")
        user_id = int(payload["sub"])
    except (JWTError, KeyError, ValueError):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token")

    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found")

    if user.must_change_password and request.url.path not in _PASSWORD_CHANGE_ALLOWED:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Password change required before using the API",
        )
    return user


def require_perm(attr: str):
    def _dep(user: User = Depends(current_user)) -> User:
        if not getattr(user, attr, False):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Permission denied")
        return user

    return _dep


def visible_camera_ids(db: Session, user: User) -> set[int] | None:
    """Returns the set of camera IDs the user can see, or None for unrestricted (admin)."""
    if user.can_manage_cameras and user.can_manage_groups and user.can_manage_users:
        return None  # admin: unrestricted
    rows = db.query(UserVisibility).filter(UserVisibility.user_id == user.id).all()
    cam_ids: set[int] = set()
    group_ids: set[int] = set()
    for r in rows:
        if r.camera_id:
            cam_ids.add(r.camera_id)
        if r.group_id:
            group_ids.add(r.group_id)
    if group_ids:
        from app.db.models import Camera, Group  # local import to avoid cycle

        sub = db.query(Group.id).filter(Group.id.in_(_descendants(db, group_ids))).all()
        descendant_ids = {row[0] for row in sub}
        cam_rows = db.query(Camera.id).filter(Camera.group_id.in_(descendant_ids)).all()
        cam_ids.update(row[0] for row in cam_rows)
    return cam_ids


def _descendants(db: Session, root_ids: set[int]) -> set[int]:
    from app.db.models import Group

    out = set(root_ids)
    frontier = set(root_ids)
    while frontier:
        rows = db.query(Group.id).filter(Group.parent_id.in_(frontier)).all()
        children = {r[0] for r in rows} - out
        if not children:
            break
        out.update(children)
        frontier = children
    return out


def client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"
