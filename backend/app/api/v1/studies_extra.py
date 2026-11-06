"""
Extra study endpoints (volume URL, PHI) split for clarity.
"""
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import assert_study_access, get_current_user, require_role
from app.models import Image, Series, User
from app.storage import presign_get

router = APIRouter()


@router.get("/{study_id}/series/{series_id}/volume-url")
async def volume_presigned_url(
    study_id: uuid.UUID,
    series_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    await assert_study_access(db, user, study_id)
    ser = await db.execute(select(Series).where(Series.id == series_id, Series.study_id == study_id))
    series = ser.scalar_one_or_none()
    if not series:
        raise HTTPException(status_code=404, detail="Series not found")
    if series.storage_type != "nifti_s3":
        raise HTTPException(status_code=400, detail="Volume URL only for NIfTI stored in object storage")
    img = await db.execute(select(Image).where(Image.series_id == series_id))
    row = img.scalars().first()
    if not row or not row.object_key:
        raise HTTPException(status_code=404, detail="No volume object")
    return {"url": presign_get(row.object_key, expires=3600)}


@router.post("/{study_id}/deidentify")
async def deidentify_stub(
    study_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(require_role("admin", "reviewer"))],
):
    """
    Optional de-identification is not claimed as complete anonymization.
    This endpoint documents the limitation; full DICOM scrubbing is not implemented in v1.
    """
    await assert_study_access(db, user, study_id)
    return {
        "status": "not_implemented",
        "message": "Full de-identification requires pixel burnt-in audit, structured scrubbing, and legal review — not done in this build.",
    }
