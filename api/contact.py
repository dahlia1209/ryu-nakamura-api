from fastapi import APIRouter
from fastapi import HTTPException
from models.email import EmailResponse,EmailRequest,EmailContent,EmailRecipients,EmailMessage,EmailAddress
from models.contact import ContactMessage
from models.order import Order
from azure.communication.email import EmailClient
from managers.email_manager import EmailManager
import os
import uuid

router = APIRouter()

@router.post("/contact",response_model=EmailResponse,tags=['contact'])
async def notify_contact(message: ContactMessage):
    try:
        email_manager=EmailManager()
        contact_reply=EmailRequest(
                content=EmailContent.contact(
                    contact_name=message.name,
                    contact_message=message.message,
                    contact_subject=message.subject,
                    ),
                recipients=EmailRecipients(
                    to=[EmailAddress(address=message.email,displayName=message.email)],
                    bcc=[EmailAddress(address=os.getenv('RECIPENTS_ADDRESS'),displayName=os.getenv('RECIPENTS_ADDRESS'))]
                    ),
                senderAddress=os.getenv('SENDER_ADDRESS'),
            )
        
        
        poller = email_manager.client.begin_send(contact_reply.model_dump())
        mail_result = poller.result()
        
        return EmailResponse(**mail_result)
        
    except Exception as ex:
        raise HTTPException(status_code=500, detail=str(ex))


