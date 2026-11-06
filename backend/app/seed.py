"""
Seed initial admin user from environment (optional).
"""
import asyncio
import os

from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models import User
from app.security import get_password_hash


async def seed_admin() -> None:
    email = os.environ.get("ADMIN_EMAIL")
    password = os.environ.get("ADMIN_PASSWORD")
    if not email or not password:
        return
    async with AsyncSessionLocal() as db:
        r = await db.execute(select(User).where(User.email == email))
        if r.scalar_one_or_none():
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
