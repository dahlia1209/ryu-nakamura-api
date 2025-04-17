from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, ValidationError
from typing import Literal, Dict, Any, List, Union,Optional
import traceback
import random
from threading import local,Lock
from azure.data.tables import TableServiceClient,TableClient
from azure.core.exceptions import ResourceExistsError
from azure.identity import DefaultAzureCredential

class TableConnectionManager:
    _instance: Optional['TableConnectionManager'] = None
    _lock = Lock()
    client:Optional['TableServiceClient']=None
    contents_table:Optional['TableClient']=None
    user_table:Optional['TableClient']=None
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock: 
                if cls._instance is None: 
                    def get_client():
                        credential = DefaultAzureCredential()
                        return TableServiceClient(
                            endpoint="https://nakamura-cosmosdb.table.cosmos.azure.com:443/", 
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
                    
        return cls._instance
    
    def __init__(self):
        pass
    
    

