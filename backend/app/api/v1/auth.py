from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import audit_log
from app.database import get_db
from app.models import User
from app.schemas import TokenOut
from app.security import create_access_token, verify_password

router = APIRouter()


class LoginJson(BaseModel):
    username: str  # email
    password: str


@router.post("/login", response_model=TokenOut)
async def login(
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """OAuth2 password flow — username field carries email."""
    r = await db.execute(select(User).where(User.email == form.username))
    user = r.scalar_one_or_none()
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = create_access_token(str(user.id), extra={"role": user.role})
    await audit_log(db, user_id=user.id, action="login", resource_type="user", resource_id=str(user.id))
    await db.commit()
    return TokenOut(access_token=token)


@router.post("/login_json", response_model=TokenOut)
async def login_json(body: LoginJson, db: Annotated[AsyncSession, Depends(get_db)]):
    r = await db.execute(select(User).where(User.email == body.username))
    user = r.scalar_one_or_none()
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = create_access_token(str(user.id), extra={"role": user.role})
    await audit_log(db, user_id=user.id, action="login_json", resource_type="user", resource_id=str(user.id))
    await db.commit()
    return TokenOut(access_token=token)
