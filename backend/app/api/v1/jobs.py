from __future__ import annotations

import json
import uuid
from typing import Annotated, Any, Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import audit_log
from app.database import get_db
from app.deps import assert_study_access, get_current_user
from app.models import Job, ModelRegistry, SegmentationResult, Series, User
from app.queueconn import get_queue
from app.schemas import JobCreate, JobOut
from app.imaging_validate import ValidationError, validate_nifti_bytes
from app.storage import object_key, presign_get, upload_bytes

router = APIRouter()


def _parse_json(s: Optional[str]) -> dict[str, Any]:
    if not s:
        return {}
    try:
        return json.loads(s)
    except Exception:
        return {}


def _model_matches_series(m: ModelRegistry, ser: Series) -> tuple[bool, str]:
    """Return (ok, reason_if_not)."""
    if not m.is_active:
        return False, "Model is inactive — configure weights, license, and mark active in registry."
    req = _parse_json(m.input_requirements_json)
    engine = req.get("inference_engine") or ""
    if engine != "classical_otsu_nifti" and not m.weights_sha256:
        return False, "Model weights hash not pinned — unsafe to run (or engine not configured)."
    mods = json.loads(m.allowed_modalities or "[]")
    body_ok = json.loads(m.allowed_body_parts or "[]")
    mod = (ser.modality or "").upper()
    bp = (ser.body_part or "").upper()
    if mods and mod and mod not in [str(x).upper() for x in mods]:
        return False, f"Modality {mod} not supported by this model."
    if body_ok and bp and bp not in [str(x).upper() for x in body_ok] and "" not in body_ok:
        return False, f"Body part {bp or 'unknown'} not in model scope."
    if ser.storage_type != "nifti_s3":
        return False, "This build runs segmentation only on NIfTI series stored in object storage (not DICOM-in-Orthanc)."
    dims = _parse_json(ser.dims_json).get("shape")
    if not dims or not isinstance(dims, list):
        return False, "Series missing validated shape metadata — cannot verify model input."
    # expect [..., Z, Y, X] or [Z,Y,X] — nib default
    min_dims = req.get("min_dims_zyx") or req.get("min_dims")
    if min_dims and len(min_dims) == len(dims):
        for a, b in zip(dims, min_dims):
            if int(a) < int(b):
                return False, "Volume smaller than minimum required dimensions for this model."
    max_vox = req.get("max_voxels")
    if max_vox:
        prod = 1
        for d in dims:
            prod *= int(d)
        if prod > int(max_vox):
            return False, "Volume exceeds maximum voxel count for this model."
    return True, ""


@router.post("/", response_model=JobOut)
async def create_job(
    body: JobCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    ser = await db.execute(select(Series).where(Series.id == body.series_id))
    series = ser.scalar_one_or_none()
    if not series:
        raise HTTPException(status_code=404, detail="Series not found")
    study = await assert_study_access(db, user, series.study_id)

    model: Optional[ModelRegistry] = None
    if body.model_id:
        mr = await db.execute(select(ModelRegistry).where(ModelRegistry.id == body.model_id))
        model = mr.scalar_one_or_none()
        if not model:
            raise HTTPException(status_code=404, detail="Model not found")
    else:
        mr = await db.execute(select(ModelRegistry).where(ModelRegistry.is_active == True))  # noqa: E712
        model = mr.scalars().first()
        if not model:
            raise HTTPException(
                status_code=400,
                detail="No active model in registry — add pinned weights or activate a configured model.",
            )

    ok, reason = _model_matches_series(model, series)
    if not ok:
        raise HTTPException(status_code=400, detail=reason)

    job = Job(
        study_id=study.id,
        series_id=series.id,
        model_id=model.id,
        status="queued",
    )
    db.add(job)
    await db.flush()

    q = get_queue()
    rq_job = q.enqueue("app.tasks.run_segmentation_job", str(job.id))
    job.rq_job_id = rq_job.id

    await audit_log(
        db,
        user_id=user.id,
        action="job_create",
        resource_type="job",
        resource_id=str(job.id),
        detail_safe={"model": str(model.id), "series": str(series.id)},
    )
    await db.commit()
    await db.refresh(job)
    return job


@router.get("/{job_id}", response_model=JobOut)
async def get_job(
    job_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    r = await db.execute(select(Job).where(Job.id == job_id))
    job = r.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    await assert_study_access(db, user, job.study_id)
    return job


@router.get("/{job_id}/result")
async def job_result(
    job_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    r = await db.execute(select(Job).where(Job.id == job_id))
    job = r.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    await assert_study_access(db, user, job.study_id)

    sr = await db.execute(select(SegmentationResult).where(SegmentationResult.job_id == job_id))
    seg = sr.scalar_one_or_none()

    out: dict[str, Any] = {
        "job": JobOut.model_validate(job).model_dump(),
        "mask_url": presign_get(seg.mask_nifti_key) if seg and seg.mask_nifti_key else None,
        "overlay_url": presign_get(seg.overlay_png_key) if seg and seg.overlay_png_key else None,
        "model_version": seg.model_output_version if seg else None,
        "class_labels": json.loads(seg.class_labels_json or "[]") if seg else [],
    }
    return out


@router.post("/{job_id}/user-mask")
async def upload_user_edited_mask(
    job_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    file: UploadFile = File(...),
):
    r = await db.execute(select(Job).where(Job.id == job_id))
    job = r.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    await assert_study_access(db, user, job.study_id)

    raw = await file.read()
    try:
        validate_nifti_bytes(raw)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    key = object_key("user-masks", f"{job_id}.nii.gz")
    upload_bytes(raw, key, "application/gzip")

    sr = await db.execute(select(SegmentationResult).where(SegmentationResult.job_id == job_id))
    seg = sr.scalar_one_or_none()
    if not seg:
        seg = SegmentationResult(job_id=job_id)
        db.add(seg)
        await db.flush()
    seg.user_edited_mask_key = key
    seg.edited_by_user_id = user.id
    from datetime import datetime, timezone

    seg.edited_at = datetime.now(timezone.utc)

    await audit_log(
        db,
        user_id=user.id,
        action="mask_user_edit_upload",
        resource_type="job",
        resource_id=str(job_id),
    )
    await db.commit()
    return {"user_mask_url": presign_get(key)}
