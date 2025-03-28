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
        
        #管理者向け
        admin_email = os.getenv("RECIPENTS_ADDRESS")  
        admin_message = message.create_admin_notification(admin_email)
        admin_poller = client.begin_send(admin_message.model_dump())
        admin_result = admin_poller.result()
        
        #顧客向け
        auto_reply_message = message.create_auto_reply()
        auto_reply_poller = client.begin_send(auto_reply_message.model_dump())
        auto_reply_result = auto_reply_poller.result()
        
        # 管理者向けメールの結果を返す
        return EmailResponse(**admin_result)
        
    except Exception as ex:
        raise HTTPException(status_code=500, detail=str(ex))
    