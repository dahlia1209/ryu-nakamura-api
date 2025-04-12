from fastapi import FastAPI
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import re

class ContentItem(BaseModel):
    id: int
    title: str
    preview_content: str
    image_url: str
    price: float
    category: str
    tags: List[str]
    publish_date: datetime
    is_featured: bool = False
    slug: str = ""
    preview_text_length: int = 100
    note_url: Optional[str] = None

    model_config = {
        "from_attributes": True
    }

    def __init__(self, **data):
        super().__init__(**data)
        if not self.slug:
            # Generate slug from title if not provided
            self.slug = re.sub(
                r'\s+', 
                '-', 
                re.sub(r'[^\w\s-]', '', self.title.lower())
            )