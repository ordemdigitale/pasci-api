#!/usr/bin/env python3
"""Script to test login"""
import asyncio
from app.database.session import get_db
from app.models.users import User
from app.core.security import verify_password
from sqlmodel import select


async def test_login():
    """Test login with admin credentials"""
    username = "admin"
    password = "admin123"

    async for db in get_db():
        # Find user
        result = await db.execute(
            select(User).where(
                (User.email == username) | (User.username == username)
            )
        )
        user = result.scalar_one_or_none()

        if not user:
            print(f"❌ User '{username}' not found")
            return

        print(f"✅ User found: {user.email}")
        print(f"   Username: {user.username}")
        print(f"   Is Active: {user.is_active}")
        print(f"   Is Staff: {user.is_staff}")
        print(f"   Is Superuser: {user.is_superuser}")
        print()

        # Test password
        if verify_password(password, user.password):
            print(f"✅ Password is correct!")
            print()
            print("=" * 60)
            print("🎉 Login credentials are valid!")
            print("=" * 60)
            print(f"📧 Email: {user.email}")
            print(f"👤 Username: {user.username}")
            print("🔑 Password: admin123")
            print("=" * 60)
        else:
            print(f"❌ Password is incorrect")


if __name__ == "__main__":
    asyncio.run(test_login())
