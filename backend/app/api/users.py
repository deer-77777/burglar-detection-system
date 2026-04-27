from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import client_ip, current_user, get_db, require_perm
from app.db.models import User, UserVisibility
from app.schemas.dto import UserCreateIn, UserOut, UserUpdateIn, UserVisibilityIn
from app.services.audit import write_audit
from app.services.auth import hash_password

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("", response_model=list[UserOut])
def list_users(_: User = Depends(require_perm("can_manage_users")), db: Session = Depends(get_db)) -> list[User]:
    return db.query(User).order_by(User.id.asc()).all()


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreateIn,
    request: Request,
    actor: User = Depends(require_perm("can_manage_users")),
    db: Session = Depends(get_db),
) -> User:
    if db.query(User).filter(User.username == payload.username).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "Username already exists")
    u = User(
        username=payload.username,
        password_hash=hash_password(payload.password),
        language=payload.language,
        can_manage_users=payload.can_manage_users,
        can_manage_groups=payload.can_manage_groups,
        can_manage_cameras=payload.can_manage_cameras,
        must_change_password=False,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    write_audit(db, user_id=actor.id, action="user_create", target_type="user", target_id=u.id, ip=client_ip(request))
    return u


@router.patch("/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    payload: UserUpdateIn,
    request: Request,
    actor: User = Depends(require_perm("can_manage_users")),
    db: Session = Depends(get_db),
) -> User:
    u = db.get(User, user_id)
    if not u:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    data = payload.model_dump(exclude_unset=True)
    if "password" in data and data["password"]:
        u.password_hash = hash_password(data.pop("password"))
    else:
        data.pop("password", None)
    for k, v in data.items():
        setattr(u, k, v)
    db.commit()
    db.refresh(u)
    write_audit(
        db, user_id=actor.id, action="user_update", target_type="user", target_id=u.id,
        ip=client_ip(request), detail=data,
    )
    return u


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    request: Request,
    actor: User = Depends(require_perm("can_manage_users")),
    db: Session = Depends(get_db),
) -> None:
    if user_id == actor.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cannot delete yourself")
    u = db.get(User, user_id)
    if not u:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    db.delete(u)
    db.commit()
    write_audit(db, user_id=actor.id, action="user_delete", target_type="user", target_id=user_id, ip=client_ip(request))


@router.put("/{user_id}/visibility")
def set_visibility(
    user_id: int,
    payload: UserVisibilityIn,
    request: Request,
    actor: User = Depends(require_perm("can_manage_users")),
    db: Session = Depends(get_db),
) -> dict:
    u = db.get(User, user_id)
    if not u:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    db.query(UserVisibility).filter(UserVisibility.user_id == user_id).delete()
    for gid in payload.group_ids:
        db.add(UserVisibility(user_id=user_id, group_id=gid, camera_id=None))
    for cid in payload.camera_ids:
        db.add(UserVisibility(user_id=user_id, group_id=None, camera_id=cid))
    db.commit()
    write_audit(
        db, user_id=actor.id, action="user_visibility_set", target_type="user", target_id=user_id,
        ip=client_ip(request), detail=payload.model_dump(),
    )
    return {"ok": True}
