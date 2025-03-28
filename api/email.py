from fastapi import APIRouter
from fastapi import HTTPException
from models.email import EmailResponse,EmailMessage
from azure.communication.email import EmailClient
import os
import uuid

router = APIRouter()

@router.post("/send-email",response_model=EmailResponse)
async def send_email(message: EmailMessage):
    try:
        connection_string = os.getenv("EMAIL_CONNECTION_STRING")
        client = EmailClient.from_connection_string(connection_string)
        message.content.html = f"""
        <html>
            <body>
                お名前:{message.senderName}<br>
                メールアドレス :{message.recipients.getFirst()}<br>
                件名:{message.content.subject}<br>
                メッセージ:{message.content.plainText}<br>
            </body>
        </html>"""
        poller = client.begin_send(message.model_dump())
        result = poller.result()
        return EmailResponse(**result)
        
    except Exception as ex:
        raise HTTPException(status_code=500, detail=str(ex))
    