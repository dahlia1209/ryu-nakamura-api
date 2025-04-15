from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, ValidationError
from typing import Literal, Dict, Any, List, Union,Optional
import traceback
import random
from threading import local,Lock
from azure.data.tables import TableServiceClient
from azure.identity import DefaultAzureCredential

class TableConnectionManager:
    _instance: Optional['TableConnectionManager'] = None
    _lock = Lock()
    client:Optional['TableServiceClient']=None
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock: 
                if cls._instance is None: 
                    cls._instance = super().__new__(cls)
                    # シングルトンの初期化
                    credential = DefaultAzureCredential()
                    cls._instance.client = TableServiceClient(
                        endpoint="https://nakamura-cosmosdb.table.cosmos.azure.com:443/", 
                        credential=credential
                    )
        return cls._instance
    
    def __init__(self):
        pass
    
    

