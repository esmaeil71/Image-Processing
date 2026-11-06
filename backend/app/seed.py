"""
Seed initial admin user from environment (optional).
"""
import asyncio
import os

from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models import User
from app.security import get_password_hash


def _env_truthy(name: str, default: str = "true") -> bool:
    return os.environ.get(name, default).strip().lower() in ("1", "true", "yes", "on")


async def seed_admin() -> None:
    email = os.environ.get("ADMIN_EMAIL")
    password = os.environ.get("ADMIN_PASSWORD")
    if not email or not password:
        return
    sync_password = _env_truthy("ADMIN_SYNC_PASSWORD", "true")
    async with AsyncSessionLocal() as db:
        r = await db.execute(select(User).where(User.email == email))
        existing = r.scalar_one_or_none()
        if existing:
            if sync_password:
                existing.hashed_password = get_password_hash(password)
                await db.commit()
            return
        u = User(
            email=email,
            hashed_password=get_password_hash(password),
            role="admin",
            full_name="Administrator",
        )
        db.add(u)
        await db.commit()


if __name__ == "__main__":
    asyncio.run(seed_admin())
