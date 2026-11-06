# MedImage Studio (Phase 1)

Research-oriented **MedImage Studio** is a locally runnable stack for uploading medical imaging (DICOM / NIfTI), viewing it, running a **real** (non-placeholder) segmentation pipeline where configured, reviewing outputs, and exporting masks — **without presenting AI output as definitive diagnosis or treatment**.

## Non‑negotiables (implemented in UX + API)

- AI output is **not** labeled as definitive diagnosis or therapy; the UI footer states (EN/FA): research and specialist review only.
- No fabricated confidence scores, heatmaps, or masks: the default active “model” uses **classical Otsu** thresholding on NIfTI volumes when the engine is `classical_otsu_nifti` (explicitly documented as non-clinical research assistance).
- MONAI-bundle / deep models stay **inactive** until you add a **pinned** `weights_sha256`, bundle path, and license — the registry and job gate enforce this.
- File types are validated from **binary content**, not extension alone (`imaging_validate.sniff_upload_kind`, pydicom/nibabel).
- Default processing is **local** (Docker Compose); no external image APIs.
- Audit logs store **opaque IDs** and small safe JSON — not full DICOM headers or pixel data.
- **De-identification** is exposed as an honest stub: full anonymization is **not implemented** (see `/studies/{id}/deidentify`).

## Architecture (as delivered)

| Layer        | Technology |
|-------------|------------|
| Frontend    | React + TypeScript + Vite, i18n (EN/FA, RTL), Niivue for NIfTI |
| Backend API | FastAPI, OpenAPI at `/docs`, JWT auth, RBAC (`admin` / `reviewer` / `viewer`) |
| Worker      | RQ + Redis; classical Otsu pipeline + hook for MONAI when configured |
| DB          | PostgreSQL (SQLAlchemy + Alembic) |
| Queue       | Redis |
| Object store| MinIO (S3-compatible) |
| DICOM       | Orthanc + DICOMweb (`/dicom-web`), REST at `:8042` |

**Phase 2** (classification, MPR/3D, DICOM‑SEG, advanced review) is **not** implemented; it is listed under *Not implemented* below.

## Quick start (Docker Compose)

**MinIO image:** Official `minio/minio` on Docker Hub is no longer reliably pullable without login. This project uses **`cgr.dev/chainguard/minio:latest`** (built from MinIO source). The init job uses **`amazon/aws-cli`** to create the bucket instead of `minio/mc`.

## Quick start (Docker Compose)

1. Copy environment file:

   ```bash
   cp .env.example .env
   ```

2. Adjust secrets in `.env` (JWT, Postgres, Orthanc, MinIO).

3. Start stack:

   ```bash
   docker compose build
   docker compose up -d
   ```

4. Wait for backend migrations (entrypoint runs `alembic upgrade head` + seeds):

   - **API**: http://localhost:8000 — OpenAPI: http://localhost:8000/docs  
   - **UI**: http://localhost:5173  
   - **Orthanc**: http://localhost:8042 (user/pass from `ORTHANC_*` / `infra/orthanc/orthanc.json`)  
   - **MinIO console**: http://localhost:9001  

5. **Login** (default admin from compose):

   - Email: `admin@medimage.local`  
   - Password: `ChangeMeAdmin123!`  

   Change `ADMIN_EMAIL` / `ADMIN_PASSWORD` in `.env` before production use.

## Supported flows

### DICOM

- Upload `.dcm` or a `.zip` of instances (one study UID per zip).
- Files are validated with **pydicom** and stored in **Orthanc**; series metadata is mirrored in PostgreSQL.
- **Viewer**: open the Orthanc **Stone Web Viewer** link from the study page (new tab); OHIF is not embedded in v1 to avoid auth/CORS complexity with Orthanc — DICOMweb base URL is shown for integration.

### NIfTI

- Upload `.nii` / `.nii.gz` (or zip with a single volume).
- Validated with **nibabel**; object stored in MinIO; **Niivue** loads a presigned URL (affine preserved in stored file).

### Segmentation job (real inference path in v1)

- **Active by default**: registry model **“CT NIfTI — classical Otsu foreground (non-ML)”** (`inference_engine: classical_otsu_nifti`).
- **Only** `nifti_s3` series are accepted for this engine (DICOM series are rejected with a clear message).
- Worker runs Otsu on z-score normalized data, writes **mask NIfTI** (same geometry) and a **PNG overlay** preview — **not** an anatomical label map.
- **MONAI bundle** path: set `MONAI_BUNDLE_PATH` and extend `worker/app/tasks.py`; keep `weights_sha256` in DB and activate only after verification.

### Manual mask upload

- `POST /api/v1/jobs/{job_id}/user-mask` with NIfTI bytes; model output key preserved; user edit tracked (`edited_by_user_id`, `edited_at`).

### Model registry

- Seeded from `backend/registry/default_models.json` (no auto-download).
- Fields: name, version, license, optional `weights_sha256`, modalities/body parts, input JSON, output classes, preprocess, constraints, `bundle_path`, `is_active`.

### Study access / PHI

- Owners always see studies; `study_access` exists for future shared PHI — **identity-bearing DICOM tags are not surfaced in list APIs** by default (viewer uses Orthanc directly for full DICOM). Stricter PHI tagging can be layered per endpoint.

## Tests

Unit tests (geometry / gating):

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
PYTHONPATH=. pytest tests/test_imaging_validate.py tests/test_model_match.py -q
```

End-to-end (against running `docker compose`, synthetic NIfTI):

```bash
export MEDIMAGE_E2E=1
export MEDIMAGE_API=http://localhost:8000
pytest backend/tests/test_e2e_segmentation.py -s
```

## Model configuration (pins)

1. Place verified weights under `./models` or `/data/models` (worker volume `model_weights`).
2. Compute SHA-256 and set `weights_sha256` on the `model_registry` row; set `bundle_path`, `license_text`, `is_active=true`.
3. Implement the matching branch in `worker/app/tasks.py` (MONAI bundle loading is **not** shipped — add explicitly).

## Limitations (honest)

| Area | Status |
|------|--------|
| MONAI Bundle CT segmentation | **Not implemented** — placeholder registry entry explains missing weights |
| Embedded OHIF viewer | **Not implemented** — Orthanc Stone Web + DICOMweb URL instead |
| DICOM‑SEG export | **Not implemented** (only when reference series linking is fully tested) |
| In-browser brush/eraser mask editing | **Not implemented** — upload edited NIfTI instead |
| Full de-identification | **Not implemented** — stub endpoint documents limits |
| Phase 2 (classification, MPR/3D, batch reports, external API) | **Not implemented** |

## RTL / i18n

- Toggle English / فارسی in the header; `dir` switches for RTL.

---

**Disclaimer:** This software is a **research and review aid**. Clinical use requires validation, regulatory review, and local legal compliance.
