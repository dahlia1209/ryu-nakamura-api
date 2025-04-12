from typing import List, Optional
from fastapi import Depends, HTTPException, status
from pydantic import BaseModel

class TokenData(BaseModel):
    sub: str
    scopes: List[str] = []