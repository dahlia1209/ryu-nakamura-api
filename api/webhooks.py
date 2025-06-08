from fastapi import APIRouter, HTTPException, Request, Response,Body,Query
import stripe
import os
from models.order import OrderItem,Order
from models.query import QueryFilter
from models.user import AzureUser,AzureAPIConnectResponse
from typing import Dict, Any
from repository import user as user_repo
from repository import content as content_repo
from repository import order as order_repo
from managers.email_manager import EmailManager
from models.email import EmailResponse,EmailRequest,EmailContent,EmailRecipients,EmailMessage,EmailAddress
import datetime
router = APIRouter()

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
endpoint_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

@router.post("/webhooks",tags=["webhooks"])
async def webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get('stripe-signature')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except ValueError as e:
        # Invalid payload
        raise HTTPException(status_code=400, detail=str(e))
    except stripe.SignatureVerificationError as e:
        # Invalid signature
        raise HTTPException(status_code=400, detail=str(e))
    
    retsult=None
    if event.type== 'checkout.session.expired' or event.type== 'checkout.session.completed':
        status=event.data.object.get("status")
        order_id = event.data.object.get('metadata', {}).get('order_id')
        order_item=order_repo.update_order_status(order_id,status)
        retsult=order_item
        
        if event.type=='checkout.session.completed':
            content=content_repo.get_content(str(order_item.content_id))
            user=user_repo.get_user(str(order_item.user_id))
            dt=datetime.datetime.fromtimestamp(event.data.object.get("created"))
            email_manager=EmailManager()
            
            purchased_order_reply=EmailRequest(
                content=EmailContent.purchased_order(
                    name=user.email,
                    order_id=order_id,
                    order_date=dt.strftime('%Y年%m月%d日 %H時%M分'),
                    content_title=content.title,
                    price=str(int(content.price)),
                    payment_method="クレジットカード",
                    content_html=content.content_html,
                    ),
                recipients=EmailRecipients(
                    to=[EmailAddress(address=user.email,displayName=user.email)],
                    bcc=[EmailAddress(address=os.getenv('RECIPENTS_ADDRESS'),displayName=os.getenv('RECIPENTS_ADDRESS'))]
                    ),
                senderAddress=os.getenv('SENDER_ADDRESS'),
            )

            poller = email_manager.client.begin_send(purchased_order_reply.model_dump())
            mail_result = poller.result()

    
    return retsult

@router.post("/webhooks/singinsignup",tags=["webhooks"])
async def webhook(azure_user: AzureUser=Body(...,description="azure user data")):
    try:
        user_item = azure_user.to_user()
        
        try:
            user_repo.update_user(user_item)
        
        except ValueError as e:
            user_repo.create_user(user_item)
        except Exception as e:
            raise HTTPException(
                status_code=500,
                    detail=f"Error: {e} "
            )
            
        return user_item
        
    except Exception as e:
        print(f"Error processing user data: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))