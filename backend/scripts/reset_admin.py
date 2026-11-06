#!/usr/bin/env python3
"""
One-shot: (re)create admin user from ADMIN_EMAIL / ADMIN_PASSWORD in environment.
Run inside backend container:
  docker compose exec backend python /app/scripts/reset_admin.py
"""
import asyncio
import os
import sys

from sqlalchemy import select

sys.path.insert(0, "/app")

from app.database import AsyncSessionLocal  # noqa: E402
from app.models import User  # noqa: E402
from app.security import get_password_hash  # noqa: E402


async def main() -> None:
    email = os.environ.get("ADMIN_EMAIL", "").strip()
    password = os.environ.get("ADMIN_PASSWORD", "")
    if not email or not password:
        print("Set ADMIN_EMAIL and ADMIN_PASSWORD in the environment.", file=sys.stderr)
        sys.exit(1)
    async with AsyncSessionLocal() as db:
        r = await db.execute(select(User).where(User.email == email))
        u = r.scalar_one_or_none()
        if u:
            u.hashed_password = get_password_hash(password)
            u.role = "admin"
            u.is_active = True
            print(f"Updated password for {email}")
        else:
            db.add(
                User(
                    email=email,
                    hashed_password=get_password_hash(password),
                    role="admin",
                    full_name="Administrator",
                )
            )
            print(f"Created admin {email}")
        await db.commit()


if __name__ == "__main__":
    asyncio.run(main())
