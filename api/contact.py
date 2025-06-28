from fastapi import APIRouter,Body,BackgroundTasks
from fastapi import HTTPException
from models.email import EmailResponse,EmailRequest,EmailContent,EmailRecipients,EmailMessage,EmailAddress
from models.contact import ContactMessage
from models.order import Order
from azure.communication.email import EmailClient
from managers.email_manager import EmailManager
from api.email import notify_contact_message
import os
import uuid
from fastapi.responses import JSONResponse

router = APIRouter()

@router.post("/contact",tags=['contact'],status_code=200,response_model=ContactMessage)
async def notify_contact(
    background_tasks: BackgroundTasks,
    message: ContactMessage=Body(...)
):
    try:
        background_tasks.add_task(notify_contact_message, message)
        
        return JSONResponse(status_code=200,content=message.model_dump())
        
    except Exception as ex:
        raise HTTPException(status_code=500, detail=str(ex))


