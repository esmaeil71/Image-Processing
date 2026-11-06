"""initial schema

Revision ID: 0001
Revises:
Create Date: 2025-11-06

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("email", sa.String(320), nullable=False, unique=True, index=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("role", sa.String(32), nullable=False, server_default="viewer"),
        sa.Column("full_name", sa.String(255), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "studies",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("title", sa.String(512), nullable=True),
        sa.Column("status", sa.String(64), server_default="uploaded"),
        sa.Column("owner_id", sa.UUID(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("orthanc_study_uid", sa.String(128), nullable=True),
        sa.Column("study_instance_uid", sa.String(128), nullable=True),
        sa.Column("orthanc_internal_id", sa.String(128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_studies_owner", "studies", ["owner_id"])
    op.create_table(
        "study_access",
        sa.Column("study_id", sa.UUID(), sa.ForeignKey("studies.id"), primary_key=True),
        sa.Column("user_id", sa.UUID(), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("can_view_phi", sa.Boolean(), server_default="false"),
    )
    op.create_table(
        "series",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("study_id", sa.UUID(), sa.ForeignKey("studies.id"), nullable=False),
        sa.Column("modality", sa.String(16), nullable=True),
        sa.Column("body_part", sa.String(64), nullable=True),
        sa.Column("series_instance_uid", sa.String(128), nullable=True),
        sa.Column("orthanc_series_id", sa.String(128), nullable=True),
        sa.Column("storage_type", sa.String(32), nullable=False),
        sa.Column("dims_json", sa.Text(), nullable=True),
        sa.Column("spacing_json", sa.Text(), nullable=True),
        sa.Column("affine_json", sa.Text(), nullable=True),
        sa.Column("orientation", sa.String(8), nullable=True),
        sa.Column("slice_count", sa.Integer(), nullable=True),
    )
    op.create_index("ix_series_study", "series", ["study_id"])
    op.create_table(
        "images",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("series_id", sa.UUID(), sa.ForeignKey("series.id"), nullable=False),
        sa.Column("instance_uid", sa.String(128), nullable=True),
        sa.Column("sop_class_uid", sa.String(128), nullable=True),
        sa.Column("object_key", sa.String(1024), nullable=True),
        sa.Column("thumbnail_key", sa.String(1024), nullable=True),
        sa.Column("extra_meta", sa.Text(), nullable=True),
    )
    op.create_index("ix_images_series", "images", ["series_id"])
    op.create_table(
        "model_registry",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("version", sa.String(64), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("license_text", sa.Text(), nullable=True),
        sa.Column("weights_sha256", sa.String(64), nullable=True),
        sa.Column("allowed_modalities", sa.Text(), nullable=True),
        sa.Column("allowed_body_parts", sa.Text(), nullable=True),
        sa.Column("input_requirements_json", sa.Text(), nullable=True),
        sa.Column("output_classes_json", sa.Text(), nullable=True),
        sa.Column("preprocess_config_json", sa.Text(), nullable=True),
        sa.Column("constraints_text", sa.Text(), nullable=True),
        sa.Column("bundle_path", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "jobs",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("study_id", sa.UUID(), sa.ForeignKey("studies.id"), nullable=False),
        sa.Column("series_id", sa.UUID(), sa.ForeignKey("series.id"), nullable=False),
        sa.Column("model_id", sa.UUID(), sa.ForeignKey("model_registry.id"), nullable=True),
        sa.Column("status", sa.String(32), server_default="queued"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("rq_job_id", sa.String(128), nullable=True),
        sa.Column("runtime_seconds", sa.Float(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_jobs_study", "jobs", ["study_id"])
    op.create_table(
        "segmentation_results",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("job_id", sa.UUID(), sa.ForeignKey("jobs.id"), nullable=False),
        sa.Column("mask_nifti_key", sa.String(1024), nullable=True),
        sa.Column("overlay_png_key", sa.String(1024), nullable=True),
        sa.Column("model_output_version", sa.String(64), nullable=True),
        sa.Column("user_edited_mask_key", sa.String(1024), nullable=True),
        sa.Column("edited_by_user_id", sa.UUID(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("edited_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("class_labels_json", sa.Text(), nullable=True),
    )
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("user_id", sa.UUID(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("resource_type", sa.String(64), nullable=True),
        sa.Column("resource_id", sa.String(64), nullable=True),
        sa.Column("detail_safe", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_audit_created", "audit_logs", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_audit_created", table_name="audit_logs")
    op.drop_table("audit_logs")
    op.drop_table("segmentation_results")
    op.drop_index("ix_jobs_study", table_name="jobs")
    op.drop_table("jobs")
    op.drop_table("model_registry")
    op.drop_index("ix_images_series", table_name="images")
    op.drop_table("images")
    op.drop_index("ix_series_study", table_name="series")
    op.drop_table("series")
    op.drop_table("study_access")
    op.drop_index("ix_studies_owner", table_name="studies")
    op.drop_table("studies")
    op.drop_table("users")
