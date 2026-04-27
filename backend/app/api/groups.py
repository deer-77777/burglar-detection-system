from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import client_ip, get_db, require_perm
from app.db.models import Group, User
from app.schemas.dto import GroupIn, GroupOut
from app.services.audit import write_audit

router = APIRouter(prefix="/api/groups", tags=["groups"])


def _level_for_parent(db: Session, parent_id: int | None) -> int:
    if parent_id is None:
        return 1
    parent = db.get(Group, parent_id)
    if not parent:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Parent group not found")
    if parent.level >= 3:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Group hierarchy is at most 3 levels deep")
    return parent.level + 1


def _build_path(db: Session, group_id: int | None) -> str:
    parts: list[str] = []
    cur = db.get(Group, group_id) if group_id else None
    while cur:
        parts.append(cur.name)
        cur = db.get(Group, cur.parent_id) if cur.parent_id else None
    return " / ".join(reversed(parts))


@router.get("", response_model=list[GroupOut])
def list_groups(db: Session = Depends(get_db), _: User = Depends(require_perm("can_manage_groups"))) -> list[Group]:
    return db.query(Group).order_by(Group.level.asc(), Group.sort_order.asc(), Group.id.asc()).all()


@router.post("", response_model=GroupOut, status_code=status.HTTP_201_CREATED)
def create_group(
    payload: GroupIn,
    request: Request,
    actor: User = Depends(require_perm("can_manage_groups")),
    db: Session = Depends(get_db),
) -> Group:
    level = _level_for_parent(db, payload.parent_id)
    g = Group(name=payload.name, parent_id=payload.parent_id, level=level, sort_order=payload.sort_order)
    db.add(g)
    db.commit()
    db.refresh(g)
    write_audit(
        db, user_id=actor.id, action="group_create", target_type="group", target_id=g.id,
        ip=client_ip(request), detail=payload.model_dump(),
    )
    return g


@router.patch("/{group_id}", response_model=GroupOut)
def update_group(
    group_id: int,
    payload: GroupIn,
    request: Request,
    actor: User = Depends(require_perm("can_manage_groups")),
    db: Session = Depends(get_db),
) -> Group:
    g = db.get(Group, group_id)
    if not g:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    if payload.parent_id != g.parent_id:
        new_level = _level_for_parent(db, payload.parent_id)
        g.parent_id = payload.parent_id
        g.level = new_level
    g.name = payload.name
    g.sort_order = payload.sort_order
    db.commit()
    db.refresh(g)
    write_audit(
        db, user_id=actor.id, action="group_update", target_type="group", target_id=g.id,
        ip=client_ip(request), detail=payload.model_dump(),
    )
    return g


@router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_group(
    group_id: int,
    request: Request,
    actor: User = Depends(require_perm("can_manage_groups")),
    db: Session = Depends(get_db),
) -> None:
    g = db.get(Group, group_id)
    if not g:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    db.delete(g)
    db.commit()
    write_audit(db, user_id=actor.id, action="group_delete", target_type="group", target_id=group_id, ip=client_ip(request))


@router.get("/{group_id}/path")
def group_path(group_id: int, db: Session = Depends(get_db), _: User = Depends(require_perm("can_manage_groups"))) -> dict:
    return {"path": _build_path(db, group_id)}
