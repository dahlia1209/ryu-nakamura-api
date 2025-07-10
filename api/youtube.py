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
from repository import youtube as youtube_repo
from models.youtube import YouTubeVideoTableEntity,YouTubeVideoFormat
from datetime import datetime,timezone
from managers.blob_manager import BlobClient
from managers.youtube_manager import YoutubeManager
import os
import logging
import json

router = APIRouter()
security = HTTPBearer()


@router.get("/youtube/videos", response_model=List[YouTubeVideoTableEntity], tags=["youtube"])
async def list_youtube_video_trend(
    limit: int = Query(50, description="Maximum number of contents to return"),
    yyyyMMddHH: Optional[str] = Query(None, description="whformetted yyyyMMddHH (default:current time)"),
    token_data: JWTPayload = Depends(requires_scope("youtube.read")),
):
    """コンテンツの一覧を取得する"""
    qf = QueryFilter()
    qf.add_filter(f"PartitionKey eq @PartitionKey", {"PartitionKey": yyyyMMddHH if yyyyMMddHH else  datetime.now(tz=timezone.utc).strftime("%Y%m%d%H")})
    youtube_videos = youtube_repo.query_contents(qf, limit)
    return youtube_videos

# @router.post("/youtube/videos/generate_report", status_code=201 , response_model=List[YouTubeVideoFormat], tags=["youtube"])
# async def generate_report(
#     token_data: JWTPayload = Depends(requires_scope("youtube.read")),
# ):
#     """レポートを作成する"""
#     youtube_manager=YoutubeManager()
#     report=youtube_manager.generate_report()
    
#     return report
