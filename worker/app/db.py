import uuid
from datetime import datetime
from typing import Generator

from sqlalchemy import DateTime, Float, ForeignKey, String, Text, create_engine
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from app.config import settings

UUID_COL = UUID(as_uuid=True)


class Base(DeclarativeBase):
    pass


class ModelRegistry(Base):
    __tablename__ = "model_registry"

    id: Mapped[uuid.UUID] = mapped_column(UUID_COL, primary_key=True)
    name: Mapped[str] = mapped_column(String(256))
    version: Mapped[str] = mapped_column(String(64))
    input_requirements_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    output_classes_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    preprocess_config_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    weights_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)


class Series(Base):
    __tablename__ = "series"

    id: Mapped[uuid.UUID] = mapped_column(UUID_COL, primary_key=True)
    study_id: Mapped[uuid.UUID] = mapped_column(UUID_COL)
    modality: Mapped[str | None] = mapped_column(String(16), nullable=True)
    body_part: Mapped[str | None] = mapped_column(String(64), nullable=True)
    storage_type: Mapped[str] = mapped_column(String(32))
    dims_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    spacing_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    affine_json: Mapped[str | None] = mapped_column(Text, nullable=True)


class Image(Base):
    __tablename__ = "images"

    id: Mapped[uuid.UUID] = mapped_column(UUID_COL, primary_key=True)
    series_id: Mapped[uuid.UUID] = mapped_column(UUID_COL, ForeignKey("series.id"))
    object_key: Mapped[str | None] = mapped_column(String(1024), nullable=True)


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID_COL, primary_key=True)
    study_id: Mapped[uuid.UUID] = mapped_column(UUID_COL)
    series_id: Mapped[uuid.UUID] = mapped_column(UUID_COL)
    model_id: Mapped[uuid.UUID | None] = mapped_column(UUID_COL, nullable=True)
    status: Mapped[str] = mapped_column(String(32))
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    rq_job_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    runtime_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SegmentationResult(Base):
    __tablename__ = "segmentation_results"

    id: Mapped[uuid.UUID] = mapped_column(UUID_COL, primary_key=True)
    job_id: Mapped[uuid.UUID] = mapped_column(UUID_COL, ForeignKey("jobs.id"))
    mask_nifti_key: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    overlay_png_key: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    model_output_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    class_labels_json: Mapped[str | None] = mapped_column(Text, nullable=True)


_sync_url = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
if _sync_url.startswith("postgresql+asyncpg"):
    _sync_url = _sync_url.replace("postgresql+asyncpg", "postgresql")

engine = create_engine(_sync_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, class_=Session)


def get_session() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
