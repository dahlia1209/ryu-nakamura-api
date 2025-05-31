from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, ValidationError
from typing import Literal, Dict, Any, List, Union,Optional
from threading import local,Lock
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient
import os


class BLOBConnectionManager:
    _instance: Optional['BLOBConnectionManager'] = None
    client:Optional['BlobServiceClient']=None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls.client = BlobServiceClient.from_connection_string(os.getenv("AZURE_STORAGE_CONNECTION_STRING"))
            
        return cls._instance
    
    def __init__(self):
        pass
    
    