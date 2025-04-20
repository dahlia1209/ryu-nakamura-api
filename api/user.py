from fastapi import APIRouter, HTTPException, Query, Path, Body, Depends
from typing import List, Optional,Literal
from models.user import User
from repository import user as user_repos
from datetime import datetime
from api.auth import get_current_user, requires_scope
from models.query import QueryFilter
import uuid

router = APIRouter()

@router.get("/users", response_model=List[User], tags=["users"])
async def list_users(
    limit: int = Query(50, description="Maximum number of users to return"),
    # token_data = Depends(requires_scope("users.read"))
):
    """ユーザーの一覧を取得する"""
    qf=QueryFilter()
    users = user_repos.query_users(qf,limit)
    return users

@router.post("/users", response_model=User, status_code=201, tags=["users"])
async def create_user_item(
    user_item: User = Body(..., description="User to create"),
    
    # token_data = Depends(requires_scope("users.write"))
):
    """新しいユーザーを作成する"""
    #サブ関数
    def get_existing_user():
        qf=QueryFilter()
        qf.add_filter(f"RowKey eq @user_id",{"user_id":user_item.id})
        users = user_repos.query_users(qf)
        return users
            
    #メイン処理
    users=get_existing_user()
    if users:
        raise HTTPException(
            status_code=409,
            detail=f"ID '{user_item.id}'  を持つリソースが既に存在します"
        )
    success = success = user_repos.create_user(user_item)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to create user")
    return user_item


@router.get("/users/{user_id}", response_model=User, tags=["users"])
async def get_user(
    user_id: str = Path(..., description="User ID to retrieve"),
    # token_data = Depends(requires_scope("users.read"))
):
    """指定されたIDのユーザーを取得する"""
    qf=QueryFilter()
    qf.add_filter(f"RowKey eq @user_id",{"user_id":user_id})
    users = user_repos.query_users(qf)
    if not user_repos:
        raise HTTPException(
            status_code=404,
            detail="指定されたIDのコンテンツが見つかりません"
        )
    return users[0]


@router.put("/users/{user_id}", response_model=User, tags=["users"])
async def update_user_item(
    user_id: uuid.UUID = Path(..., description="User ID to update"),
    user_item: User = Body(..., description="Updated user data"),
    mode:Literal['update','upsert']= Query('update', description="Operation to upsert or update"),
    # token_data = Depends(requires_scope("users.write"))
):
    """指定されたIDのコンテンツを更新する"""
    #サブ関数
    def get_existing_user():
        qf=QueryFilter()
        qf.add_filter(f"RowKey eq @user_id",{"user_id":user_item.id})
        users = user_repos.query_users(qf)
        return users
            
    #メイン処理
    if user_id!=user_item.id:
        raise HTTPException(
            status_code=400,
            detail=f"パラメータのID {user_id} と更新するコンテンツのID {user_item.id} が一致しません。"
        )
    
    users=get_existing_user()
    if not users:
        if mode=="update":
            raise HTTPException(
                status_code=404,
                detail=f"指定されたID {user_id} のコンテンツが見つかりません"
            )
        elif mode=="upsert":
            success = user_repos.create_user(user_item)
        else:
            raise HTTPException(
                status_code=400,
                detail=f"mode {mode} が正しくありません。"
            )
    else:
        user_item.created_at=None
        success = user_repos.update_user(user_item)
    if not success:
        raise HTTPException(status_code=500, detail=f"Failed to {mode} user")
    
    return user_item

@router.delete("/users/{user_id}", status_code=204, tags=["users"])
async def delete_user_item(
    user_id: str = Path(..., description="User ID to delete"),
    # token_data = Depends(requires_scope("users.write"))
):
    """指定されたIDのユーザーを削除する"""
    #サブ関数
    def get_existing_user():
        qf=QueryFilter()
        qf.add_filter(f"RowKey eq @user_id",{"user_id":user_id})
        users = user_repos.query_users(qf)
        return users
        
    #メイン処理
    users=get_existing_user()
    if not users:
        raise HTTPException(
            status_code=404,
            detail="指定されたIDのコンテンツが見つかりません"
        )
    success = user_repos.delete_user(users[0])
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete user")
    
    return users[0]
