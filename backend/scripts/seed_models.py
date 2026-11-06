"""
Load model registry definitions from JSON file (no downloads).
"""
import asyncio
import json
import os
import uuid
from pathlib import Path

from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models import ModelRegistry

REGISTRY_PATH = Path(__file__).resolve().parent.parent / "registry" / "default_models.json"


async def run() -> None:
    path = Path(os.environ.get("MODEL_REGISTRY_JSON", str(REGISTRY_PATH)))
    if not path.exists():
        return
    data = json.loads(path.read_text())
    async with AsyncSessionLocal() as db:
        for item in data:
            ext_id = item.get("id")
            r = await db.execute(select(ModelRegistry).where(ModelRegistry.name == item["name"]))
            if r.scalar_one_or_none():
                continue
            inp = item.get("input_requirements") or {}
            engine = inp.get("inference_engine") or ""
            has_weights = bool(item.get("weights_sha256"))
            can_activate = bool(item.get("is_active")) and (has_weights or engine == "classical_otsu_nifti")
            m = ModelRegistry(
                id=uuid.uuid5(uuid.NAMESPACE_DNS, f"medimage-model-{ext_id}"),
                name=item["name"],
                version=item["version"],
                source_url=item.get("source_url"),
                license_text=item.get("license_text"),
                weights_sha256=item.get("weights_sha256"),
                allowed_modalities=json.dumps(item.get("allowed_modalities", [])),
                allowed_body_parts=json.dumps(item.get("allowed_body_parts", [])),
                input_requirements_json=json.dumps(inp),
                output_classes_json=json.dumps(item.get("output_classes", [])),
                preprocess_config_json=json.dumps(item.get("preprocess", {})),
                constraints_text=item.get("constraints_text"),
                bundle_path=item.get("bundle_path"),
                is_active=can_activate,
            )
            db.add(m)
        await db.commit()


if __name__ == "__main__":
    asyncio.run(run())
