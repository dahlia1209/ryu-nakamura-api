import azure.functions as func
import logging
import datetime
from api import app as fastapi_app
from models.youtube import YouTubeVideoListResponse
from managers.table_manager import TableConnectionManager
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient,generate_blob_sas,BlobSasPermissions
import googleapiclient.discovery
import googleapiclient.errors
import os
from repository.youtube import create_youtube_video
from managers.youtube_manager import YoutubeManager

app = func.AsgiFunctionApp(app=fastapi_app, http_auth_level=func.AuthLevel.ANONYMOUS)

@app.timer_trigger(schedule=os.getenv("YOUTUBE_SCHEDULER_CRON"), arg_name="myTimer", run_on_startup=False,use_monitor=False) 
def youtube_trending_scheduler(myTimer: func.TimerRequest) -> None:
    """
    YouTube トレンド動画を定期的に取得するスケジュール関数
    スケジュール: 6時間ごと (0 0 */6 * * *)
    """
    try:
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
            create_youtube_video(youtube,rank,utc_timestamp)
            
        youtube_manager=YoutubeManager()
        report=youtube_manager.generate_report()
            
    except Exception as e:
        logging.error(f'Error in YouTube trending scheduler: {str(e)}')
        raise
