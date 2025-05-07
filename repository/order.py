from azure.data.tables import TableServiceClient,UpdateMode
from azure.identity import DefaultAzureCredential
from azure.core.exceptions import ResourceExistsError
from managers.table_manager import TableConnectionManager
from models.order import Order,OrderTableEntity,OrderStatus,OrderItem
from models.query import QueryFilter
from repository import user as user_repo
from repository import content as content_repo
from typing import List, Optional, Dict, Any
from datetime import datetime
import json
import uuid


def query_orders(
        query_filter:QueryFilter,
        limit: int = 50,
    ) :
    try:
        manager = TableConnectionManager()
        
        entities = list(manager.order_table.query_entities(**query_filter.model_dump(),results_per_page=limit))
        table_entities=[OrderTableEntity.from_entity(e) for e in entities]
        orders:List[Order]=[]
        
        for order_entity in table_entities:
            user=user_repo.get_user(order_entity.user_id)
            content=content_repo.get_content(order_entity.content_id)
            deserialized_created_at = datetime.fromisoformat(order_entity.created_at) if order_entity.created_at else None
            deserialized_updated_at = datetime.fromisoformat(order_entity.updated_at) if order_entity.updated_at else None
            order=Order(id=order_entity.RowKey,user=user,content=content,created_at=deserialized_created_at,updated_at=deserialized_updated_at,
            checkout_status=order_entity.checkout_status,quantity=order_entity.quantity)
            orders.append(order)
        
        return orders
        
    except Exception as e:
        raise ValueError(f"Error retrieving users: {str(e)}")

def get_order(order_id:str):
    """注文情報を取得する"""
    try:
        manager = TableConnectionManager()
        
        entity=manager.order_table.get_entity(partition_key='order',row_key=order_id)
        order_entity=OrderTableEntity.from_entity(entity)
        
        user=user_repo.get_user(order_entity.user_id)
        content=content_repo.get_content(order_entity.content_id)
        deserialized_created_at = datetime.fromisoformat(order_entity.created_at) if order_entity.created_at else None
        deserialized_updated_at = datetime.fromisoformat(order_entity.updated_at) if order_entity.updated_at else None
        order=Order(id=order_entity.RowKey,user=user,content=content,created_at=deserialized_created_at,updated_at=deserialized_updated_at,
                    checkout_status=order_entity.checkout_status,quantity=order_entity.quantity)
        
        return order
        
    except Exception as e:
        raise ValueError(f"Error retrieving contents: {str(e)}")

def create_order(order: Order) -> bool:
    """新しい注文を作成する"""
    try:
        manager = TableConnectionManager()
        order.update_timestamp('create')
        order_entity=OrderTableEntity.from_order(order)
        
        manager.order_table.create_entity(order_entity.model_dump(exclude_none=True))
        return True
        
    except Exception as e:
        raise ValueError(f"Error retrieving contents: {str(e)}")
    
    
def update_order_status(order_id:str,status: OrderStatus) :
    """注文ステータスをアップデートする"""
    try:
        manager = TableConnectionManager()
        
        entity=manager.order_table.get_entity(partition_key='order',row_key=order_id)
        entity["checkout_status"]=status
        entity["updated_at"]=datetime.now().isoformat()
        manager.order_table.update_entity(mode=UpdateMode.MERGE, entity=entity)
        order_item=OrderTableEntity.from_entity(entity).to_order_item()
        return order_item
        
    except Exception as e:
        raise ValueError(f"Error retrieving contents: {str(e)}")