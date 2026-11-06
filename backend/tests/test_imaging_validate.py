import tempfile
from pathlib import Path

import numpy as np
import nibabel as nib

from app.imaging_validate import ValidationError, validate_nifti_bytes, sniff_upload_kind


def test_sniff_rejects_extension_only():
    try:
        sniff_upload_kind("data.txt", b"not medical data" * 10)
    except ValidationError:
        return
    raise AssertionError("expected ValidationError")


def test_nifti_roundtrip_geometry():
    data = np.random.rand(12, 16, 14).astype(np.float32)
    affine = np.eye(4)
    zooms = (0.8, 0.8, 2.5)
    img = nib.Nifti1Image(data, affine)
    img.header.set_zooms(zooms)
    with tempfile.NamedTemporaryFile(suffix=".nii.gz", delete=False) as f:
        path = f.name
    nib.save(img, path)
    raw = Path(path).read_bytes()
    Path(path).unlink(missing_ok=True)
    info = validate_nifti_bytes(raw)
    assert info.shape == data.shape
    assert len(info.zooms) == len(info.shape)


def test_nifti_mask_shape_matches():
    data = np.random.rand(10, 12, 8).astype(np.float32)
    img = nib.Nifti1Image(data, np.eye(4))
    with tempfile.NamedTemporaryFile(suffix=".nii.gz", delete=False) as f:
        path = f.name
    nib.save(img, path)
    raw = Path(path).read_bytes()
    Path(path).unlink(missing_ok=True)
    vi = validate_nifti_bytes(raw)
    assert vi.shape == tuple(data.shape)
