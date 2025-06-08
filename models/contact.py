from pydantic import BaseModel,Field
from typing import List, Optional,Dict
from bs4 import BeautifulSoup
import os


class ContactMessage(BaseModel):
    name: str 
    email: str 
    message: str 
    subject: Optional[str] 

