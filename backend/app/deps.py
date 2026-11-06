import uuid
from typing import Annotated, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Study, StudyAccess, User
from app.security import decode_token

bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    cred: Annotated[Optional[HTTPAuthorizationCredentials], Depends(bearer)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    if cred is None or cred.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        payload = decode_token(cred.credentials)
        sub = payload.get("sub")
        if not sub:
            raise HTTPException(status_code=401, detail="Invalid token")
        uid = uuid.UUID(str(sub))
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")
    result = await db.execute(select(User).where(User.id == uid))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Inactive user")
    return user


def require_role(*roles: str):
    async def _dep(user: Annotated[User, Depends(get_current_user)]) -> User:
        if user.role not in roles and user.role != "admin":
            raise HTTPException(status_code=403, detail="Forbidden")
        return user

    return _dep


async def assert_study_access(
    db: AsyncSession,
    user: User,
    study_id: uuid.UUID,
    *,
    need_phi: bool = False,
) -> Study:
    q = await db.execute(select(Study).where(Study.id == study_id, Study.deleted_at.is_(None)))
    study = q.scalar_one_or_none()
    if not study:
        raise HTTPException(status_code=404, detail="Study not found")

    if user.role == "admin":
        return study

    if study.owner_id == user.id:
        return study

    shared = await db.execute(
        select(StudyAccess).where(StudyAccess.study_id == study_id, StudyAccess.user_id == user.id)
    )
    sa = shared.scalar_one_or_none()
    if not sa:
        raise HTTPException(status_code=403, detail="No access to study")

    if need_phi and not sa.can_view_phi:
        raise HTTPException(status_code=403, detail="PHI access not granted")
    return study
