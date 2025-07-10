from fastapi import APIRouter, WebSocket, WebSocketDisconnect,HTTPException
import requests
from pydantic import BaseModel, ValidationError
from typing import Literal, Dict, Any, List, Union,Optional
from threading import local,Lock
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient,generate_blob_sas,BlobSasPermissions
import os
from datetime import datetime,timezone
from models.query import QueryFilter
import logging
import json
from repository import youtube as youtube_repo
from models.youtube import YouTubeVideoTableEntity,YouTubeVideoFormat

class YoutubeManager:
    
    def generate_report(self,yyyyMMddHH = datetime.now(tz=timezone.utc).strftime("%Y%m%d%H")):
        qf = QueryFilter()
        qf.add_filter(f"PartitionKey eq @PartitionKey", {"PartitionKey": yyyyMMddHH if yyyyMMddHH else  datetime.now(tz=timezone.utc).strftime("%Y%m%d%H")})
        youtube_videos = youtube_repo.query_contents(qf, 50)
        blobname = f"{os.getenv('CONTENT_REPORT_FILE_DIR')}/current_youtube_video_trend.json"
        blob_client =BlobClient.from_connection_string(
            conn_str=os.getenv("AZURE_STORAGE_CONNECTION_STRING"),
            container_name=os.getenv("AZURE_BLOB_CONTAINER_NAME"),
            blob_name=blobname,
            max_block_size=1024*1024*4, # 4 MiB
            max_single_put_size=1024*1024*8 # 8 MiB
        )
        
        
        contents_list = json.dumps([json.loads(c.to_youtube_video_format().model_dump_json()) for c in youtube_videos], ensure_ascii=False)
        logging.info(f"次のファイルをアップロードします: {blobname}")
        result=blob_client.upload_blob(contents_list, overwrite=True,timeout=600,max_concurrency=2)
        logging.info(f"アップロード完了しました: {blobname}")
        
        return [y.to_youtube_video_format() for y in youtube_videos]