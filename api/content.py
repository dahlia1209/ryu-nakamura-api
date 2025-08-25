from fastapi import APIRouter, HTTPException, Query, Path, Body,Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List, Optional
from models.content import Content,PreviewContent
from managers.auth_manager import (
    JWTPayload,
    get_current_user,
    requires_scope,
    is_token_id_matching,
)
from managers.blob_manager import BLOBConnectionManager
from repository import content as content_repo
from datetime import datetime
import uuid
from models.query import QueryFilter
from bs4 import BeautifulSoup
import os
import json

router = APIRouter()
security = HTTPBearer()


@router.get("/contents", response_model=List[Content], tags=["contents"])
async def list_contents(
    category: Optional[str] = Query(None, description="Filter by category"),
    title_no: Optional[int] = Query(None, description="Filter by title_no"),
    limit: int = Query(50, description="Maximum number of contents to return"),
    token_data: JWTPayload = Depends(requires_scope("contents.read")),
):
    """コンテンツの一覧を取得する"""
    qf = QueryFilter()
    qf.add_filter(f"category eq @category", {"category": category})
    qf.add_filter(f"title_no eq @title_no", {"title_no": title_no})
    contents = content_repo.query_contents(qf, limit)
    return contents


@router.post("/contents", response_model=Content, status_code=201, tags=["contents"])
async def create_content(
    content_item: Content = Body(..., description="Content to create"),
    token_data: JWTPayload = Depends(requires_scope("contents.write")),
):
    """新しいコンテンツを作成する"""
    
    # サブ関数
    def check_existing_content():
        qf = QueryFilter()
        qf.add_filter(f"RowKey eq @content_id", {"content_id": content_item.id})
        qf.add_filter(
            f"title_no eq @title_no", {"title_no": content_item.title_no}, "or"
        )
        contents = content_repo.query_contents(qf)
        if contents:
            return True
        return False
    
    def update_content(content_item: Content):
        soup = BeautifulSoup(content_item.content_html, 'html.parser')
        content_item.content_html = str(soup)
        content_item.content_text = soup.get_text()

    # メイン処理
    existing = check_existing_content()
    update_content(content_item)
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"ID '{content_item.id}' または title_no '{content_item.title_no}' を持つリソースが既に存在します",
        )
    
    success = content_repo.create_content(content_item)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to create content")

    return content_item


@router.get("/contents/{content_id}", response_model=Content, tags=["contents"])
async def get_content_by_id(
    content_id: uuid.UUID = Path(..., description="Content ID to get"),
    token_data: JWTPayload = Depends(requires_scope("contents.read")),
):
    """指定されたIDのコンテンツを取得する"""
    try:
        content = content_repo.get_content(str(content_id))
        return content

    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail=f"指定されたID {content_id} のコンテンツが見つかりません",
        )


@router.put("/contents/{content_id}", response_model=Content, tags=["contents"])
async def update_content(
    content_id: uuid.UUID = Path(..., description="Content ID to update"),
    content_item: Content = Body(..., description="Updated content data"),
    token_data: JWTPayload = Depends(requires_scope("contents.write")),
):
    """指定されたIDのコンテンツを更新する"""

    # サブ関数
    def get_existing_content():
        qf = QueryFilter()
        qf.add_filter(f"RowKey eq @content_id", {"content_id": content_item.id})
        contents = content_repo.query_contents(qf)
        return contents

    # メイン処理
    if content_id != content_item.id:
        raise HTTPException(
            status_code=400,
            detail=f"パラメータのID {content_id} と更新するコンテンツのID {content_item.id} が一致しません。",
        )
    contents = get_existing_content()
    if not contents:
        raise HTTPException(
            status_code=404,
            detail=f"指定されたID {content_id} のコンテンツが見つかりません",
        )
    success = content_repo.update_content(content_item)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to create content")

    return content_item


@router.delete("/contents/{content_id}", status_code=204, tags=["contents"])
async def delete_content_item(
    content_id: uuid.UUID = Path(..., description="Content ID to delete"),
    token_data: JWTPayload = Depends(requires_scope("contents.write")),
):
    """指定されたIDのコンテンツを削除する"""

    # サブ関数
    def get_existing_content():
        qf = QueryFilter()
        qf.add_filter(f"RowKey eq @content_id", {"content_id": content_id})
        contents = content_repo.query_contents(qf)
        return contents

    # メイン処理
    contents = get_existing_content()
    if not contents:
        raise HTTPException(
            status_code=404, detail="指定されたIDのコンテンツが見つかりません"
        )
    success = content_repo.delete_content(contents[0])
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete content")

    return contents[0]


@router.put("/contents/process/generate_contents_list", response_model=List[PreviewContent], tags=["contents"])
async def generate_contents_list(
    token_data: JWTPayload = Depends(requires_scope("contents.read")),
):
    """コンテンツ一覧ファイルを生成する"""
    try:
        qf = QueryFilter()
        contents = content_repo.query_contents(qf)

        manager=BLOBConnectionManager()
        contents_list = json.dumps([json.loads(c.to_preview().model_dump_json()) for c in contents])
        
        blob_client = manager.client.get_blob_client(
                container=os.getenv("AZURE_BLOB_CONTAINER_NAME","root"), 
                blob=os.getenv("CONTENT_LIST_FILE_NAME"), 
        )
            
        blob_client.upload_blob(contents_list, overwrite=True)
        return [c.to_preview().model_dump() for c in contents]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"コンテンツ一覧ファイル生成に失敗しました:{e}")

    
    