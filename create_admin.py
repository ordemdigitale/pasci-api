#!/usr/bin/env python3
"""Script to create default admin user"""
import asyncio
from app.database.session import get_db
from app.models.users import User
from app.core.security import get_password_hash
from sqlmodel import select


async def create_admin():
    """Create default admin user"""
    async for db in get_db():
        # Check if admin already exists
        result = await db.execute(
            select(User).where(
                (User.email == "admin@pasci.dz") | (User.username == "admin")
            )
        )
        existing_user = result.scalar_one_or_none()

        if existing_user:
            print(f"✅ Admin user already exists: {existing_user.email}")
            return

        # Create admin user
        hashed_password = get_password_hash("admin123")
        admin = User(
            email="admin@pasci.dz",
            username="admin",
            password=hashed_password,
            first_name="Admin",
            last_name="PASCI",
            is_active=True,
            is_staff=True,
            is_superuser=True,
        )

        db.add(admin)
        await db.commit()
        await db.refresh(admin)

        print("=" * 60)
        print("✅ Admin user created successfully!")
        print("=" * 60)
        print(f"📧 Email: {admin.email}")
        print(f"👤 Username: {admin.username}")
        print("🔑 Password: admin123")
        print("=" * 60)
        print("⚠️  Please change the password after first login!")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(create_admin())
