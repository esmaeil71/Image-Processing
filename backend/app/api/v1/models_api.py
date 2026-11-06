import json
import uuid
from typing import Annotated, Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_current_user
from app.models import ModelRegistry, User

router = APIRouter()


def _parse_list(s: Optional[str]) -> list[Any]:
    if not s:
        return []
    try:
        return json.loads(s)
    except Exception:
        return []


@router.get("/")
async def list_models(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
):
    r = await db.execute(select(ModelRegistry).order_by(ModelRegistry.name))
    rows = list(r.scalars().all())
    return [
        {
            "id": m.id,
            "name": m.name,
            "version": m.version,
            "is_active": m.is_active,
            "constraints_text": m.constraints_text,
            "allowed_modalities": _parse_list(m.allowed_modalities),
            "allowed_body_parts": _parse_list(m.allowed_body_parts),
            "output_classes": _parse_list(m.output_classes_json),
            "weights_sha256": m.weights_sha256,
            "bundle_path": m.bundle_path,
        }
        for m in rows
    ]


@router.get("/{model_id}")
async def get_model(
    model_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
):
    r = await db.execute(select(ModelRegistry).where(ModelRegistry.id == model_id))
    m = r.scalar_one_or_none()
    if not m:
        raise HTTPException(status_code=404, detail="Model not found")
    return {
        "id": m.id,
        "name": m.name,
        "version": m.version,
        "is_active": m.is_active,
        "source_url": m.source_url,
        "license_text": m.license_text,
        "weights_sha256": m.weights_sha256,
        "allowed_modalities": _parse_list(m.allowed_modalities),
        "allowed_body_parts": _parse_list(m.allowed_body_parts),
        "input_requirements": json.loads(m.input_requirements_json or "{}"),
        "output_classes": _parse_list(m.output_classes_json),
        "preprocess": json.loads(m.preprocess_config_json or "{}"),
        "constraints_text": m.constraints_text,
        "bundle_path": m.bundle_path,
    }
