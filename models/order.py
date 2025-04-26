from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Literal
from datetime import datetime
import uuid
from enum import Enum
from azure.data.tables import TableEntity
import json
from models.content import Content
from models.user import User
import stripe

OrderStatus= Literal['complete','expired','open']

class Order(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    content: Content
    user: User
    quantity: int = 1
    checkout_status:OrderStatus='open'
    checkout_id:Optional[str]=None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    notes: Optional[str] = None

    model_config = {
        "from_attributes": True
    }

    def to_line_item(self):
        return stripe.checkout.Session.CreateParamsLineItem(
            price_data={
                "currency": "jpy",
                "product_data": {
                    "name": self.content.title,
                    "description": self.content.content_text[:200],
                    "images": [],
                },
                "unit_amount": int(self.content.price),
            },
            quantity=self.quantity,
        )
    
    def update_timestamp(self,mode:Literal['update','create','upsert']):
        if mode=='create':
            self.created_at = datetime.now()
            self.updated_at = None
        elif mode=='update':
            self.created_at = None
            self.updated_at = datetime.now()
        elif mode=='upsert':
            self.created_at = datetime.now()
            self.updated_at = datetime.now()


class OrderItem(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    user_id: uuid.UUID
    content_id: uuid.UUID
    checkout_id:Optional[str]=None
    quantity: int = 1
    checkout_status: OrderStatus='open'
    notes: Optional[str] = None

    model_config = {
        "from_attributes": True
    }

class OrderResponse(BaseModel):
    session_id: str  
    url: str  

class OrderTableEntity(BaseModel):
    PartitionKey: str = "order"
    RowKey: str  
    user_id: str
    content_id: str
    checkout_id: str
    quantity: int
    checkout_status: str 
    created_at: Optional[str] = None  
    updated_at: Optional[str] = None
    notes: Optional[str] = None
    
    
    def to_order_item(self) -> OrderItem:
        deserialized_id = uuid.UUID(self.RowKey)
        deserialized_user_id = uuid.UUID(self.user_id) 
        deserialized_content_id = uuid.UUID(self.content_id) 
        deserialized_created_at = datetime.fromisoformat(self.created_at) if self.created_at else None
        deserialized_updated_at = datetime.fromisoformat(self.updated_at) if self.updated_at else None
        
        return OrderItem(id=deserialized_id,user_id=deserialized_user_id,content_id=deserialized_content_id,created_at=deserialized_created_at,updated_at=deserialized_updated_at,
                        notes=self.notes,checkout_status=self.checkout_status,checkout_id=self.checkout_id)
    
    @classmethod
    def from_order(cls, order: Order) -> "OrderTableEntity":
        serialized_id = str(order.id)
        serialized_user_id = str(order.user.id) 
        serialized_content_id = str(order.content.id) 
        serialized_created_at = order.created_at.isoformat() if order.created_at else None
        serialized_updated_at = order.updated_at.isoformat() if order.updated_at else None
        
        return cls(RowKey=serialized_id,user_id=serialized_user_id,content_id=serialized_content_id,
                   created_at=serialized_created_at,updated_at=serialized_updated_at,
                   **order.model_dump(exclude={"RowKey","user_id","content_id","created_at","updated_at"}))
        
    @classmethod
    def from_entity(cls, entity: TableEntity):
        entity_dict = dict(entity)
        table_entity = OrderTableEntity.model_validate(entity_dict)
        return table_entity
