from fastapi import FastAPI
from fastapi.testclient import TestClient
from function_app import app as function_app
from api import app
from models.email import EmailMessage, EmailContent, EmailRecipients,EmailAddress,EmailResponse
import os

client = TestClient(app)

def test_my_second_function():
    email_message = EmailMessage(
        content=EmailContent(
            subject="テスト メール",
            plainText="メールで Hello World。",
            html="<html><body><h1>メールで Hello World。</h1></body></html>",
        ),
        senderAddress=os.getenv("SENDER_ADDRESS"),
        recipients=EmailRecipients(to=[EmailAddress(address=os.getenv("RECIPENTS_ADDRESS"))])
    )
    response = client.post(
        "/send-email",
        json=email_message.model_dump(),
        
    )
    assert response.status_code==200
    response = EmailResponse(**response.json())
    assert response.status=="Succeeded"
    assert response.error is None
    
    
