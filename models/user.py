from fastapi import FastAPI
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import re
import uuid

class User(BaseModel):
    id:str =str(uuid.uuid4())
    