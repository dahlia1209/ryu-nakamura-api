from fastapi import FastAPI
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import re
import uuid

class Content(BaseModel):
    id:str =str(uuid.uuid4())
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
    PartitionKey: str 
    RowKey: str
    title_no: int
    title: Optional[str] = None
    content_text: Optional[str] = None
    content_html: Optional[str] = None
    image_url: Optional[str] = None
    price: Optional[float] = None
    tags: Optional[List[str]] = None
    publish_date: Optional[datetime] = None
    preview_text_length: Optional[int] = None
    note_url: Optional[str] = None
    
    # Content モデルに変換するメソッド
    def to_content(self) -> Content:
        # デフォルト値を設定しながら変換
        return Content(
            id=self.RowKey,
            title_no=self.title_no,
            title=self.title or "",
            content_text=self.content_text or "",
            content_html=self.content_html or "",
            image_url=self.image_url or "",
            price=float(self.price or 0.0),
            category=self.PartitionKey or "未分類",
            tags=self.tags or [],
            publish_date=self.publish_date or datetime.now(),
            preview_text_length=self.preview_text_length or 100,
            note_url=self.note_url
        )
    
    @classmethod
    def from_content(cls, content: Content) -> "ContentTableEntity":
        # Contentモデルからテーブルエンティティを作成
        return cls(
            PartitionKey=content.category,
            RowKey=content.id,
            title_no=content.title_no,
            title=content.title,
            content_text=content.content_text,
            content_html=content.content_html,
            image_url=content.image_url,
            price=content.price,
            tags=content.tags,
            publish_date=content.publish_date,
            preview_text_length=content.preview_text_length,
            note_url=content.note_url
        )
        
        
    