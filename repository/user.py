from azure.data.tables import TableServiceClient
from azure.identity import DefaultAzureCredential
from azure.core.exceptions import ResourceExistsError
from managers.table_connection import TableConnectionManager
from models.user import User, UserTableEntity
from models.query import QueryFilter
from typing import List, Optional, Dict, Any
from datetime import datetime
import json
import uuid


def query_users(
        query_filter:QueryFilter,
        limit: int = 50,
    ) :
    try:
        manager = TableConnectionManager()
        
        entities = list(manager.user_table.query_entities(**query_filter.model_dump(),results_per_page=limit))
        table_entities=[UserTableEntity.from_entity(e).to_user() for e in entities]
        
        return table_entities
        
    except Exception as e:
        raise ValueError(f"Error retrieving users: {str(e)}")
    

def create_user(user: User) -> bool:
    """新しいユーザーを作成する"""
    try:
        manager = TableConnectionManager()
        user.set_timestamp('create')
        user_entity=UserTableEntity.from_user(user)
        
        manager.user_table.create_entity(user_entity.model_dump(exclude_none=True))
        return True
        
    except Exception as e:
        raise ValueError(f"Error retrieving contents: {str(e)}")
    

def update_user(user: User) -> bool:
    """ユーザーを更新する"""
    try:
        manager = TableConnectionManager()
        user.set_timestamp('update')
        user_entity=UserTableEntity.from_user(user)
        
        manager.user_table.update_entity(user_entity.model_dump(exclude_none=True))
        return True
        
    except Exception as e:
        raise ValueError(f"Error retrieving contents: {str(e)}")



def delete_user(user: User) -> bool:
    """ユーザーを削除する"""
    try:
        manager = TableConnectionManager()
        user_entity=UserTableEntity.from_user(user)
        
        manager.user_table.delete_entity(partition_key=user_entity.PartitionKey,row_key=user_entity.RowKey)
        return True
        
    except Exception as e:
        raise ValueError(f"Error retrieving users: {str(e)}")
    