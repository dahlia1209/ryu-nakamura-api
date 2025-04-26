from azure.data.tables import TableServiceClient
from azure.identity import DefaultAzureCredential
from azure.core.exceptions import ResourceExistsError
from managers.table_connection import TableConnectionManager
from models.content import Content,ContentTableEntity
from models.query import QueryFilter
from typing import List, Optional, Dict, Any
from datetime import datetime
import json
import uuid
from pydantic import BaseModel, Field, EmailStr

def query_contents(
        query_filter:QueryFilter,
        limit: int = 50,
    ) -> List[Content]:
    
    try:
        manager = TableConnectionManager()
        
        entities = list(manager.contents_table.query_entities(**query_filter.model_dump(),results_per_page=limit))
        table_entities=[ContentTableEntity.from_entity(e).to_content() for e in entities]
        
        return table_entities
        
    except Exception as e:
        raise ValueError(f"Error retrieving contents: {str(e)}")
    
def get_content(content_id:str) :
    try:
        manager = TableConnectionManager()
        
        entity=manager.contents_table.get_entity(partition_key='content',row_key=content_id)
        content=ContentTableEntity.from_entity(entity).to_content()
        
        return content
        
    except Exception as e:
        raise ValueError(f"Error retrieving contents: {str(e)}")

def create_content(content: Content) -> bool:
    """コンテンツの作成または更新"""

    try:
        manager = TableConnectionManager()
        content_entity=ContentTableEntity.from_content(content)
        
        manager.contents_table.create_entity(content_entity.model_dump(exclude_none=True))
        return True
        
    except Exception as e:
        raise ValueError(f"Error retrieving contents: {str(e)}")

def update_content(content: Content) -> bool:
    """コンテンツの作成"""

    try:
        manager = TableConnectionManager()
        content_entity=ContentTableEntity.from_content(content)
        
        manager.contents_table.update_entity(content_entity.model_dump(exclude_none=True))
        return True
        
    except Exception as e:
        raise ValueError(f"Error retrieving contents: {str(e)}")
    

def delete_content(content: Content) -> bool:
    """指定されたIDのコンテンツを削除する"""
    try:
        manager = TableConnectionManager()
        content_entity=ContentTableEntity.from_content(content)
        
        manager.contents_table.delete_entity(partition_key=content_entity.PartitionKey,row_key=content_entity.RowKey)
        return True
        
    except Exception as e:
        raise ValueError(f"Error retrieving contents: {str(e)}")
    