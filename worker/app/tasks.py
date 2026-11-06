from __future__ import annotations

import json
import time
import uuid
from datetime import datetime, timezone

from sqlalchemy import select

from app.db import Image, Job, ModelRegistry, SegmentationResult, Series, SessionLocal
from app.infer_classical import run_otsu_on_nifti, store_results
from app.s3util import download_bytes


def run_segmentation_job(job_id_str: str) -> dict[str, str]:
    job_id = uuid.UUID(job_id_str)
    t0 = time.perf_counter()
    with SessionLocal() as db:
        try:
            job = db.execute(select(Job).where(Job.id == job_id)).scalar_one_or_none()
            if not job:
                return {"error": "job missing"}
            job.status = "running"
            job.error_message = None
            job.started_at = datetime.now(timezone.utc)
            db.commit()

            series = db.execute(select(Series).where(Series.id == job.series_id)).scalar_one_or_none()
            model = db.execute(select(ModelRegistry).where(ModelRegistry.id == job.model_id)).scalar_one_or_none()
            if not series or not model:
                raise RuntimeError("series or model missing")

            req = json.loads(model.input_requirements_json or "{}")
            engine = req.get("inference_engine") or ""

            im = db.execute(select(Image).where(Image.series_id == series.id)).scalars().first()
            if not im or not im.object_key:
                raise RuntimeError("No image object for series")

            raw = download_bytes(im.object_key)

            if engine == "classical_otsu_nifti":
                mask_b, png_b, meta = run_otsu_on_nifti(
                    raw, job_id=job_id, model_name=model.name, model_version=model.version
                )
                mk, pk = store_results(job_id, mask_b, png_b)
                seg = SegmentationResult(
                    id=uuid.uuid4(),
                    job_id=job.id,
                    mask_nifti_key=mk,
                    overlay_png_key=pk,
                    model_output_version=model.version,
                    class_labels_json=json.dumps(
                        [
                            {
                                "id": 1,
                                "label": "foreground",
                                "meta": meta,
                            }
                        ]
                    ),
                )
                db.add(seg)
                job.status = "completed"
            else:
                job.status = "failed"
                job.error_message = "Inference engine not implemented or MONAI bundle not mounted with valid weights."

            job.finished_at = datetime.now(timezone.utc)
            job.runtime_seconds = time.perf_counter() - t0
            db.commit()
            return {"status": job.status}
        except Exception as e:
            db.rollback()
            job = db.execute(select(Job).where(Job.id == job_id)).scalar_one_or_none()
            if job:
                job.status = "failed"
                job.error_message = str(e)[:4000]
                job.finished_at = datetime.now(timezone.utc)
                job.runtime_seconds = time.perf_counter() - t0
                db.commit()
            return {"error": str(e)}
