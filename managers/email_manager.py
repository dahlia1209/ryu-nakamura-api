from fastapi import APIRouter, HTTPException, Query, Path, Body, Depends, Header, Request, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List, Optional, Literal, Dict, Any
import os
from azure.communication.email import EmailClient

class EmailManager:
    _instance: Optional['EmailManager'] = None
    client: Optional[EmailClient] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            connection_string = os.getenv("EMAIL_CONNECTION_STRING")
            cls._instance.client = EmailClient.from_connection_string(connection_string)
        return cls._instance