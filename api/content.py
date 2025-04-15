from fastapi import APIRouter, HTTPException, Query, Path, Body
from typing import List, Optional
from models.content import Content
from repository import content
from datetime import datetime

router = APIRouter()

@router.get("/contents", response_model=List[Content], tags=["contents"])
async def list_contents(
    category: Optional[str] = Query(None, description="Filter by category"),
    title_no: Optional[int] = Query(None, description="Filter by title_no"),
    limit: int = Query(50, description="Maximum number of contents to return")
):
    """コンテンツの一覧を取得する"""
    contents = content.get_contents(category, title_no,limit)
    return contents

# @router.get("/contents/preview", response_model=List[Content], tags=["contents"])
# async def list_contents(
#     limit: int = Query(50, description="Maximum number of contents to return")
# ):
#     """コンテンツの一覧を取得する"""
#     contents = content.get_contents(is_preview=True,limit=limit)
#     return contents


@router.post("/contents", response_model=Content, status_code=201, tags=["contents"])
async def create_content(
    content_item: Content = Body(..., description="Content to create")
):
    """新しいコンテンツを作成する"""
    success = content.create_or_update_content(content_item)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to create content")
    
    return content_item

@router.put("/contents/{content_id}", response_model=Content, tags=["contents"])
async def update_content(
    content_id: int = Path(..., description="Content ID to update"),
    content_item: Content = Body(..., description="Updated content data")
):
    """指定されたIDのコンテンツを更新する"""
    # パスのIDとボディのIDが一致することを確認
    if content_id != content_item.title_no:
        raise HTTPException(status_code=400, detail="Path ID and body ID do not match")
    
    # 更新前に存在確認
    existing = content.get_content_by_id(content_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Content not found")
    
    success = content.create_or_update_content(content_item)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update content")
    
    return content_item

@router.delete("/contents/{content_id}", status_code=204, tags=["contents"])
async def delete_content_item(
    content_id: int = Path(..., description="Content ID to delete")
):
    """指定されたIDのコンテンツを削除する"""
    success = content.delete_content(content_id)
    if not success:
        raise HTTPException(status_code=404, detail="Content not found or could not be deleted")
    return None

