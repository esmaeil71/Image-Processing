import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import audit_log
from app.database import get_db
from app.deps import get_current_user, require_role
from app.models import User
from app.schemas import UserCreate, UserOut
from app.security import get_password_hash

router = APIRouter()


@router.post("/", response_model=UserOut)
async def create_user(
    body: UserCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[User, Depends(require_role("admin"))],
):
    exists = await db.execute(select(User).where(User.email == body.email))
    if exists.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")
    if body.role not in ("admin", "reviewer", "viewer"):
        raise HTTPException(status_code=400, detail="Invalid role")
    u = User(
        email=body.email,
        hashed_password=get_password_hash(body.password),
        full_name=body.full_name,
        role=body.role,
    )
    db.add(u)
    await audit_log(
        db,
        user_id=admin.id,
        action="user_create",
        resource_type="user",
        resource_id=str(u.id),
        detail_safe={"email_domain": body.email.split("@")[-1] if "@" in body.email else "unknown"},
    )
    await db.commit()
    await db.refresh(u)
    return u


@router.get("/me", response_model=UserOut)
async def me(user: Annotated[User, Depends(get_current_user)]):
    return user


@router.get("/{user_id}", response_model=UserOut)
async def get_user(
    user_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(require_role("admin"))],
):
    r = await db.execute(select(User).where(User.id == user_id))
    u = r.scalar_one_or_none()
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    return u
