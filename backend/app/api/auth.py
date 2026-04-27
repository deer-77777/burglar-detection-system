from datetime import datetime, timedelta

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from jose import JWTError
from sqlalchemy.orm import Session

from app.api.deps import client_ip, current_user, get_db
from app.config import settings
from app.db.models import User
from app.schemas.dto import ChangePasswordIn, LoginIn, TokenPair
from app.services.audit import write_audit
from app.services.auth import decode_token, hash_password, make_access_token, make_refresh_token, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _set_cookies(response: Response, access: str, refresh: str) -> None:
    secure = settings.APP_ENV == "production"
    response.set_cookie(
        "access_token", access, httponly=True, secure=secure, samesite="lax",
        max_age=settings.JWT_ACCESS_TTL_MIN * 60, path="/",
    )
    response.set_cookie(
        "refresh_token", refresh, httponly=True, secure=secure, samesite="lax",
        max_age=settings.JWT_REFRESH_TTL_DAYS * 86400, path="/api/auth",
    )


@router.post("/login", response_model=TokenPair)
def login(payload: LoginIn, request: Request, response: Response, db: Session = Depends(get_db)) -> TokenPair:
    user = db.query(User).filter(User.username == payload.username).first()
    now = datetime.utcnow()

    if user and user.locked_until and user.locked_until > now:
        raise HTTPException(status.HTTP_423_LOCKED, "Account temporarily locked")

    if not user or not verify_password(payload.password, user.password_hash):
        if user:
            window = settings.LOGIN_LOCK_WINDOW_SEC
            if not user.failed_login_window_start or (now - user.failed_login_window_start).total_seconds() > window:
                user.failed_login_window_start = now
                user.failed_login_count = 1
            else:
                user.failed_login_count += 1
            if user.failed_login_count >= settings.LOGIN_LOCK_THRESHOLD:
                user.locked_until = now + timedelta(seconds=settings.LOGIN_LOCK_DURATION_SEC)
                user.failed_login_count = 0
                user.failed_login_window_start = None
            db.commit()
        write_audit(
            db, user_id=user.id if user else None, action="login_failed",
            ip=client_ip(request), detail={"username": payload.username},
        )
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")

    user.failed_login_count = 0
    user.failed_login_window_start = None
    user.locked_until = None
    user.last_login_at = now
    db.commit()

    access = make_access_token(user.id)
    refresh = make_refresh_token(user.id)
    _set_cookies(response, access, refresh)

    write_audit(db, user_id=user.id, action="login_ok", ip=client_ip(request))
    return TokenPair(access_token=access, refresh_token=refresh, must_change_password=user.must_change_password)


@router.post("/refresh", response_model=TokenPair)
def refresh_token(
    response: Response,
    refresh_token: str | None = Cookie(default=None),
    db: Session = Depends(get_db),
) -> TokenPair:
    if not refresh_token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing refresh token")
    try:
        payload = decode_token(refresh_token)
        if payload.get("type") != "refresh":
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Wrong token type")
        user_id = int(payload["sub"])
    except (JWTError, KeyError, ValueError):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token")

    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found")

    access = make_access_token(user.id)
    refresh = make_refresh_token(user.id)
    _set_cookies(response, access, refresh)
    return TokenPair(access_token=access, refresh_token=refresh, must_change_password=user.must_change_password)


@router.post("/logout")
def logout(response: Response) -> dict:
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/api/auth")
    return {"ok": True}


@router.post("/change-password")
def change_password(
    payload: ChangePasswordIn,
    request: Request,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Current password is incorrect")
    if payload.current_password == payload.new_password:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "New password must differ from the old one")
    user.password_hash = hash_password(payload.new_password)
    user.must_change_password = False
    db.commit()
    write_audit(db, user_id=user.id, action="password_changed", ip=client_ip(request))
    return {"ok": True}


@router.get("/me")
def me(user: User = Depends(current_user)) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "language": user.language,
        "must_change_password": user.must_change_password,
        "permissions": {
            "manage_users": user.can_manage_users,
            "manage_groups": user.can_manage_groups,
            "manage_cameras": user.can_manage_cameras,
        },
    }
