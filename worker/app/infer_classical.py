"""
Classical (non-ML) segmentation for reproducible pipelines — not clinical.
"""
from __future__ import annotations

import gzip
import io
import tempfile
import uuid
from pathlib import Path
from typing import Any, Tuple

import nibabel as nib
import numpy as np
from PIL import Image as PILImage
from skimage.filters import threshold_otsu

from app.s3util import upload_bytes


def _sample_threshold_otsu(vol: np.ndarray, max_samples: int = 2_000_000) -> float:
    flat = vol.ravel()
    if flat.size > max_samples:
        rng = np.random.default_rng(42)
        idx = rng.choice(flat.size, size=max_samples, replace=False)
        sample = flat[idx].astype(np.float64)
    else:
        sample = flat.astype(np.float64)
    return float(threshold_otsu(sample))


def run_otsu_on_nifti(
    nifti_bytes: bytes,
    *,
    job_id: uuid.UUID,
    model_name: str,
    model_version: str,
) -> Tuple[bytes, bytes, dict[str, Any]]:
    """Return (mask_nifti_bytes, overlay_png_bytes, meta)."""
    raw = nifti_bytes
    if raw[:2] == b"\x1f\x8b":
        raw = gzip.decompress(raw)
    path_in = ""
    try:
        with tempfile.NamedTemporaryFile(suffix=".nii", delete=False) as tmp:
            tmp.write(raw)
            path_in = tmp.name
        img = nib.load(path_in)
    finally:
        if path_in:
            Path(path_in).unlink(missing_ok=True)
    data = np.as_anyarray(img.dataobj).astype(np.float32)
    if data.size == 0:
        raise ValueError("Empty volume")

    mean = float(np.mean(data))
    std = float(np.std(data))
    if std < 1e-6:
        std = 1.0
    norm = (data - mean) / std

    thr = _sample_threshold_otsu(norm)
    mask = (norm > thr).astype(np.uint8)

    out_img = nib.Nifti1Image(mask, img.affine, img.header)
    path_out = ""
    try:
        with tempfile.NamedTemporaryFile(suffix=".nii.gz", delete=False) as tmp:
            path_out = tmp.name
        nib.save(out_img, path_out)
        mask_bytes = Path(path_out).read_bytes()
    finally:
        if path_out:
            Path(path_out).unlink(missing_ok=True)

    # middle slice along last spatial axis (NIfTI axis ordering preserved)
    vol = np.asarray(data)
    mk = np.asarray(mask)
    if vol.ndim == 4:
        vol = vol[..., 0]
        mk = mk[..., 0]
    if vol.ndim != 3 or mk.ndim != 3:
        raise ValueError("Only 3D (or 4D with time first) volumes supported for overlay")
    mid = vol.shape[-1] // 2
    sl_vol = vol[..., mid]
    sl_mask = mk[..., mid]
    sl_v = (sl_vol - float(np.min(sl_vol))) / (float(np.max(sl_vol) - float(np.min(sl_vol))) + 1e-8)
    rgb = np.stack([sl_v, sl_v, sl_v], axis=-1)
    overlay = np.zeros((*sl_v.shape, 4), dtype=np.float32)
    overlay[..., :3] = rgb
    overlay[..., 3] = 0.0
    overlay[sl_mask > 0, 0] = 1.0
    overlay[sl_mask > 0, 3] = 0.45
    png = PILImage.fromarray((np.clip(overlay, 0, 1) * 255).astype(np.uint8), mode="RGBA")
    png_buf = io.BytesIO()
    png.save(png_buf, format="PNG")
    png_bytes = png_buf.getvalue()

    meta = {
        "engine": "classical_otsu_nifti",
        "threshold": thr,
        "model": model_name,
        "version": model_version,
        "slice_index": int(mid),
    }
    return mask_bytes, png_bytes, meta


def store_results(job_id: uuid.UUID, mask_bytes: bytes, png_bytes: bytes) -> Tuple[str, str]:
    mid = str(job_id)
    mk = f"results/{mid}/mask.nii.gz"
    pk = f"results/{mid}/overlay.png"
    upload_bytes(mk, mask_bytes, "application/gzip")
    upload_bytes(pk, png_bytes, "image/png")
    return mk, pk
