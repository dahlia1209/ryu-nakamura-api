from fastapi import FastAPI
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import re
import uuid
from azure.data.tables import TableEntity
import json

class Content(BaseModel):
    id:uuid.UUID =uuid.uuid4()
    title_no: int
    title: str
    content_text: str
    content_html: str
    image_url: str
    price: float
    category: str
    tags: List[str]
    publish_date: datetime
    preview_text_length: int = 100
    note_url: Optional[str] = None

    model_config = {
        "from_attributes": True
    }


class ContentTableEntity(BaseModel):
    PartitionKey: str ="content"
    RowKey: str
    title_no: int
    title: Optional[str] = None
    category: str="uncategorized"
    content_text: Optional[str] = None
    content_html: Optional[str] = None
    image_url: Optional[str] = None
    price: Optional[float] = None
    tags: Optional[str] =None
    publish_date: Optional[str] =  None
    preview_text_length: Optional[int] = None
    note_url: Optional[str] = None
    
    # Content モデルに変換するメソッド
    def to_content(self) -> Content:
        # デフォルト値を設定しながら変換
        deserialized_tags= json.loads(self.tags)
        deserialized_publish_date=datetime.fromisoformat(self.publish_date)
        deserialized_id=uuid.UUID(self.RowKey)
        return Content(id=deserialized_id,tags=deserialized_tags,publish_date=deserialized_publish_date,
                       **self.model_dump(exclude={"PartitionKey","RowKey","tags","publish_date"}))
        
    
    @classmethod
    def from_content(cls, content: Content) -> "ContentTableEntity":
        # Contentモデルからテーブルエンティティを作成
        serialized_tags= json.dumps(content.tags)
        serialized_publish_date=content.publish_date.isoformat()
        serialized_id=str(content.id)
        
        return cls(PartitionKey="content",RowKey=serialized_id,publish_date=serialized_publish_date,tags=serialized_tags,
                   **content.model_dump(exclude={"PartitionKey","RowKey","tags","publish_date"}))
        
    
    @classmethod
    def from_entity(cls, entity: TableEntity) :
        entity_dict = dict(entity)
        table_entity = ContentTableEntity.model_validate(entity_dict)
        return table_entity
        
        
        
        
    