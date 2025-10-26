from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, ValidationError
from typing import Literal, Dict, Any, List, Union,Optional
from threading import local,Lock
from azure.data.tables import TableServiceClient,TableClient
from azure.core.exceptions import ResourceExistsError
from azure.identity import DefaultAzureCredential
import os

class TableConnectionManager:
    _instance: Optional['TableConnectionManager'] = None
    _lock = Lock()
    client:Optional['TableServiceClient']=None
    contents_table:Optional['TableClient']=None
    user_table:Optional['TableClient']=None
    order_table:Optional['TableClient']=None
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
                    cls._instance.blockchain_address_table = get_table_client("blockchain_address",cls._instance.client)
                    cls._instance.blockchain_block_table = get_table_client("blockchain_block",cls._instance.client)
                    cls._instance.blockchain_transaction_table = get_table_client("blockchain_transaction",cls._instance.client)
                    cls._instance.blockchain_transaction_vin_table = get_table_client("blockchain_transaction_vin",cls._instance.client)
                    cls._instance.blockchain_transaction_output_table = get_table_client("blockchain_transaction_output",cls._instance.client)
                    
        return cls._instance
    
    def __init__(self):
        pass
    
    

