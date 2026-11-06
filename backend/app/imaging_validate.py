"""
Validate medical imaging files from bytes — do not trust file extensions alone.
"""
from __future__ import annotations

import io
import json
import tempfile
import zipfile
from pathlib import Path
from dataclasses import dataclass
from typing import Any, Optional

import nibabel as nib
import numpy as np
import pydicom
from pydicom.errors import InvalidDicomError


class ValidationError(Exception):
    pass


MAX_HEADER_BYTES = 32 * 1024 * 1024  # read headers only for DICOM where possible


@dataclass
class NiftiInfo:
    shape: tuple[int, ...]
    zooms: tuple[float, ...]
    affine: list[list[float]]
    qform_code: int
    sform_code: int


def _nifti_magic_ok(d: bytes) -> bool:
    if len(d) < 348:
        return False
    # NIfTI-1
    if d[343:348] in (b"n+1\0", b"ni1\0"):
        return True
    # NIfTI-2 (magic at bytes 4–7 after 4-byte struct fields)
    if len(d) >= 8 and d[4:8] in (b"n+2\0", b"ni2\0"):
        return True
    return False


def _looks_like_nifti_magic(buf: bytes) -> bool:
    if _nifti_magic_ok(buf):
        return True
    # gzip: decompress and re-check (nibabel often writes .nii.gz)
    if buf[:2] == b"\x1f\x8b":
        import gzip

        try:
            d = gzip.decompress(buf[: min(len(buf), 50 * 1024 * 1024)])
            return _nifti_magic_ok(d)
        except Exception:
            return False
    return False


def validate_nifti_bytes(data: bytes) -> NiftiInfo:
    if len(data) < 100:
        raise ValidationError("File too small to be NIfTI")
    # nibabel 5.x load() expects a path — decompress gzip to raw .nii bytes first
    if data[:2] == b"\x1f\x8b":
        import gzip

        try:
            data = gzip.decompress(data)
        except Exception as e:
            raise ValidationError(f"Gzip decompress failed: {e}") from e
    path = ""
    try:
        with tempfile.NamedTemporaryFile(suffix=".nii", delete=False) as tmp:
            tmp.write(data)
            path = tmp.name
        img = nib.load(path)  # type: ignore[no-untyped-call]
    except Exception as e:
        raise ValidationError(f"NIfTI load failed: {e}") from e
    finally:
        if path:
            Path(path).unlink(missing_ok=True)
    shape = tuple(int(x) for x in img.shape)
    zoom_hdr = img.header.get_zooms()
    zooms = tuple(float(x) for x in zoom_hdr[: len(shape)]) if zoom_hdr is not None else tuple()
    affine = img.affine.tolist()
    hdr = img.header
    qc = int(hdr["qform_code"]) if "qform_code" in hdr else 0
    sc = int(hdr["sform_code"]) if "sform_code" in hdr else 0
    return NiftiInfo(shape=shape, zooms=zooms, affine=affine, qform_code=qc, sform_code=sc)


def validate_dicom_bytes(data: bytes) -> dict[str, Any]:
    if len(data) < 132:
        raise ValidationError("File too small to be DICOM")
    # DICOM preamble + DICM
    if data[128:132] != b"DICM":
        # Some files omit preamble; try direct parse
        pass
    try:
        ds = pydicom.dcmread(io.BytesIO(data), stop_before_pixels=True, force=True)
    except InvalidDicomError as e:
        raise ValidationError(f"Invalid DICOM: {e}") from e
    except Exception as e:
        raise ValidationError(f"DICOM parse error: {e}") from e

    modality = str(getattr(ds, "Modality", "") or "")
    sop_class = str(getattr(ds, "SOPClassUID", "") or "")
    study_uid = str(getattr(ds, "StudyInstanceUID", "") or "")
    series_uid = str(getattr(ds, "SeriesInstanceUID", "") or "")
    instance_uid = str(getattr(ds, "SOPInstanceUID", "") or "")
    body_part = str(getattr(ds, "BodyPartExamined", "") or "")
    rows = int(getattr(ds, "Rows", 0) or 0)
    cols = int(getattr(ds, "Columns", 0) or 0)
    num_frames = int(getattr(ds, "NumberOfFrames", 0) or 0)
    return {
        "modality": modality,
        "sop_class_uid": sop_class,
        "study_instance_uid": study_uid,
        "series_instance_uid": series_uid,
        "sop_instance_uid": instance_uid,
        "body_part_examined": body_part,
        "rows": rows,
        "columns": cols,
        "number_of_frames": num_frames,
    }


def validate_zip_not_evil(z: zipfile.ZipFile, max_uncompressed: int = 2 * 1024**3) -> None:
    total = 0
    for i in z.infolist():
        if i.filename.startswith("/") or ".." in i.filename:
            raise ValidationError("Zip path traversal not allowed")
        total += i.file_size
        if total > max_uncompressed:
            raise ValidationError("Zip uncompressed size too large")


def sniff_upload_kind(filename: str, data: bytes) -> str:
    fn = filename.lower()
    if fn.endswith((".nii", ".nii.gz")):
        return "nifti"
    if fn.endswith(".zip"):
        return "zip"
    if fn.endswith(".dcm") or fn.endswith(".dicom"):
        return "dicom"
    # sniff content
    if data[128:132] == b"DICM" or (len(data) > 8 and data[0:4] in (b"\x02\x00\x00\x00", b"\x08\x00\x00\x00")):
        return "dicom"
    if _looks_like_nifti_magic(data):
        return "nifti"
    if data[:2] == b"PK":
        return "zip"
    raise ValidationError("Unsupported or unrecognized file type (do not rely on extension alone).")


def series_dims_json_from_dicom_meta(meta: dict[str, Any]) -> str:
    return json.dumps(
        {
            "rows": meta.get("rows"),
            "columns": meta.get("columns"),
            "number_of_frames": meta.get("number_of_frames"),
        }
    )
