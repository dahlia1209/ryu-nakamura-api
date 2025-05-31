from fastapi import APIRouter, HTTPException, Query, Path, Body, Depends,Header,Request
from typing import List, Optional,Literal
from models.user import User
from managers.auth_manager import  JWTPayload,get_current_user,requires_scope,is_token_oid_matching
from repository import user as user_repo
from datetime import datetime
from models.query import QueryFilter
import uuid


router = APIRouter()

@router.get("/me", response_model=User, tags=["users"])
async def get_current_user_profile(
    token_data: JWTPayload = Depends(get_current_user)
):
    """ログインユーザー自身の情報を取得する"""
    user_id = token_data.get("sub")
    if not user_id:
        raise HTTPException(status_code=400, detail="ユーザーIDが見つかりません")
    
    try:
        user = user_repo.get_user(user_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail="ユーザーが見つかりません")
    
    return user

@router.get("/users", response_model=List[User], tags=["users"])
async def list_users(
    limit: int = Query(50, description="Maximum number of users to return"),
    token_data: JWTPayload = Depends(requires_scope("users.list"))
):
    """ユーザーの一覧を取得する"""
    qf=QueryFilter()
    users = user_repo.query_users(qf,limit)
    return users

@router.post("/users", response_model=User, status_code=201, tags=["users"])
async def create_user_item(
    user_item: User = Body(..., description="User to create"),
    token_data: JWTPayload = Depends(requires_scope("users.write"))
):
    """新しいユーザーを作成する"""
    if not is_token_oid_matching(token_data,user_item.id):
        raise HTTPException(
            status_code=403,
            detail=f"user_item id {user_item.id} とトークンのsubが一致しません"
        )
    # 既存ユーザーの確認
    try:
        existing_user = user_repo.get_user(str(user_item.id))
        if existing_user:
            raise HTTPException(
                status_code=409,
                detail=f"ID '{user_item.id}' を持つリソースが既に存在します"
            )
    except ValueError:
        pass
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"ユーザー検索中にエラーが発生しました: {str(e)}"
        )
    
    # ユーザー作成
    try:
        user_repo.create_user(user_item)
        return user_item
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"ユーザー作成中にエラーが発生しました: {str(e)}"
        )

@router.get("/users/{user_id}", response_model=User, tags=["users"])
async def get_user(
    user_id: uuid.UUID = Path(..., description="User ID to retrieve"),
    token_data: JWTPayload  = Depends(requires_scope("users.read"))
):
    """指定されたIDのユーザーを取得する"""
    if not is_token_oid_matching(token_data,user_id):
        raise HTTPException(
            status_code=403,
            detail=f"user_id {user_id} とトークンのsubが一致しません"
        )
    try:
        user = user_repo.get_user(str(user_id))
        return user
    
    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail=f"指定されたID {user_id} のユーザーが見つかりません"
        )


@router.put("/users/{user_id}", response_model=User, tags=["users"])
async def update_user_item(
    user_id: uuid.UUID = Path(..., description="User ID to update"),
    user_item: User = Body(..., description="Updated user data"),
    mode:Literal['update','upsert']= Query('update', description="Operation to upsert or update"),
    token_data: JWTPayload  = Depends(requires_scope("users.write"))
):
    """指定されたIDのコンテンツを更新する"""
    if not is_token_oid_matching(token_data,user_id):
            raise HTTPException(
                status_code=403,
                detail=f"user_id {user_id} とトークンのoidが一致しません"
            )
    try:
        user_repo.update_user(user_item)
    
    except ValueError as e:
        if mode=="upsert":
            user_repo.create_user(user_item)
        else:
            raise HTTPException(
                status_code=404,
                detail=f"指定されたID {user_id} のコンテンツが見つかりません"
            )
    except Exception as e:
        raise HTTPException(
            status_code=500,
                detail=f"Error: {e} "
        )
        
    return user_item
    

@router.delete("/users/{user_id}", status_code=204, tags=["users"])
async def delete_user_item(
    user_id: uuid.UUID = Path(..., description="User ID to delete"),
    token_data: JWTPayload  = Depends(requires_scope("users.write"))
):
    """指定されたIDのユーザーを削除する"""
    if not is_token_oid_matching(token_data,user_id):
            raise HTTPException(
                status_code=403,
                detail=f"user_id {user_id} とトークンのsubが一致しません"
            )
    try:
        user = user_repo.get_user(str(user_id))
        user_repo.delete_user(str(user_id))
    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail=f"指定されたID {user_id} のコンテンツが見つかりません"
        )
        
    return True
