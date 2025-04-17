from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid

class User(BaseModel):
    id: uuid.UUID # Azure B2C user ID
    provider:str
    email: str
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    last_login: Optional[datetime] = None
    
    model_config = {
        "from_attributes": True
    }

class UserTableEntity(BaseModel):
    PartitionKey: str = "User"  # Static partition key for all users
    RowKey: str  # user ID
    provider:str
    email: str
    created_at: str  # ISO format
    updated_at: str  # ISO format
    last_login: Optional[str] = None  # ISO format
    
    # User モデルに変換するメソッド
    def to_user(self) -> User:
        # 日付文字列をdatetimeに変換
        created_at = datetime.fromisoformat(self.created_at) if isinstance(self.created_at, str) else datetime.now()
        updated_at = datetime.fromisoformat(self.updated_at) if isinstance(self.updated_at, str) else datetime.now()
        last_login = datetime.fromisoformat(self.last_login) if self.last_login else None
        
        return User(
            id=uuid.uuid4(self.RowKey),
            email=self.email,
            provider=self.provider,
            created_at=created_at,
            updated_at=updated_at,
            last_login=last_login,
        )
    
    @classmethod
    def from_user(cls, user: User) -> "UserTableEntity":
        
        # リストとオブジェクトをJSON文字列に変換
        return cls(
            PartitionKey="User",
            RowKey=str(user.id),
            email=user.email,
            provider=user.provider,
            created_at=user.created_at.isoformat(),
            updated_at=user.updated_at.isoformat(),
            last_login=user.last_login.isoformat() if user.last_login else None,
        )