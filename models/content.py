from fastapi import FastAPI
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import re
import uuid
from azure.data.tables import TableEntity
import json
from bs4 import BeautifulSoup


class Content(BaseModel):
    id:uuid.UUID =Field(default_factory=uuid.uuid4)
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
    preview_speech_url: Optional[str] = None
    full_speech_url: Optional[str] = None
    preview_moovie_url: Optional[str] = None

    model_config = {
        "from_attributes": True
    }
    
    def to_preview(self):
        preview_text=""
        preview_html=""
        remaining_text_length=""
        
        soup = BeautifulSoup(self.content_html, 'html.parser')
        first_h2 = soup.find('h2')
        if not first_h2:
            return PreviewContent(**self.model_dump(),preview_html=preview_html,preview_text=preview_text,remaining_text_length=remaining_text_length)
        
        # 最初のh2とその後の連続するp要素を収集
        first_section_elements = [first_h2]
        current_element = first_h2.next_sibling
        
        while current_element:
            if current_element.name == 'p':
                first_section_elements.append(current_element)
                current_element = current_element.next_sibling
            elif current_element.name and current_element.name != 'p':
                # 次のh2や他のタグに遭遇したら停止
                break
            else:
                # テキストノードなどをスキップ
                current_element = current_element.next_sibling
        
        # ①の結果：最初のセクションのHTML
        preview_html = ''.join(str(elem) for elem in first_section_elements)
        preview_text = ''.join(elem.get_text() for elem in first_section_elements)
        preview_text_length = len(preview_text)
        
        all_text = soup.get_text()
        remaining_text = all_text.replace(preview_text, '', 1)  # 最初の一致のみ削除
        remaining_text_length = len(remaining_text)
        
        return PreviewContent(**self.model_dump(exclude={"full_speech_url"}),preview_html=preview_html,preview_text=preview_text,remaining_text_length=remaining_text_length)
            

class PreviewContent(BaseModel):
    id:uuid.UUID =Field(default_factory=uuid.uuid4)
    title_no: int
    title: str
    preview_text: str
    preview_html: str
    image_url: str
    price: float
    category: str
    tags: List[str]
    publish_date: datetime
    remaining_text_length: int 
    note_url: Optional[str] = None
    preview_speech_url: Optional[str] = None
    preview_moovie_url: Optional[str] = None
            


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
    preview_speech_url: Optional[str] = None
    full_speech_url: Optional[str] = None
    preview_moovie_url: Optional[str] = None
    
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
        
        
        
        
    