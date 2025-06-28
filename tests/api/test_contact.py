from fastapi import FastAPI
from fastapi.testclient import TestClient
from api import app
from models.email import EmailResponse,EmailRequest,EmailContent,EmailRecipients,EmailMessage,EmailAddress
import os
from unittest.mock import Mock, patch
from models.contact import ContactMessage

client = TestClient(app)

def test_notify_contact():
    content=ContactMessage(
        name='TEST TARO',
        email='wakyaroya@cocoro.uk',
        message='こんにちは\nテストです\nTEST',
        subject='TEST 件名'
    )
    response = client.post(
        "/contact",
        json=content.model_dump(),
    )
    print(response.json())
    response_message=ContactMessage(**response.json())
    print(response_message.model_dump_json())
    assert response.status_code==200
    
    
