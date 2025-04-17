from fastapi import APIRouter, HTTPException, Query, Path, Body, Depends
from typing import List, Optional
from models.user import User
from repository import user
from datetime import datetime
from api.auth import get_current_user, requires_scope

router = APIRouter()

@router.get("/users", response_model=List[User], tags=["users"])
async def list_users(
    limit: int = Query(50, description="Maximum number of users to return"),
    # token_data = Depends(requires_scope("users.read"))
):
    """ユーザーの一覧を取得する"""
    users = user.get_users(limit)
    return users

@router.get("/users/{user_id}", response_model=User, tags=["users"])
async def get_user(
    user_id: str = Path(..., description="User ID to retrieve"),
    # token_data = Depends(requires_scope("users.read"))
):
    """指定されたIDのユーザーを取得する"""
    user_item = user.get_user_by_id(user_id)
    if not user_item:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user_item


@router.get("/users/email/{email}", response_model=User, tags=["users"])
async def get_user_by_email(
    email: str = Path(..., description="Email to retrieve"),
    # token_data = Depends(requires_scope("users.read"))
):
    """メールアドレスでユーザーを取得する"""
    user_item = user.get_user_by_email(email)
    if not user_item:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user_item

@router.post("/users", response_model=User, status_code=201, tags=["users"])
async def create_user_item(
    user_item: User = Body(..., description="User to create"),
    # token_data = Depends(requires_scope("users.write"))
):
    """新しいユーザーを作成する"""
    # 認証IDが既に存在するか確認
    existing_auth_user = user.get_user_by_id(user_item.id)
    if existing_auth_user:
        raise HTTPException(status_code=400, detail="Auth ID already registered")
    
    success = user.create_user(user_item)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to create user")
    
    return user_item

@router.put("/users/{user_id}", response_model=User, tags=["users"])
async def update_user_item(
    user_id: str = Path(..., description="User ID to update"),
    user_item: User = Body(..., description="Updated user data"),
    # token_data = Depends(requires_scope("users.write"))
):
    """指定されたIDのユーザーを更新する"""
    # パスのIDとボディのIDが一致することを確認
    if user_id != user_item.id:
        raise HTTPException(status_code=400, detail="Path ID and body ID do not match")
    
    # 更新前に存在確認
    existing = user.get_user_by_id(user_id)
    if not existing:
        raise HTTPException(status_code=404, detail="User not found")
    
    # メールアドレスが変更された場合、重複がないか確認
    if existing.email != user_item.email:
        email_user = user.get_user_by_email(user_item.email)
        if email_user and email_user.id != user_id:
            raise HTTPException(status_code=400, detail="Email already registered to another user")
    
    success = user.update_user(user_item)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update user")
    
    return user_item

@router.patch("/users/{user_id}/login", response_model=User, tags=["users"])
async def update_user_login_time(
    user_id: str = Path(..., description="User ID to update login time"),
    # token_data = Depends(requires_scope("users.write"))
):
    """ユーザーの最終ログイン時間を更新する"""
    # ユーザーの存在を確認
    existing = user.get_user_by_id(user_id)
    if not existing:
        raise HTTPException(status_code=404, detail="User not found")
    
    # 最終ログイン時間を更新
    success = user.update_user_login(user_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update login time")
    
    # 更新されたユーザーを返す
    updated_user = user.get_user_by_id(user_id)
    return updated_user

@router.delete("/users/{user_id}", status_code=204, tags=["users"])
async def delete_user_item(
    user_id: str = Path(..., description="User ID to delete"),
    # token_data = Depends(requires_scope("users.write"))
):
    """指定されたIDのユーザーを削除する"""
    success = user.delete_user(user_id)
    if not success:
        raise HTTPException(status_code=404, detail="User not found or could not be deleted")
    
    return None