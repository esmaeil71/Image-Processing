import json
import uuid

from app.api.v1.jobs import _model_matches_series
from app.models import ModelRegistry, Series


def test_classical_model_requires_nifti_series():
    m = ModelRegistry(
        id=uuid.uuid4(),
        name="test",
        version="1",
        is_active=True,
        weights_sha256=None,
        allowed_modalities=json.dumps(["CT"]),
        allowed_body_parts=json.dumps([""]),
        input_requirements_json=json.dumps({"inference_engine": "classical_otsu_nifti"}),
    )
    ser_dicom = Series(
        id=uuid.uuid4(),
        study_id=uuid.uuid4(),
        storage_type="dicom_orthanc",
        modality="CT",
        dims_json=json.dumps({"shape": [10, 10, 10]}),
    )
    ok, reason = _model_matches_series(m, ser_dicom)
    assert ok is False
    assert "NIfTI" in reason

    ser_nii = Series(
        id=uuid.uuid4(),
        study_id=uuid.uuid4(),
        storage_type="nifti_s3",
        modality="CT",
        dims_json=json.dumps({"shape": [10, 12, 8]}),
    )
    ok2, _ = _model_matches_series(m, ser_nii)
    assert ok2 is True
