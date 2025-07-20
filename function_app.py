import azure.functions as func
import logging
import datetime
from api import app as fastapi_app
from models.youtube import YouTubeVideoListResponse
from models.trends24 import Trends24DataTableEntity
from managers.table_manager import TableConnectionManager
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient,generate_blob_sas,BlobSasPermissions
import googleapiclient.discovery
import googleapiclient.errors
import os
from repository import trends as trends_repo
from managers.trends_manager import YoutubeManager,Trends24Manager

app = func.AsgiFunctionApp(app=fastapi_app, http_auth_level=func.AuthLevel.ANONYMOUS)

@app.timer_trigger(schedule=os.getenv("TRENDS_SCHEDULER_CRON"), arg_name="myTimer", run_on_startup=False,use_monitor=False) 
def trending_scheduler(myTimer: func.TimerRequest) -> None:
    """
    トレンドニュースを定期的に取得するスケジュール関数
    """
    try:
        #Youtubeのトレンド
        utc_timestamp = datetime.datetime.now(tz=datetime.timezone.utc).strftime("%Y%m%d%H")
        youtube = googleapiclient.discovery.build(
            'youtube', 'v3', developerKey=os.getenv('YOUTUBE_API_KEY'))

        request = youtube.videos().list(
            part='snippet,statistics',
            chart='mostPopular', 
            regionCode='JP',      
            maxResults=10
        )
        response = request.execute()
        model_response=YouTubeVideoListResponse(**response)
        for (i,youtube) in enumerate(model_response.items):
            rank=i+1
            trends_repo.create_youtube_video(youtube,rank,utc_timestamp)
        
        youtube_manager=YoutubeManager()
        report=youtube_manager.generate_report(utc_timestamp)  
        
        
        #Xのトレンド
        trends24_manager=Trends24Manager()
        trends_data = trends24_manager.get_japan_trends()
        
        if trends_data:
            entities=Trends24DataTableEntity.from_trends24_data(trends_data) 
            for e in entities:
                trends_repo.create_trends24_item(e)
            
        report=trends24_manager.generate_report(utc_timestamp)
            
    except Exception as e:
        logging.error(f'Error in trending scheduler: {str(e)}')
        raise
