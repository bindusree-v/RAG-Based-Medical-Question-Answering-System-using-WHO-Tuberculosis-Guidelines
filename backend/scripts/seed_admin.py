"""
MediRAG AI – Admin Seed Script
Creates the initial admin user on first startup.
Run once: python scripts/seed_admin.py
"""

import asyncio
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.database import AsyncSessionLocal, init_db, User
from app.utils.security import hash_password
from sqlalchemy import select


async def seed():
    await init_db()

    username = os.getenv("ADMIN_USERNAME", "admin")
    email = os.getenv("ADMIN_EMAIL", "admin@medirag.local")
    password = os.getenv("ADMIN_PASSWORD", "ChangeMe123!")

    async with AsyncSessionLocal() as session:
        existing = await session.execute(
            select(User).where(User.username == username)
        )
        if existing.scalar_one_or_none():
            print(f"Admin user '{username}' already exists.")
            return

        admin = User(
            username=username,
            email=email,
            hashed_password=hash_password(password),
            role="admin",
            is_active=True,
        )
        session.add(admin)
        await session.commit()
        print(f"Admin user '{username}' created successfully.")
        print(f"  Email: {email}")
        print("  IMPORTANT: Change the default password immediately!")


if __name__ == "__main__":
    asyncio.run(seed())
