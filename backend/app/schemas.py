from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, EmailStr, Field


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: Optional[str] = None
    role: str = "viewer"


class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    role: str
    full_name: Optional[str] = None

    model_config = {"from_attributes": True}


class StudyOut(BaseModel):
    id: uuid.UUID
    title: Optional[str]
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SeriesOut(BaseModel):
    id: uuid.UUID
    modality: Optional[str]
    body_part: Optional[str]
    storage_type: str
    slice_count: Optional[int] = None

    model_config = {"from_attributes": True}


class StudyDetailOut(StudyOut):
    series: list[SeriesOut] = []


class JobCreate(BaseModel):
    series_id: uuid.UUID
    model_id: Optional[uuid.UUID] = None


class JobOut(BaseModel):
    id: uuid.UUID
    study_id: uuid.UUID
    series_id: uuid.UUID
    model_id: Optional[uuid.UUID]
    status: str
    error_message: Optional[str]
    runtime_seconds: Optional[float]
    created_at: datetime

    model_config = {"from_attributes": True}


class ModelRegistryOut(BaseModel):
    id: uuid.UUID
    name: str
    version: str
    is_active: bool
    constraints_text: Optional[str]
    allowed_modalities: Optional[list[str]] = None
    output_classes: Optional[list[dict[str, Any]]] = None

    model_config = {"from_attributes": True}


class SegmentationResultOut(BaseModel):
    id: uuid.UUID
    job_id: uuid.UUID
    mask_nifti_key: Optional[str]
    overlay_png_key: Optional[str]
    model_output_version: Optional[str]
    class_labels: Optional[list[Any]] = None

    model_config = {"from_attributes": True}
