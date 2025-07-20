from fastapi import APIRouter, HTTPException, Query, Path, Body,Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List, Optional
from managers.auth_manager import (
    JWTPayload,
    get_current_user,
    requires_scope,
    is_token_id_matching,
)
from models.query import QueryFilter
from repository import trends as trends_repo
from models.youtube import YouTubeVideoTableEntity,YouTubeVideoFormat
from models.trends24 import Trends24DataTableEntity
from datetime import datetime,timezone
from managers.blob_manager import BlobClient
from managers.trends_manager import Trends24Manager,YoutubeManager
import os
import logging
import json


router = APIRouter()
security = HTTPBearer()

# @router.get("/youtube/videos", response_model=List[YouTubeVideoTableEntity], tags=["trends"])
# async def list_youtube_video_trend(
#     limit: int = Query(50, description="Maximum number of contents to return"),
#     yyyyMMddHH: Optional[str] = Query(None, description="whformetted yyyyMMddHH (default:current time)"),
#     token_data: JWTPayload = Depends(requires_scope("youtube.read")),
# ):
#     """コンテンツの一覧を取得する"""
#     qf = QueryFilter()
#     qf.add_filter(f"PartitionKey eq @PartitionKey", {"PartitionKey": yyyyMMddHH if yyyyMMddHH else  datetime.now(tz=timezone.utc).strftime("%Y%m%d%H")})
#     youtube_videos = trends_repo.query_youtube_videos(qf, limit)
#     return youtube_videos


# @router.get("/trends24",  tags=["trends"])
# async def list_youtube_video_trend(
#     token_data: JWTPayload = Depends(requires_scope("web.read")),
# ):
#     scraper = Trends24Manager()
#     print("日本のトレンドデータを取得中...")
#     trends_data = scraper.get_japan_trends()
    
#     if trends_data:
#         print(f"\n=== データ取得成功 (取得時刻: {trends_data.scraped_at}) ===")
#         print(f"タイムライン数: {len(trends_data.timeline)}")
#         entities=Trends24DataTableEntity.from_trends24_data(trends_data) 
#         for e in entities:
#             trends_repo.create_trends24_item(e)
        
#         return Trends24DataTableEntity.from_trends24_data(trends_data) 
        
#     else:
#         print("データの取得に失敗しました")
        
        

# @router.post("/trends24/generate_report", status_code=201 , response_model=List[Trends24DataTableEntity], tags=["trends"])
# async def generate_report(
#     token_data: JWTPayload = Depends(requires_scope("youtube.read")),
# ):
#     """レポートを作成する"""
#     trends24_manager=Trends24Manager()
#     report=trends24_manager.generate_report()
    
#     return report