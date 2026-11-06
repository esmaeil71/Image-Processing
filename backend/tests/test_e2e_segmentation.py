"""
End-to-end path against a running API (docker compose up).

Run: MEDIMAGE_E2E=1 pytest tests/test_e2e_segmentation.py -s

Requires: admin login and a small synthetic NIfTI reachable locally or via URL.
"""
import io
import os

import nibabel as nib
import numpy as np
import pytest

httpx = pytest.importorskip("httpx")


BASE = os.environ.get("MEDIMAGE_API", "http://localhost:8000")


@pytest.mark.skipif(os.environ.get("MEDIMAGE_E2E") != "1", reason="Set MEDIMAGE_E2E=1")
@pytest.mark.asyncio
async def test_upload_nifti_run_job():
    admin_email = os.environ.get("ADMIN_EMAIL", "admin@medimage.local")
    admin_password = os.environ.get("ADMIN_PASSWORD", "ChangeMeAdmin123!")

    async with httpx.AsyncClient(base_url=BASE, timeout=120.0) as client:
        r = await client.post(
            "/api/v1/auth/login",
            data={"username": admin_email, "password": admin_password},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert r.status_code == 200, r.text
        token = r.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        data = np.random.rand(12, 14, 10).astype(np.float32)
        img = nib.Nifti1Image(data, np.eye(4))
        buf = io.BytesIO()
        nib.save(img, buf)
        raw = buf.getvalue()

        files = {"file": ("synth.nii.gz", raw, "application/gzip")}
        u = await client.post("/api/v1/studies/upload", files=files, headers=headers, data={"title": "e2e synthetic"})
        assert u.status_code == 200, u.text
        study = u.json()
        study_id = study["id"]

        g = await client.get(f"/api/v1/studies/{study_id}", headers=headers)
        assert g.status_code == 200
        detail = g.json()
        series_id = detail["series"][0]["id"]

        mlist = await client.get("/api/v1/models/", headers=headers)
        models = mlist.json()
        active = next((m for m in models if m.get("is_active")), None)
        assert active, "Need an active model in registry for e2e"

        j = await client.post(
            "/api/v1/jobs/",
            json={"series_id": series_id, "model_id": str(active["id"])},
            headers=headers,
        )
        assert j.status_code == 200, j.text
        job_id = j.json()["id"]

        for _ in range(60):
            sj = await client.get(f"/api/v1/jobs/{job_id}", headers=headers)
            st = sj.json()["status"]
            if st in ("completed", "failed"):
                break
            import asyncio

            await asyncio.sleep(1)
        assert sj.json()["status"] == "completed", sj.json()

        res = await client.get(f"/api/v1/jobs/{job_id}/result", headers=headers)
        assert res.status_code == 200
        body = res.json()
        assert body.get("mask_url"), "missing mask presign"
