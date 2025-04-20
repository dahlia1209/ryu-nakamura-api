from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict, Any,Literal
from datetime import datetime
import uuid
from azure.data.tables import TableEntity

class User(BaseModel):
    id: uuid.UUID 
    provider:str
    email: str
    created_at: Optional[datetime] = None
    last_login: Optional[datetime] = None
    
    model_config = {
        "from_attributes": True
    }
    
        
    def set_timestamp(self,mode:Literal['update','create']):
        if mode=='create':
            self.created_at = datetime.now()
            self.last_login = None
        elif mode=='update':
            self.created_at = None
            self.last_login = datetime.now()

class UserTableEntity(BaseModel):
    PartitionKey: str = "user" 
    RowKey: str  
    provider:str
    email: str
    created_at: Optional[str] = None  
    last_login: Optional[str] = None 
    
    # User モデルに変換するメソッド
    def to_user(self) -> User:
        # 日付文字列をdatetimeに変換
        deserialized_id=uuid.UUID(self.RowKey)
        deserialized_created_at = datetime.fromisoformat(self.created_at) if self.created_at else None
        deserialized_last_login = datetime.fromisoformat(self.last_login) if self.last_login else None
        
        return User(id=deserialized_id,created_at=deserialized_created_at,last_login=deserialized_last_login,
                       **self.model_dump(exclude={"PartitionKey","RowKey","created_at","last_login"}))
    
    @classmethod
    def from_user(cls, user: User) -> "UserTableEntity":
        serialized_id=str(user.id)
        serialized_created_at = user.created_at.isoformat() if user.created_at else None
        serialized_last_login = user.last_login.isoformat() if user.last_login else None
        
        
        return cls(RowKey=serialized_id,created_at=serialized_created_at,last_login=serialized_last_login,
                   **user.model_dump(exclude={"RowKey","created_at","last_login"}))
        
    @classmethod
    def from_entity(cls, entity: TableEntity) :
        entity_dict = dict(entity)
        table_entity = UserTableEntity.model_validate(entity_dict)
        return table_entity

        
        