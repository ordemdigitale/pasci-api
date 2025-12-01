# app/api/v1/endpoints/users.py
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from sqlmodel import select

users_router = APIRouter()

@users_router.get("/")
async def get_users():
    return {"message": "Get all users"}


@users_router.get("/{user_id}")
async def get_user(user_id: int):
    return {"message": f"Get user with ID {user_id}"}


@users_router.post("/")
async def create_user():
    return {"message": "Create user"}


@users_router.put("/{user_id}")
async def update_user(user_id: int):
    return {"message": f"Update user {user_id}"}


@users_router.delete("/{user_id}")
async def delete_user(user_id: int):
    return {"message": f"Delete user {user_id}"}