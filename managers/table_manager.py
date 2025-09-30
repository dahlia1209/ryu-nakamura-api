from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, ValidationError
from typing import Literal, Dict, Any, List, Union,Optional
from threading import local,Lock
from azure.data.tables import TableServiceClient,TableClient
from azure.core.exceptions import ResourceExistsError
from azure.identity import DefaultAzureCredential
import os

# class TableConnectionManager:
#     _instance: Optional['TableConnectionManager'] = None
    
#     def __init__(self):
#         self._client: Optional[TableServiceClient] = None
#         self._table_clients: dict[str, TableClient] = {}
    
#     def __new__(cls):
#         if cls._instance is None:
#             cls._instance = super().__new__(cls)
#         return cls._instance
    
#     def _get_client(self) -> TableServiceClient:
#         """TableServiceClientを遅延初期化で取得"""
#         if self._client is None:
#             credential = DefaultAzureCredential()
#             self._client = TableServiceClient(
#                 endpoint=os.getenv("AZURE_COSMOSDB_ENDPOINT"), 
#                 credential=credential
#             )
#         return self._client
    
#     def _get_table_client(self, table_name: str) -> TableClient:
#         """指定されたテーブル名のTableClientを遅延初期化で取得"""
#         # 既にキャッシュにある場合は即座に返す（高速化のポイント）
#         if table_name in self._table_clients:
#             return self._table_clients[table_name]
        
#         # キャッシュにない場合のみ作成
#         client = self._get_client()
#         try:
#             table_client = client.create_table_if_not_exists(table_name)
#         except ResourceExistsError:
#             table_client = client.get_table_client(table_name)
        
#         # キャッシュに保存
#         self._table_clients[table_name] = table_client
#         return table_client
    
#     # 各テーブルへのアクセス用プロパティ
#     @property
#     def contents_table(self) -> TableClient:
#         return self._get_table_client("content")
    
#     @property
#     def user_table(self) -> TableClient:
#         return self._get_table_client("user")
    
#     @property
#     def order_table(self) -> TableClient:
#         return self._get_table_client("order")
    
#     @property
#     def youtube_video_raw_table(self) -> TableClient:
#         return self._get_table_client("youtube_video_raw")
    
#     @property
#     def youtube_video_report_table(self) -> TableClient:
#         return self._get_table_client("youtube_video_report")
    
#     @property
#     def trends24_item_raw_table(self) -> TableClient:
#         return self._get_table_client("trends24_item_raw")
    
#     @property
#     def address_table(self) -> TableClient:
#         return self._get_table_client("address")
    
#     @property
#     def blockchain_transaction_table(self) -> TableClient:
#         return self._get_table_client("blockchain_transaction")
    
#     @property
#     def blockchain_transaction_vin_table(self) -> TableClient:
#         return self._get_table_client("blockchain_transaction_vin")
    
#     @property
#     def blockchain_transaction_output_table(self) -> TableClient:
#         return self._get_table_client("blockchain_transaction_output")

class TableConnectionManager:
    _instance: Optional['TableConnectionManager'] = None
    _lock = Lock()
    client:Optional['TableServiceClient']=None
    contents_table:Optional['TableClient']=None
    user_table:Optional['TableClient']=None
    order_table:Optional['TableClient']=None
    youtube_video_raw_table:Optional['TableClient']=None
    youtube_video_report_table:Optional['TableClient']=None
    trends24_item_raw_table:Optional['TableClient']=None
    blockchain_address_table:Optional['TableClient']=None
    blockchain_block_table:Optional['TableClient']=None
    blockchain_transaction_table:Optional['TableClient']=None
    blockchain_transaction_vin_table:Optional['TableClient']=None
    blockchain_transaction_output_table:Optional['TableClient']=None
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock: 
                if cls._instance is None: 
                    def get_client():
                        credential = DefaultAzureCredential()
                        return TableServiceClient(
                            endpoint=os.getenv("AZURE_COSMOSDB_ENDPOINT"), 
                            credential=credential
                        )
                        
                    def get_table_client(table_name:str,client:TableServiceClient):
                        try:
                            table_client = client.create_table_if_not_exists(table_name)
                        except ResourceExistsError:
                            table_client = client.get_table_client(table_name)
                        return table_client
                    
                    
                    cls._instance = super().__new__(cls)
                    # シングルトンの初期化
                    cls._instance.client = get_client()
                    cls._instance.contents_table = get_table_client("content",cls._instance.client)
                    cls._instance.user_table = get_table_client("user",cls._instance.client)
                    cls._instance.order_table = get_table_client("order",cls._instance.client)
                    cls._instance.youtube_video_raw_table = get_table_client("youtube_video_raw",cls._instance.client)
                    cls._instance.youtube_video_report_table = get_table_client("youtube_video_report",cls._instance.client)
                    cls._instance.trends24_item_raw_table = get_table_client("trends24_item_raw",cls._instance.client)
                    cls._instance.blockchain_address_table = get_table_client("blockchain_address",cls._instance.client)
                    cls._instance.blockchain_block_table = get_table_client("blockchain_block",cls._instance.client)
                    cls._instance.blockchain_transaction_table = get_table_client("blockchain_transaction",cls._instance.client)
                    cls._instance.blockchain_transaction_vin_table = get_table_client("blockchain_transaction_vin",cls._instance.client)
                    cls._instance.blockchain_transaction_output_table = get_table_client("blockchain_transaction_output",cls._instance.client)
                    
        return cls._instance
    
    def __init__(self):
        pass
    
    

