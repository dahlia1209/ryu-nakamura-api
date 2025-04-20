from fastapi import APIRouter, HTTPException, Query, Path, Body
from typing import List, Optional
from models.content import Content
from repository import content
from datetime import datetime
import uuid
from models.query import QueryFilter

router = APIRouter()

@router.get("/contents", 
            response_model=List[Content], 
            tags=["contents"])
async def list_contents(
    category: Optional[str] = Query(None, description="Filter by category"),
    title_no: Optional[int] = Query(None, description="Filter by title_no"),
    limit: int = Query(50, description="Maximum number of contents to return")
):
    """コンテンツの一覧を取得する"""
    qf=QueryFilter()
    qf.add_filter(f"category eq @category",{"category":category})
    qf.add_filter(f"title_no eq @title_no",{"title_no":title_no})
    contents = content.query_contents(qf,limit)
    return contents


@router.post("/contents", response_model=Content, status_code=201, tags=["contents"])
async def create_content(
    content_item: Content = Body(..., description="Content to create")
):
    """新しいコンテンツを作成する"""
    #サブ関数
    def check_existing_content():
        qf=QueryFilter()
        qf.add_filter(f"RowKey eq @content_id",{"content_id":content_item.id})
        qf.add_filter(f"title_no eq @title_no",{"title_no":content_item.title_no},'or')
        contents = content.query_contents(qf)
        if contents:
            return True
        return False
            
    #メイン処理
    existing=check_existing_content()
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"ID '{content_item.id}' または title_no '{content_item.title_no}' を持つリソースが既に存在します"
        )
    success = content.create_content(content_item)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to create content")
    
    return content_item

@router.get("/contents/{content_id}", response_model=Content, tags=["contents"])
async def get_content_by_id(
    content_id: uuid.UUID = Path(..., description="Content ID to get"),
):
    """指定されたIDのコンテンツを取得する"""
    qf=QueryFilter()
    qf.add_filter(f"RowKey eq @content_id",{"content_id":content_id})
    contents = content.query_contents(qf)
    if not contents:
        raise HTTPException(
            status_code=404,
            detail="指定されたIDのコンテンツが見つかりません"
        )
    return contents[0]


@router.put("/contents/{content_id}", response_model=Content, tags=["contents"])
async def update_content(
    content_id: uuid.UUID = Path(..., description="Content ID to update"),
    content_item: Content = Body(..., description="Updated content data")
):
    """指定されたIDのコンテンツを更新する"""
    #サブ関数
    def get_existing_content():
        qf=QueryFilter()
        qf.add_filter(f"RowKey eq @content_id",{"content_id":content_item.id})
        contents = content.query_contents(qf)
        return contents
        
            
    #メイン処理
    if content_id!=content_item.id:
        raise HTTPException(
            status_code=400,
            detail=f"パラメータのID {content_id} と更新するコンテンツのID {content_item.id} が一致しません。"
        )
    contents=get_existing_content()
    if not contents:
        raise HTTPException(
            status_code=404,
            detail=f"指定されたID {content_id} のコンテンツが見つかりません"
        )
    success = content.update_content(content_item)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to create content")
    
    return content_item


@router.delete("/contents/{content_id}", status_code=204, tags=["contents"])
async def delete_content_item(
    content_id: uuid.UUID  = Path(..., description="Content ID to delete")
):
    """指定されたIDのコンテンツを削除する"""
    #サブ関数
    def get_existing_content():
        qf=QueryFilter()
        qf.add_filter(f"RowKey eq @content_id",{"content_id":content_id})
        contents = content.query_contents(qf)
        return contents
        
    #メイン処理
    contents=get_existing_content()
    if not contents:
        raise HTTPException(
            status_code=404,
            detail="指定されたIDのコンテンツが見つかりません"
        )
    success = content.delete_content(contents[0])
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete content")
    
    return contents[0]

