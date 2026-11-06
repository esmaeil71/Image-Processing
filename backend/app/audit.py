import json
import uuid
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog


async def audit_log(
    db: AsyncSession,
    *,
    user_id: Optional[uuid.UUID],
    action: str,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    detail_safe: Optional[dict[str, Any]] = None,
) -> None:
    """Persist audit entry without PHI — only opaque IDs and safe fields."""
    safe: Optional[str] = None
    if detail_safe is not None:
        safe = json.dumps(detail_safe, default=str)[:8000]
    row = AuditLog(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        detail_safe=safe,
    )
    db.add(row)
