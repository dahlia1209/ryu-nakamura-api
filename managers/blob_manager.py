from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, ValidationError
from typing import Literal, Dict, Any, List, Union,Optional
from threading import local,Lock
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient,generate_blob_sas,BlobSasPermissions
import os
import datetime

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
    
    
    async def generate_sas_url(self,blob_name: str):
        """Azure Blob Storage用のSAS URLを生成する"""
        try:
            conn_str=os.getenv("AZURE_STORAGE_CONNECTION_STRING")
            result = {}
            for pair in conn_str.split(";"):
                key, value = pair.split('=', 1)
                result[key] = value
            start_time = datetime.datetime.now(datetime.timezone.utc)
            expiry_time = start_time + datetime.timedelta(hours=1)
            
            blob_client = self.client.get_blob_client(
                    container=os.getenv("AZURE_BLOB_PRIVATE_CONTAINER_NAME"), 
                    blob=blob_name, 
            )
            
            sas_token = generate_blob_sas(
                account_name=result["AccountName"],
                container_name=os.getenv("AZURE_BLOB_PRIVATE_CONTAINER_NAME"),
                blob_name=blob_name,
                account_key=result["AccountKey"],
                permission=BlobSasPermissions(read=True),
                expiry=expiry_time,
                start=start_time
            )
            
            sas_url = f"{blob_client.url}?{sas_token}"
            
            return sas_url
            
        except Exception as e:
            raise ValueError(f"SAS URL生成に失敗しました: {str(e)}")
    