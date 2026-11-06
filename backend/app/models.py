from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, UUID_PK


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID_PK, primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(32), default="viewer")  # admin, reviewer, viewer
    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")


class Study(Base):
    __tablename__ = "studies"

    id: Mapped[uuid.UUID] = mapped_column(UUID_PK, primary_key=True, default=uuid.uuid4)
    title: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    status: Mapped[str] = mapped_column(String(64), default="uploaded")
    owner_id: Mapped[uuid.UUID] = mapped_column(UUID_PK, ForeignKey("users.id"))
    orthanc_study_uid: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    study_instance_uid: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    orthanc_internal_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    owner: Mapped["User"] = relationship("User")
    series_list: Mapped[list["Series"]] = relationship("Series", back_populates="study")


class StudyAccess(Base):
    __tablename__ = "study_access"

    study_id: Mapped[uuid.UUID] = mapped_column(UUID_PK, ForeignKey("studies.id"), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID_PK, ForeignKey("users.id"), primary_key=True)
    can_view_phi: Mapped[bool] = mapped_column(Boolean, default=False)


class Series(Base):
    __tablename__ = "series"

    id: Mapped[uuid.UUID] = mapped_column(UUID_PK, primary_key=True, default=uuid.uuid4)
    study_id: Mapped[uuid.UUID] = mapped_column(UUID_PK, ForeignKey("studies.id"))
    modality: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    body_part: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    series_instance_uid: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    orthanc_series_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    storage_type: Mapped[str] = mapped_column(String(32))  # dicom_orthanc, nifti_s3
    dims_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    spacing_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    affine_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    orientation: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)
    slice_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    study: Mapped["Study"] = relationship("Study", back_populates="series_list")
    images: Mapped[list["Image"]] = relationship("Image", back_populates="series")


class Image(Base):
    __tablename__ = "images"

    id: Mapped[uuid.UUID] = mapped_column(UUID_PK, primary_key=True, default=uuid.uuid4)
    series_id: Mapped[uuid.UUID] = mapped_column(UUID_PK, ForeignKey("series.id"))
    instance_uid: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    sop_class_uid: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    object_key: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    thumbnail_key: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    extra_meta: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    series: Mapped["Series"] = relationship("Series", back_populates="images")


class ModelRegistry(Base):
    __tablename__ = "model_registry"

    id: Mapped[uuid.UUID] = mapped_column(UUID_PK, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(256))
    version: Mapped[str] = mapped_column(String(64))
    source_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    license_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    weights_sha256: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    allowed_modalities: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON list
    allowed_body_parts: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    input_requirements_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    output_classes_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    preprocess_config_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    constraints_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    bundle_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID_PK, primary_key=True, default=uuid.uuid4)
    study_id: Mapped[uuid.UUID] = mapped_column(UUID_PK, ForeignKey("studies.id"))
    series_id: Mapped[uuid.UUID] = mapped_column(UUID_PK, ForeignKey("series.id"))
    model_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID_PK, ForeignKey("model_registry.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="queued")
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    rq_job_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    runtime_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")


class SegmentationResult(Base):
    __tablename__ = "segmentation_results"

    id: Mapped[uuid.UUID] = mapped_column(UUID_PK, primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(UUID_PK, ForeignKey("jobs.id"))
    mask_nifti_key: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    overlay_png_key: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    model_output_version: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    user_edited_mask_key: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    edited_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID_PK, ForeignKey("users.id"), nullable=True)
    edited_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    class_labels_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID_PK, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID_PK, ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(64))
    resource_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    resource_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    detail_safe: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")
