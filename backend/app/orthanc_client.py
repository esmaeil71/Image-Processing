from typing import Any, Optional

import httpx

from app.config import settings


def _auth() -> tuple[str, str]:
    return settings.orthanc_user, settings.orthanc_password


async def orthanc_post_instances(data: bytes) -> dict[str, Any]:
    url = f"{settings.orthanc_url.rstrip('/')}/instances"
    async with httpx.AsyncClient(timeout=120.0) as client:
        r = await client.post(url, content=data, auth=_auth())
        r.raise_for_status()
        return r.json()


async def orthanc_get_study(study_id: str) -> dict[str, Any]:
    url = f"{settings.orthanc_url.rstrip('/')}/studies/{study_id}"
    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await client.get(url, auth=_auth())
        r.raise_for_status()
        return r.json()


async def orthanc_get_series(series_id: str) -> dict[str, Any]:
    url = f"{settings.orthanc_url.rstrip('/')}/series/{series_id}"
    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await client.get(url, auth=_auth())
        r.raise_for_status()
        return r.json()


async def orthanc_find_study_by_uid(study_instance_uid: str) -> Optional[str]:
    """Return Orthanc internal study ID for DICOM StudyInstanceUID."""
    url = f"{settings.orthanc_url.rstrip('/')}/tools/find"
    payload = {"Level": "Study", "Query": {"StudyInstanceUID": study_instance_uid}}
    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await client.post(url, json=payload, auth=_auth())
        r.raise_for_status()
        ids = r.json()
        if ids and isinstance(ids, list):
            return str(ids[0])
    return None
