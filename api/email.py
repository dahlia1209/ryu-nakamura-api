from fastapi import APIRouter
from fastapi import HTTPException
from models.email import EmailResponse,EmailMessage,EmailRecipients,EmailContent,EmailAddress
from models.order import Order
from azure.communication.email import EmailClient
from managers.email_manager import EmailManager
import os
import uuid

router = APIRouter()

@router.post("/email",response_model=EmailResponse,tags=['email'])
async def send_email(message: EmailMessage):
    try:
        email_manager=EmailManager()
        
        #管理者向け
        admin_email = os.getenv("RECIPENTS_ADDRESS")  
        admin_message = message.create_admin_notification(admin_email)
        admin_poller = email_manager.client.begin_send(admin_message.model_dump())
        admin_result = admin_poller.result()
        
        #顧客向け
        auto_reply_message = message.create_auto_reply()
        auto_reply_poller = email_manager.client.begin_send(auto_reply_message.model_dump())
        auto_reply_result = auto_reply_poller.result()
        
        # 管理者向けメールの結果を返す
        return EmailResponse(**admin_result)
        
    except Exception as ex:
        raise HTTPException(status_code=500, detail=str(ex))


