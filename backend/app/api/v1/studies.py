from __future__ import annotations

import io
import json
import uuid
import zipfile
from datetime import datetime, timezone
from typing import Annotated, Any, Optional

import httpx
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import audit_log
from app.config import settings
from app.database import get_db
from app.deps import assert_study_access, get_current_user
from app.imaging_validate import (
    ValidationError,
    series_dims_json_from_dicom_meta,
    sniff_upload_kind,
    validate_dicom_bytes,
    validate_nifti_bytes,
    validate_zip_not_evil,
)
from app.models import Image as DbImage
from app.models import Job, Series, Study, User
from app.orthanc_client import orthanc_find_study_by_uid, orthanc_get_series, orthanc_get_study, orthanc_post_instances
from app.schemas import SeriesOut, StudyDetailOut, StudyOut
from app.storage import object_key, upload_bytes

router = APIRouter()


@router.get("/", response_model=list[StudyOut])
async def list_studies(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    q: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
):
    stmt = select(Study).where(Study.deleted_at.is_(None))
    if user.role != "admin":
        stmt = stmt.where(Study.owner_id == user.id)
    if q:
        stmt = stmt.where(Study.title.ilike(f"%{q}%"))
    if status_filter:
        stmt = stmt.where(Study.status == status_filter)
    stmt = stmt.order_by(Study.updated_at.desc())
    res = await db.execute(stmt)
    return list(res.scalars().all())


@router.get("/{study_id}", response_model=StudyDetailOut)
async def get_study(
    study_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    study = await assert_study_access(db, user, study_id)
    sres = await db.execute(select(Series).where(Series.study_id == study_id))
    series = list(sres.scalars().all())
    return StudyDetailOut(
        id=study.id,
        title=study.title,
        status=study.status,
        created_at=study.created_at,
        updated_at=study.updated_at,
        series=[SeriesOut.model_validate(s) for s in series],
    )


@router.delete("/{study_id}")
async def delete_study(
    study_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    study = await assert_study_access(db, user, study_id)
    if study.owner_id != user.id and user.role != "admin":
        raise HTTPException(status_code=403, detail="Only owner or admin can delete")
    study.deleted_at = datetime.now(timezone.utc)
    study.status = "deleted"
    await audit_log(
        db,
        user_id=user.id,
        action="study_delete",
        resource_type="study",
        resource_id=str(study.id),
    )
    await db.commit()
    return {"ok": True}


async def _ingest_dicom_bytes(
    db: AsyncSession,
    user: User,
    data: bytes,
    filename: str,
    title: Optional[str],
) -> Study:
    try:
        meta = validate_dicom_bytes(data)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    try:
        inst = await orthanc_post_instances(data)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Orthanc ingest failed: {e}") from e

    study_uid = meta.get("study_instance_uid") or ""
    if not study_uid:
        raise HTTPException(status_code=400, detail="DICOM missing StudyInstanceUID")

    orth_study_id = await orthanc_find_study_by_uid(study_uid)
    if not orth_study_id:
        raise HTTPException(status_code=500, detail="Could not locate study in Orthanc after upload")

    study_json = await orthanc_get_study(orth_study_id)
    st = Study(
        title=title or f"DICOM Study {study_uid[-8:]}",
        status="ready",
        owner_id=user.id,
        orthanc_study_uid=study_uid,
        study_instance_uid=study_uid,
        orthanc_internal_id=orth_study_id,
    )
    db.add(st)
    await db.flush()

    for ser_id in study_json.get("Series", []):
        ser_j = await orthanc_get_series(ser_id)
        tags = ser_j.get("MainDicomTags", {})
        modality = tags.get("Modality", "") or None
        body = tags.get("BodyPartExamined", "") or None
        series = Series(
            study_id=st.id,
            modality=modality,
            body_part=body,
            series_instance_uid=tags.get("SeriesInstanceUID"),
            orthanc_series_id=str(ser_id),
            storage_type="dicom_orthanc",
            dims_json=series_dims_json_from_dicom_meta(
                {
                    "rows": int(tags["Rows"]) if tags.get("Rows") not in (None, "") else 0,
                    "columns": int(tags["Columns"]) if tags.get("Columns") not in (None, "") else 0,
                    "number_of_frames": int(tags["NumberOfFrames"])
                    if tags.get("NumberOfFrames") not in (None, "")
                    else 0,
                }
            ),
            slice_count=len(ser_j.get("Instances", [])) or None,
        )
        db.add(series)

    await audit_log(
        db,
        user_id=user.id,
        action="study_upload_dicom",
        resource_type="study",
        resource_id=str(st.id),
        detail_safe={"modality": meta.get("modality"), "demo_label": settings.demo_data_label},
    )
    await db.commit()
    await db.refresh(st)
    return st


async def _ingest_nifti_bytes(
    db: AsyncSession,
    user: User,
    data: bytes,
    title: Optional[str],
) -> Study:
    try:
        info = validate_nifti_bytes(data)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    key = object_key("nifti", "volume.nii.gz")
    upload_bytes(data, key, "application/gzip")

    st = Study(
        title=title or "NIfTI volume",
        status="ready",
        owner_id=user.id,
    )
    db.add(st)
    await db.flush()

    series = Series(
        study_id=st.id,
        modality="UNKNOWN",
        body_part=None,
        storage_type="nifti_s3",
        dims_json=json.dumps({"shape": list(info.shape)}),
        spacing_json=json.dumps(list(info.zooms)),
        affine_json=json.dumps(info.affine),
        orientation="from_affine",
        slice_count=int(info.shape[-1]) if len(info.shape) >= 1 else None,
    )
    db.add(series)
    await db.flush()
    im = DbImage(series_id=series.id, object_key=key, extra_meta=json.dumps({"format": "nifti"}))
    db.add(im)

    await audit_log(
        db,
        user_id=user.id,
        action="study_upload_nifti",
        resource_type="study",
        resource_id=str(st.id),
        detail_safe={"shape": list(info.shape), "demo_label": settings.demo_data_label},
    )
    await db.commit()
    await db.refresh(st)
    return st


@router.post("/upload", response_model=StudyOut)
async def upload_study(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
):
    raw = await file.read()
    if len(raw) > settings.upload_max_bytes:
        raise HTTPException(status_code=413, detail="File exceeds configured upload limit")

    try:
        kind = sniff_upload_kind(file.filename or "upload", raw)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    if kind == "dicom":
        st = await _ingest_dicom_bytes(db, user, raw, file.filename or "instance.dcm", title)
        return st

    if kind == "nifti":
        return await _ingest_nifti_bytes(db, user, raw, title)

    if kind == "zip":
        zbuf = io.BytesIO(raw)
        try:
            z = zipfile.ZipFile(zbuf)
        except zipfile.BadZipFile as e:
            raise HTTPException(status_code=400, detail="Invalid ZIP") from e
        try:
            validate_zip_not_evil(z, max_uncompressed=settings.upload_max_bytes)
        except ValidationError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e

        dicom_files: list[bytes] = []
        nifti_files: list[bytes] = []
        for name in z.namelist():
            if name.endswith("/"):
                continue
            chunk = z.read(name)
            if len(chunk) > settings.upload_max_bytes:
                raise HTTPException(status_code=413, detail="Zip member too large")
            try:
                k = sniff_upload_kind(name, chunk)
            except ValidationError:
                continue
            if k == "dicom":
                dicom_files.append(chunk)
            elif k == "nifti":
                nifti_files.append(chunk)

        if dicom_files and nifti_files:
            raise HTTPException(status_code=400, detail="Mixed DICOM and NIfTI in one archive is not supported")

        if dicom_files:
            study_uid: Optional[str] = None
            for d in dicom_files:
                meta = validate_dicom_bytes(d)
                su = meta.get("study_instance_uid")
                if not su:
                    raise HTTPException(status_code=400, detail="DICOM in ZIP missing StudyInstanceUID")
                if study_uid is None:
                    study_uid = su
                elif study_uid != su:
                    raise HTTPException(
                        status_code=400, detail="All DICOM files in ZIP must share the same StudyInstanceUID"
                    )
                await orthanc_post_instances(d)
            assert study_uid
            orth_study_id = await orthanc_find_study_by_uid(study_uid)
            if not orth_study_id:
                raise HTTPException(status_code=500, detail="Could not locate study in Orthanc after batch upload")
            study_json = await orthanc_get_study(orth_study_id)
            st = Study(
                title=title or f"DICOM Study {study_uid[-8:]}",
                status="ready",
                owner_id=user.id,
                orthanc_study_uid=study_uid,
                study_instance_uid=study_uid,
                orthanc_internal_id=orth_study_id,
            )
            db.add(st)
            await db.flush()
            for ser_id in study_json.get("Series", []):
                ser_j = await orthanc_get_series(ser_id)
                tags = ser_j.get("MainDicomTags", {})
                tr = tags.get("Rows")
                tc = tags.get("Columns")
                series = Series(
                    study_id=st.id,
                    modality=tags.get("Modality", "") or None,
                    body_part=tags.get("BodyPartExamined", "") or None,
                    series_instance_uid=tags.get("SeriesInstanceUID"),
                    orthanc_series_id=str(ser_id),
                    storage_type="dicom_orthanc",
                    dims_json=series_dims_json_from_dicom_meta(
                        {
                            "rows": int(tr) if tr not in (None, "") else 0,
                            "columns": int(tc) if tc not in (None, "") else 0,
                            "number_of_frames": int(tags["NumberOfFrames"])
                            if tags.get("NumberOfFrames") not in (None, "")
                            else 0,
                        }
                    ),
                    slice_count=len(ser_j.get("Instances", [])) or None,
                )
                db.add(series)
            await audit_log(
                db,
                user_id=user.id,
                action="study_upload_zip_dicom",
                resource_type="study",
                resource_id=str(st.id),
            )
            await db.commit()
            await db.refresh(st)
            return st

        if nifti_files:
            if len(nifti_files) > 1:
                raise HTTPException(status_code=400, detail="Only one NIfTI per ZIP supported in this version")
            return await _ingest_nifti_bytes(db, user, nifti_files[0], title)

        raise HTTPException(status_code=400, detail="No valid DICOM or NIfTI found in archive")

    raise HTTPException(status_code=400, detail=f"Unsupported kind {kind}")


@router.get("/{study_id}/viewer")
async def viewer_info(
    study_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    study = await assert_study_access(db, user, study_id)
    base = settings.orthanc_url.rstrip("/")
    out: dict[str, Any] = {
        "study_instance_uid": study.study_instance_uid,
        "orthanc_internal_id": study.orthanc_internal_id,
        "dicomweb_root": f"{base}/dicom-web",
        "disclaimer": "For research and specialist review only — not for diagnostic or treatment decisions.",
        "nifti_only": study.orthanc_internal_id is None,
    }
    if study.orthanc_internal_id:
        out["stone_webviewer"] = f"{base}/stone-webviewer/index.html?study={study.orthanc_internal_id}"
    return out
