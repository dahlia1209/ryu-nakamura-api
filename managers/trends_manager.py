import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime,timezone
from typing import Optional, List, Dict, Any
from pydantic import ValidationError
from models.query import QueryFilter
from repository import trends as trends_repo
from models.trends24 import (
    Trends24Data, TimelineTrend, TrendItem, TrendsStatistics, 
    StatCategory, StatItem, Trends24DataProcessor, DataValidator,
    Trends24DataTableEntity
)
import logging
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient,generate_blob_sas,BlobSasPermissions
import os

class Trends24Manager:
    """Pydantic対応のtrends24.inスクレイパー"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })

    def get_japan_trends(self) -> Optional[Trends24Data]:
        """日本のX（Twitter）トレンドデータを取得してPydanticモデルで返す"""
        url = "https://trends24.in/japan/"
        
        try:
            response = self.session.get(url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # 生データを取得
            raw_timeline_data = self._extract_timeline_trends(soup)
            raw_stats_data = self._extract_statistics(soup)
            
            # Pydanticモデルでデータを検証・構造化
            timeline_data = self._validate_timeline_data(raw_timeline_data)
            statistics_data = self._validate_statistics_data(raw_stats_data)
            
            # 最終的なデータモデルを作成
            trends_data = Trends24Data(
                timeline=timeline_data,
                statistics=statistics_data,
                scraped_at=datetime.now(timezone.utc)
            )
            
            return trends_data
            
        except requests.RequestException as e:
            print(f"リクエストエラー: {e}")
            return None
        except ValidationError as e:
            print(f"データ検証エラー: {e}")
            return None
        except Exception as e:
            print(f"予期しないエラー: {e}")
            return None

    def _extract_timeline_trends(self, soup) -> List[Dict[str, Any]]:
        """タイムライン形式のトレンドデータを抽出（生データ）"""
        timeline_data = []
        
        timeline_container = soup.find('div', id='timeline-container')
        if not timeline_container:
            return timeline_data
        
        list_containers = timeline_container.find_all('div', class_='list-container')
        
        for container in list_containers:
            if 'vertical-ad' in container.get('class', []):
                continue
                
            title_elem = container.find('h3', class_='title')
            if not title_elem:
                continue
                
            timestamp_attr = title_elem.get('data-timestamp')
            timestamp_text = title_elem.get_text(strip=True)
            
            trend_list = container.find('ol', class_='trend-card__list')
            if not trend_list:
                continue
                
            trends = []
            for li in trend_list.find_all('li'):
                trend_data = self._extract_trend_item(li)
                if trend_data:
                    trends.append(trend_data)
            
            if trends:
                timeline_data.append({
                    'timestamp': timestamp_attr,
                    'timestamp_text': timestamp_text,
                    'trends': trends
                })
        
        return timeline_data

    def _extract_trend_item(self, li_element) -> Optional[Dict[str, Any]]:
        """個別のトレンド項目を抽出（生データ）"""
        trend_name_span = li_element.find('span', class_='trend-name')
        if not trend_name_span:
            return None
        
        trend_link = trend_name_span.find('a', class_='trend-link')
        if not trend_link:
            return None
            
        trend_text = trend_link.get_text(strip=True)
        trend_url = trend_link.get('href')
        
        tweet_count_span = trend_name_span.find('span', class_='tweet-count')
        tweet_count = None
        tweet_count_raw = None
        
        if tweet_count_span:
            tweet_count_text = tweet_count_span.get_text(strip=True)
            tweet_count_raw_attr = tweet_count_span.get('data-count')
            
            if tweet_count_text:
                tweet_count = tweet_count_text
            if tweet_count_raw_attr:
                try:
                    tweet_count_raw = int(tweet_count_raw_attr)
                except ValueError:
                    pass
        
        return {
            'text': trend_text,
            'url': trend_url,
            'tweet_count': tweet_count,
            'tweet_count_raw': tweet_count_raw
        }

    def _extract_statistics(self, soup) -> Dict[str, Any]:
        """統計データを抽出（生データ）"""
        stats = {}
        
        stat_cards = soup.find_all('section', class_='stat-card')
        
        for card in stat_cards:
            title_elem = card.find('h3', class_='stat-card-title')
            if not title_elem:
                continue
                
            title = title_elem.get_text(strip=True)
            
            items = []
            list_elem = card.find('ol', class_='stat-card-list')
            if list_elem:
                for li in list_elem.find_all('li', class_='stat-card-item'):
                    item_data = self._extract_stat_item(li)
                    if item_data:
                        items.append(item_data)
            
            if items:
                key = self._title_to_key(title)
                stats[key] = {
                    'title': title,
                    'items': items
                }
        
        return stats

    def _extract_stat_item(self, li_element) -> Optional[Dict[str, Any]]:
        """統計項目を抽出（生データ）"""
        trend_link = li_element.find('a', class_='trend-link')
        if not trend_link:
            return None
            
        trend_text = trend_link.get_text(strip=True)
        trend_url = trend_link.get('href')
        
        full_text = li_element.get_text(strip=True)
        additional_info = full_text.replace(trend_text, '').strip()
        
        return {
            'trend': trend_text,
            'url': trend_url,
            'info': additional_info
        }

    def _title_to_key(self, title: str) -> str:
        """日本語タイトルを英語キーに変換"""
        key_mapping = {
            'Longest Trending': 'longest_trending',
            'Trends with Maximum Tweets': 'max_tweets',
            'New Trends': 'new_trends',
            'Popular Active Trends': 'popular_active'
        }
        return key_mapping.get(title, title.lower().replace(' ', '_'))

    def _validate_timeline_data(self, raw_data: List[Dict[str, Any]]) -> List[TimelineTrend]:
        """タイムラインデータをPydanticモデルで検証"""
        validated_data = []
        for item in raw_data:
            try:
                # 各トレンド項目を検証
                validated_trends = []
                for trend_data in item.get('trends', []):
                    try:
                        validated_trend = TrendItem(**trend_data)
                        validated_trends.append(validated_trend)
                    except ValidationError as e:
                        print(f"トレンド項目検証エラー: {e}, データ: {trend_data}")
                        continue
                
                # タイムライン項目を検証
                timeline_item = TimelineTrend(
                    timestamp=item.get('timestamp'),
                    timestamp_text=item.get('timestamp_text', ''),
                    trends=validated_trends
                )
                validated_data.append(timeline_item)
                
            except ValidationError as e:
                print(f"タイムラインデータ検証エラー: {e}, データ: {item}")
                continue
        
        return validated_data

    def _validate_statistics_data(self, raw_data: Dict[str, Any]) -> TrendsStatistics:
        """統計データをPydanticモデルで検証"""
        validated_stats = {}
        
        for key, stat_data in raw_data.items():
            try:
                # 統計項目を検証
                validated_items = []
                for item_data in stat_data.get('items', []):
                    try:
                        validated_item = StatItem(**item_data)
                        validated_items.append(validated_item)
                    except ValidationError as e:
                        print(f"統計項目検証エラー: {e}, データ: {item_data}")
                        continue
                
                # 統計カテゴリを検証
                stat_category = StatCategory(
                    title=stat_data.get('title', ''),
                    items=validated_items
                )
                validated_stats[key] = stat_category
                
            except ValidationError as e:
                print(f"統計カテゴリ検証エラー: {e}, データ: {stat_data}")
                continue
        
        return TrendsStatistics(**validated_stats)

    def generate_report(self,yyyyMMddHH = datetime.now(tz=timezone.utc).strftime("%Y%m%d%H")):
        qf = QueryFilter()
        qf.add_filter(f"PartitionKey eq @PartitionKey", {"PartitionKey": yyyyMMddHH if yyyyMMddHH else  datetime.now(tz=timezone.utc).strftime("%Y%m%d%H")})
        trends24_items = trends_repo.query_trends24_item(qf, 50)
        blobname = f"{os.getenv('CONTENT_REPORT_FILE_DIR')}/current_trend24_item_trend.json"
        blob_client =BlobClient.from_connection_string(
            conn_str=os.getenv("AZURE_STORAGE_CONNECTION_STRING"),
            container_name=os.getenv("AZURE_BLOB_CONTAINER_NAME"),
            blob_name=blobname,
            max_block_size=1024*1024*4, # 4 MiB
            max_single_put_size=1024*1024*8 # 8 MiB
        )
        
        
        contents_list = json.dumps([json.loads(c.model_dump_json()) for c in trends24_items], ensure_ascii=False)
        logging.info(f"次のファイルをアップロードします: {blobname}")
        result=blob_client.upload_blob(contents_list, overwrite=True,timeout=600,max_concurrency=2)
        logging.info(f"アップロード完了しました: {blobname}")
        
        return trends24_items
    
    
class YoutubeManager:
    def generate_report(self,yyyyMMddHH = datetime.now(tz=timezone.utc).strftime("%Y%m%d%H")):
        qf = QueryFilter()
        qf.add_filter(f"PartitionKey eq @PartitionKey", {"PartitionKey": yyyyMMddHH if yyyyMMddHH else  datetime.now(tz=timezone.utc).strftime("%Y%m%d%H")})
        youtube_videos = trends_repo.query_youtube_videos(qf, 50)
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