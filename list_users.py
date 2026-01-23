#!/usr/bin/env python3
"""Script to list all users in database"""
import asyncio
from app.database.session import get_db
from app.models.users import User
from sqlmodel import select


async def list_users():
    """List all users in the database"""
    async for db in get_db():
        result = await db.execute(select(User))
        users = result.scalars().all()

        if not users:
            print("❌ No users found in database")
            return

        print(f"✅ Found {len(users)} user(s):")
        print("=" * 80)
        for user in users:
            print(f"ID: {user.id}")
            print(f"Email: {user.email}")
            print(f"Username: {user.username}")
            print(f"First Name: {user.first_name}")
            print(f"Last Name: {user.last_name}")
            print(f"Is Active: {user.is_active}")
            print(f"Is Staff: {user.is_staff}")
            print(f"Is Superuser: {user.is_superuser}")
            print(f"Date Joined: {user.date_joined}")
            print("-" * 80)


if __name__ == "__main__":
    asyncio.run(list_users())
